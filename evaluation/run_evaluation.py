#!/usr/bin/env python3
"""Run an evaluation set against the gateway and report measured output.

Two ways to run it:

* ``--base-url`` sends each scenario to a running gateway. This is the only mode whose
  numbers can describe a live system. It needs nothing but the standard library.
* ``--in-process`` builds the gateway inside this process, in fixture mode, and applies each
  failure scenario's ``condition`` with deterministic stub detectors. It is a contract and
  degraded-mode check. Its verdict agreement is never a detection result.

Scenario ``condition`` blocks need in-process control, so they are skipped (and listed as
skipped) when running against ``--base-url``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fixture_set  # noqa: E402

COVERAGE_KEYS = {"text", "url", "conversation", "reputation"}
BENIGN = {"legitimate", "spam"}

# (status_code, body or None, latency_ms)
Outcome = tuple[int, dict[str, Any] | None, float]
Poster = Callable[[dict[str, Any], dict[str, Any] | None], Outcome]


def http_poster(base_url: str) -> Poster:
    endpoint = f"{base_url.rstrip('/')}/v1/analyze"

    def post(payload: dict[str, Any], condition: dict[str, Any] | None) -> Outcome:
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=20) as response:
                status, raw = response.status, response.read()
        except HTTPError as error:
            status, raw = error.code, error.read()
        latency = (time.perf_counter() - started) * 1000
        try:
            return status, json.loads(raw), latency
        except json.JSONDecodeError:
            return status, None, latency

    return post


class ConditionDetectors:
    """Stands in for the private text and URL services under a named condition."""

    def __init__(self, states: dict[str, str]) -> None:
        self.states = states

    async def _run(self, name: str, ok: Callable[[], Any]) -> Any:
        from services.gateway.app.clients.detectors import unavailable_result

        state = self.states.get(name, "ok")
        if state == "unavailable":
            return unavailable_result(name, f"{name} service was unavailable")
        if state == "slow":
            await asyncio.sleep(60)  # the gateway's overall deadline cancels this
        return ok()

    async def text(self, text: str) -> Any:
        from services.gateway.app.risk.fixtures import fixture_text_result

        return await self._run("text", lambda: fixture_text_result(text))

    async def url(self, urls: list[str]) -> Any:
        from services.gateway.app.risk.fixtures import fixture_url_result

        return await self._run("url", lambda: fixture_url_result(urls))


class InProcessGateway:
    """A gateway built in this process, reused for every scenario. Imported lazily so that
    ``--base-url`` needs no packages. Settings and detectors are swapped per scenario."""

    def __init__(self) -> None:
        sys.path.insert(0, str(fixture_set.ROOT.parent))
        import httpx

        from services.gateway.app.main import create_app
        from services.gateway.app.settings import Settings

        self._settings = Settings
        self._default_settings = Settings(_env_file=None, demo_mode=True)
        self.app = create_app(self._default_settings)
        self._default_detectors = self.app.state.detectors
        self.loop = asyncio.new_event_loop()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://gateway")

    def __enter__(self) -> "InProcessGateway":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if not self.loop.is_closed():
            self.loop.run_until_complete(self.client.aclose())
            self.loop.close()

    def __call__(self, payload: dict[str, Any], condition: dict[str, Any] | None) -> Outcome:
        if condition:
            self.app.state.settings = self._settings(
                _env_file=None, demo_mode=False,
                analysis_timeout_seconds=float(condition.get("analysis_timeout_seconds", 5)),
            )
            self.app.state.detectors = ConditionDetectors(condition.get("detectors", {}))
        else:
            self.app.state.settings = self._default_settings
            self.app.state.detectors = self._default_detectors
        started = time.perf_counter()
        response = self.loop.run_until_complete(self.client.post("/v1/analyze", json=payload))
        latency = (time.perf_counter() - started) * 1000
        try:
            return response.status_code, response.json(), latency
        except ValueError:
            return response.status_code, None, latency


def in_process_poster() -> InProcessGateway:
    return InProcessGateway()


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))], 2)


def contract_violations(body: dict[str, Any]) -> list[str]:
    """Invariants every 200 response must hold, whatever the mode or detector."""
    problems = []
    if body.get("risk_score") is not None:
        problems.append("risk_score is not null")
    if body.get("probability_calibrated") is not False:
        problems.append("probability_calibrated is not false")
    if set(body.get("coverage", {})) != COVERAGE_KEYS:
        problems.append("coverage does not have exactly the four contract fields")
    if body.get("verdict") == "suspected_scam" and not body.get("evidence"):
        problems.append("suspected_scam without evidence")
    if body.get("status") == "unavailable" and (body.get("verdict") != "unknown" or body.get("severity") != "unknown"):
        problems.append("unavailable result is not unknown/unknown")
    return problems


def expectation_failures(scenario: dict[str, Any], status: int, body: dict[str, Any] | None) -> list[str]:
    """Compare a response with the scenario's stated expectations.

    ``expected_http_status`` (default 200) and ``expected_status`` are top-level fields so other
    tooling can read them; ``expected`` holds the extra checks (severity, coverage, evidence).
    """
    failures = []
    want_http = scenario.get("expected_http_status", 200)
    if status != want_http:
        failures.append(f"http_status {status} != {want_http}")
    if status == 200 and body is not None:
        extra = scenario.get("expected", {})
        if "expected_status" in scenario and body.get("status") != scenario["expected_status"]:
            failures.append(f"status {body.get('status')!r} != {scenario['expected_status']!r}")
        if "severity" in extra and body.get("severity") != extra["severity"]:
            failures.append(f"severity {body.get('severity')!r} != {extra['severity']!r}")
        for name, want in extra.get("coverage", {}).items():
            if body.get("coverage", {}).get(name) != want:
                failures.append(f"coverage.{name} {body.get('coverage', {}).get(name)!r} != {want!r}")
        if extra.get("evidence_required") and not body.get("evidence"):
            failures.append("expected evidence but the result has none")
    return failures


def run_scenarios(scenarios: list[dict[str, Any]], post: Poster, *, can_apply_conditions: bool) -> list[dict[str, Any]]:
    records = []
    for scenario in scenarios:
        base = {
            "id": scenario["id"], "category": scenario.get("category"), "group": scenario.get("group"),
            "ambiguous": bool(scenario.get("ambiguous")), "expected": scenario["expected_verdict"],
        }
        condition = scenario.get("condition")
        if condition and not can_apply_conditions:
            records.append({**base, "skipped": "needs in-process control of the detectors; run with --in-process"})
            continue
        try:
            status, body, latency = post(scenario["input"], condition)
        except (URLError, TimeoutError, OSError) as error:
            records.append({**base, "error": f"{type(error).__name__}: request failed", "http_status": None})
            continue
        record = {**base, "http_status": status, "latency_ms": round(latency, 2)}
        if status == 200 and body is not None:
            record.update(
                actual=body.get("verdict"), status=body.get("status"), severity=body.get("severity"),
                fixture_generated=bool(body.get("fixture_generated")) or any(
                    m.get("fixture_generated") for m in body.get("module_results", {}).values()),
                versions=body.get("versions", {}),
                contract_violations=contract_violations(body),
            )
            record["matched"] = record["actual"] == scenario["expected_verdict"]
        failures = expectation_failures(scenario, status, body)
        if status != 200 or any(key in scenario for key in ("expected", "expected_status", "expected_http_status")):
            record["expectation_failures"] = failures
        records.append(record)
    return records


def versions_seen(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Every distinct component version observed, so a mixed run is visible."""
    seen: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for name, version in record.get("versions", {}).items():
            seen[name].add(version)
    return {name: sorted(values) for name, values in sorted(seen.items())}


def build_report(
    records: list[dict[str, Any]], *, set_name: str, document: dict[str, Any], mode: str,
) -> dict[str, Any]:
    scored = [r for r in records if r.get("http_status") == 200 and "actual" in r]
    skipped = [{"id": r["id"], "reason": r["skipped"]} for r in records if "skipped" in r]
    # Network failures, and any non-200 the scenario did not expect.
    errors = [r for r in records if "error" in r or (
        r.get("http_status") not in (200, None) and r.get("expectation_failures"))]
    confusion: Counter[str] = Counter(f"{r['expected']}->{r['actual']}" for r in scored)
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for r in scored:
        by_category[r["category"] or "uncategorised"][f"{r['expected']}->{r['actual']}"] += 1

    tp = sum(r["expected"] == "suspected_scam" and r["actual"] == "suspected_scam" for r in scored)
    fp = sum(r["expected"] != "suspected_scam" and r["actual"] == "suspected_scam" for r in scored)
    fn = sum(r["expected"] == "suspected_scam" and r["actual"] != "suspected_scam" for r in scored)
    benign = [r for r in scored if r["expected"] in BENIGN]
    latencies = [r["latency_ms"] for r in scored]

    freeze = document.get("metadata", {}).get("freeze", {})
    not_reportable = []
    if set_name == "bootstrap":
        not_reportable.append("the bootstrap set holds six contract examples, not a sprint set")
    if freeze.get("status") != "frozen":
        not_reportable.append("the set is not frozen: labels lack two reviewers")
    if document.get("metadata", {}).get("synthetic") is True:
        not_reportable.append("the dataset is synthetic and cannot support a detection-performance claim")
    if mode == "in-process":
        not_reportable.append("in-process mode uses fixture rules and stub detectors")
    if any(r.get("fixture_generated") for r in scored):
        not_reportable.append("responses were fixture-generated demo data")
    if skipped:
        not_reportable.append(f"{len(skipped)} scenarios were skipped")

    return {
        "scope": "Contract and degraded-mode check; not a detection result."
        if not_reportable else "Measured against the live gateway on a frozen, reviewed set.",
        "reportable_as_detection_performance": not not_reportable,
        "reasons_not_reportable": not_reportable,
        "mode": mode,
        "set": set_name,
        "fixture_sha256": fixture_set.canonical_hash(document),
        "freeze_status": freeze.get("status", "n/a"),
        "synthetic": document.get("metadata", {}).get("synthetic"),
        "scenario_count": len(records),
        "scored_count": len(scored),
        "skipped": skipped,
        "exact_verdict_agreement": sum(bool(r["matched"]) for r in scored),
        "confusion": dict(sorted(confusion.items())),
        "confusion_by_category": {k: dict(sorted(v.items())) for k, v in sorted(by_category.items())},
        "scam": {
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        },
        "benign_false_positives": {
            "benign_scenarios": len(benign),
            "flagged_as_scam": sum(r["actual"] == "suspected_scam" for r in benign),
        },
        "ambiguous_scenarios": sum(r["ambiguous"] for r in scored),
        "unknown_results": sum(r["actual"] == "unknown" for r in scored),
        "partial_responses": sum(r.get("status") == "partial" for r in scored),
        "unavailable_responses": sum(r.get("status") == "unavailable" for r in scored),
        "request_errors": len(errors),
        "contract_violations": {r["id"]: r["contract_violations"] for r in scored if r["contract_violations"]},
        "expectation_failures": {r["id"]: r["expectation_failures"] for r in records if r.get("expectation_failures")},
        "latency_ms": {"p50": round(statistics.median(latencies), 2) if latencies else None, "p95": percentile(latencies, 0.95),
                       "basis": "in-process call" if mode == "in-process" else "client-observed HTTP"},
        "versions": versions_seen(scored),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", dest="set_name", choices=tuple(fixture_set.SETS), default="development")
    parser.add_argument("--fixtures", type=Path, help="run this fixture file instead of the named set")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    target.add_argument("--in-process", action="store_true")
    parser.add_argument("--final-run", action="store_true", help="required to run the holdout set")
    parser.add_argument("--check-expectations", action="store_true",
                        help="exit 1 on contract violations or unmet failure-scenario expectations")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.set_name == "holdout" and not args.final_run:
        print("The holdout set is for the final measurement only. Re-run with --final-run once the "
              "development work is finished; never tune against it.", file=sys.stderr)
        return 2

    path = args.fixtures or fixture_set.SETS[args.set_name]
    document = fixture_set.load(path)
    mode = "in-process" if args.in_process else "http"
    if args.in_process:
        with in_process_poster() as post:
            records = run_scenarios(document["scenarios"], post, can_apply_conditions=True)
    else:
        records = run_scenarios(document["scenarios"], http_poster(args.base_url), can_apply_conditions=False)
    report = build_report(records, set_name=args.set_name, document=document, mode=mode)

    output = json.dumps(report, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(
        f"[{mode}] {report['set']}: {report['scored_count']}/{report['scenario_count']} scored, "
        f"{len(report['skipped'])} skipped, {report['request_errors']} errors, "
        f"{len(report['contract_violations'])} contract violations, "
        f"{len(report['expectation_failures'])} unmet expectations. {report['scope']}",
        file=sys.stderr,
    )
    if args.check_expectations and (
        report["contract_violations"] or report["expectation_failures"] or report["request_errors"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
