#!/usr/bin/env python3
"""Run labeled scenarios and separate contract checks from performance evidence."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCAM = "suspected_scam"


def post(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.load(response), (time.perf_counter() - started) * 1000
    except HTTPError as exc:
        try:
            body = json.load(exc)
        except json.JSONDecodeError:
            body = {"detail": "non-JSON error response"}
        return exc.code, body, (time.perf_counter() - started) * 1000


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return round(ordered[index], 2)


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def calculate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = [record for record in records if record.get("expected") and record.get("actual")]
    true_positive = sum(record["expected"] == SCAM and record["actual"] == SCAM for record in labeled)
    false_positive = sum(record["expected"] != SCAM and record["actual"] == SCAM for record in labeled)
    false_negative = sum(record["expected"] == SCAM and record["actual"] != SCAM for record in labeled)
    benign = [record for record in labeled if record["expected"] == "legitimate"]
    benign_false_positive = sum(record["actual"] == SCAM for record in benign)
    return {
        "scam_precision": ratio(true_positive, true_positive + false_positive),
        "scam_recall": ratio(true_positive, true_positive + false_negative),
        "benign_false_positive_rate": ratio(benign_false_positive, len(benign)),
        "status_counts": dict(sorted(Counter(record.get("status", "error") for record in records).items())),
        "transport_error_count": sum(record.get("transport_error") is not None for record in records),
        "partial_count": sum(record.get("status") == "partial" for record in records),
        "unavailable_count": sum(record.get("status") == "unavailable" for record in records),
    }


def assess_dataset(document: dict[str, Any]) -> dict[str, Any]:
    metadata = document.get("metadata", {})
    scenarios = document.get("scenarios", [])
    split_counts = Counter(scenario.get("split", "unassigned") for scenario in scenarios)
    conversation_count = sum(scenario.get("input", {}).get("source") == "conversation" for scenario in scenarios)
    failure_count = sum(
        scenario.get("case_kind") == "failure"
        or scenario.get("expected_status") in {"partial", "unavailable"}
        or scenario.get("expected_http_status", 200) != 200
        for scenario in scenarios
    )
    provenance_count = sum(bool(scenario.get("provenance")) for scenario in scenarios)
    evidence_count = sum(bool(str(scenario.get("support", "")).strip()) for scenario in scenarios)
    dual_review_count = sum(len(set(scenario.get("reviewers", []))) >= 2 for scenario in scenarios)

    requirements = {
        "non_synthetic_dataset": metadata.get("synthetic") is False,
        "development_cases_at_least_30": split_counts["development"] >= 30,
        "holdout_cases_at_least_20": split_counts["holdout"] >= 20,
        "conversation_cases_at_least_6": conversation_count >= 6,
        "failure_cases_at_least_5": failure_count >= 5,
        "provenance_for_every_case": provenance_count == len(scenarios) and bool(scenarios),
        "supporting_evidence_for_every_case": evidence_count == len(scenarios) and bool(scenarios),
        "two_reviewers_for_every_case": dual_review_count == len(scenarios) and bool(scenarios),
        "holdout_is_frozen": metadata.get("holdout_frozen") is True,
        "holdout_tuning_is_prohibited": metadata.get("holdout_tuning_prohibited") is True,
    }
    unmet = [name for name, met in requirements.items() if not met]
    return {
        "performance_claim_eligible": not unmet,
        "requirements": requirements,
        "unmet_requirements": unmet,
        "split_counts": dict(sorted(split_counts.items())),
        "conversation_count": conversation_count,
        "failure_count": failure_count,
        "provenance_count": provenance_count,
        "dual_review_count": dual_review_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "scenarios.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-release-dataset",
        action="store_true",
        help="fail unless the dataset meets the documented release-evaluation gates",
    )
    args = parser.parse_args()

    fixture_document = json.loads(args.fixtures.read_text(encoding="utf-8"))
    readiness = assess_dataset(fixture_document)
    records: list[dict[str, Any]] = []
    latencies: list[float] = []
    confusion: Counter[str] = Counter()
    version_matrix: Counter[str] = Counter()
    for scenario in fixture_document["scenarios"]:
        expected = scenario.get("expected_verdict")
        expected_status = scenario.get("expected_status")
        expected_http = scenario.get("expected_http_status", 200)
        try:
            http_status, response, latency_ms = post(
                f"{args.base_url.rstrip('/')}/v1/analyze", scenario["input"]
            )
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            records.append(
                {
                    "id": scenario["id"],
                    "split": scenario.get("split", "unassigned"),
                    "expected": expected,
                    "actual": None,
                    "status": "error",
                    "http_status": None,
                    "transport_error": type(exc).__name__,
                    "matched": False,
                }
            )
            continue

        actual = response.get("verdict")
        actual_status = response.get("status", "error")
        latency_ms = round(latency_ms, 2)
        latencies.append(latency_ms)
        if expected and actual:
            confusion[f"{expected}->{actual}"] += 1
        versions = response.get("versions") if isinstance(response.get("versions"), dict) else {}
        if versions:
            version_matrix[json.dumps(versions, sort_keys=True)] += 1
        matched = http_status == expected_http
        if expected is not None:
            matched = matched and actual == expected
        if expected_status is not None:
            matched = matched and actual_status == expected_status
        records.append(
            {
                "id": scenario["id"],
                "split": scenario.get("split", "unassigned"),
                "expected": expected,
                "actual": actual,
                "expected_status": expected_status,
                "status": actual_status,
                "expected_http_status": expected_http,
                "http_status": http_status,
                "fixture_generated": response.get("fixture_generated"),
                "latency_ms": latency_ms,
                "transport_error": None,
                "matched": matched,
            }
        )

    metrics = calculate_metrics(records)
    report = {
        "scope": "authored synthetic bootstrap scenarios; not a real-world accuracy claim"
        if fixture_document.get("metadata", {}).get("synthetic") is True
        else "reviewed labeled scenarios; interpret only within the documented dataset scope",
        "performance_claim_eligible": readiness["performance_claim_eligible"]
        and not any(record.get("fixture_generated") for record in records),
        "dataset_readiness": readiness,
        "scenario_count": len(records),
        "fixture_document": fixture_document["metadata"],
        "confusion": dict(sorted(confusion.items())),
        "metrics": metrics,
        "matched_count": sum(record["matched"] for record in records),
        "p50_latency_ms": round(statistics.median(latencies), 2) if latencies else None,
        "p95_latency_ms": percentile(latencies, 0.95),
        "version_matrix": [
            {"versions": json.loads(versions), "scenario_count": count}
            for versions, count in sorted(version_matrix.items())
        ],
        "records": records,
    }
    output = json.dumps(report, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    if metrics["transport_error_count"]:
        return 1
    if args.require_release_dataset and not report["performance_claim_eligible"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
