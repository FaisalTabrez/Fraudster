#!/usr/bin/env python3
"""No-dependency smoke check for a running Fraudster gateway or public origin.

Run it against the gateway directly (``--base-url http://127.0.0.1:8000``) or through the
web origin (``--base-url http://127.0.0.1:4173/api``). It makes no outbound requests other
than to the given base URL and needs no provider key.

``--expect fixture``      the gateway runs with DEMO_MODE=true
``--expect partial``      DEMO_MODE=false with URL complete and text unavailable
``--expect unavailable``  DEMO_MODE=false; submit text only and require unavailable/unknown
``--expect live-no-key``  DEMO_MODE=false with the real services running but no text provider key,
                          which is the default Docker stack: text is unavailable, URL checks may complete
``--expect any``          accept any of these, but check every invariant that must hold in all of them
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

COVERAGE_KEYS = {"text", "url", "conversation", "reputation"}
URGENT = "Act now, your account will be suspended."
SECRET = "Send your OTP to verify the account."


def request_json(url: str, payload: Any = None, *, raw: bytes | None = None) -> tuple[int, Any]:
    data = raw if raw is not None else (None if payload is None else json.dumps(payload).encode("utf-8"))
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="GET" if data is None else "POST")
    try:
        with urlopen(request, timeout=15) as response:
            status, body = response.status, response.read()
    except HTTPError as error:
        status, body = error.code, error.read()
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, None


class Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []

    def check(self, condition: bool, description: str) -> None:
        if condition:
            self.passed += 1
        else:
            self.failures.append(description)


def conversation(*pairs: tuple[str, str], protected: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "messages": [{"id": f"m{i}", "sender_id": sender, "text": text} for i, (sender, text) in enumerate(pairs, 1)],
        "urls": [],
        "source": "conversation",
    }
    if protected:
        body["sender_id"] = protected
    return body


def check_contract(checks: Checks, label: str, body: dict[str, Any]) -> None:
    checks.check(body.get("risk_score") is None, f"{label}: risk_score must be null")
    checks.check(body.get("probability_calibrated") is False, f"{label}: probability_calibrated must be false")
    checks.check(set(body.get("coverage", {})) == COVERAGE_KEYS, f"{label}: coverage must have the four contract fields")
    if body.get("verdict") == "suspected_scam":
        checks.check(bool(body.get("evidence")), f"{label}: a positive scam verdict must cite evidence")
    if body.get("status") == "unavailable":
        checks.check((body.get("verdict"), body.get("severity")) == ("unknown", "unknown"),
                     f"{label}: an unavailable result must be unknown/unknown, never clean")


def run(base: str, expect: str) -> tuple[Checks, dict[str, Any]]:
    checks = Checks()
    live_status, live = request_json(f"{base}/health/live")
    ready_status, ready = request_json(f"{base}/health/ready")
    checks.check(live_status == 200 and (live or {}).get("status") == "live", "health/live must report live")
    checks.check(ready_status in (200, 503), "health/ready must answer 200 or 503")

    url = "http://192.0.2.10/verify"
    status, analysis = request_json(f"{base}/v1/analyze", {
        "text": "Urgent: send your OTP to verify your account.",
        "urls": [] if expect == "unavailable" else [url],
        "messages": [],
        "source": "manual",
    })
    checks.check(status == 200 and isinstance(analysis, dict), "analyze must answer 200 with a JSON object")
    analysis = analysis if isinstance(analysis, dict) else {}
    check_contract(checks, "manual request", analysis)

    if expect == "fixture":
        checks.check(analysis.get("fixture_generated") is True, "fixture mode must mark responses as demo data")
        checks.check(ready_status == 200 and (ready or {}).get("mode") == "fixture", "fixture mode must be ready")
    if expect == "unavailable":
        checks.check(analysis.get("fixture_generated") is False, "default mode must not return fixture data")
        checks.check(analysis.get("status") == "unavailable" and analysis.get("verdict") == "unknown",
                     "default mode without detectors must be unavailable/unknown")
        checks.check(ready_status == 503, "default mode without detectors must not report ready")

    if expect == "partial":
        checks.check(analysis.get("fixture_generated") is False, "live partial mode must not return fixture data")
        checks.check(analysis.get("status") == "partial", "live mode must preserve a partial result")
        checks.check(analysis.get("coverage", {}).get("url") == "complete",
                     "partial mode must preserve completed URL coverage")
        checks.check(analysis.get("coverage", {}).get("text") == "unavailable",
                     "partial mode must expose unavailable text coverage")

    if expect == "live-no-key":
        checks.check(analysis.get("fixture_generated") is False, "live mode must not return fixture data")
        checks.check(analysis.get("coverage", {}).get("text") == "unavailable",
                     "without a provider key the text check must be unavailable")
        checks.check(analysis.get("status") in ("partial", "unavailable"),
                     "without a provider key the result must be partial or unavailable, never complete")
        checks.check(ready_status == 503, "live mode without a provider key must not report ready")

    # A link-only request still returns a contract-valid result.
    status, body = request_json(f"{base}/v1/analyze", {"urls": [url], "messages": [], "source": "manual"})
    checks.check(status == 200 and isinstance(body, dict), "a URL-only request must be accepted")
    check_contract(checks, "URL-only request", body or {})

    # Sender separation holds in every mode: the conversation rules are local.
    for label, payload, scam, ids in (
        ("same sender", conversation(("sender-a", URGENT), ("sender-a", SECRET)), True, {"m1", "m2"}),
        ("different senders", conversation(("sender-a", URGENT), ("sender-b", SECRET)), False, set()),
        ("protected sender", conversation(("me", URGENT), ("me", SECRET), protected="me"), False, set()),
    ):
        status, body = request_json(f"{base}/v1/analyze", payload)
        body = body if isinstance(body, dict) else {}
        checks.check(status == 200, f"{label}: conversation request must be accepted")
        check_contract(checks, label, body)
        checks.check((body.get("verdict") == "suspected_scam") is scam, f"{label}: scam verdict must be {scam}")
        checks.check({e.get("message_id") for e in body.get("evidence", [])} == ids,
                     f"{label}: evidence must cite exactly the supplied message ids {sorted(ids)}")

    # Malformed requests are refused, never analysed.
    for label, payload, raw in (
        ("blank text", {"text": "   ", "urls": [], "messages": [], "source": "manual"}, None),
        ("no input", {"urls": [], "messages": [], "source": "manual"}, None),
        ("unknown source", {"text": "hi", "source": "telepathy"}, None),
        ("six URLs", {"urls": [f"http://a{i}.test/" for i in range(6)], "source": "manual"}, None),
        ("not JSON", None, b"not json"),
    ):
        status, body = request_json(f"{base}/v1/analyze", payload, raw=raw)
        checks.check(status == 422, f"malformed request ({label}) must be rejected with 422, got {status}")
        checks.check(not (isinstance(body, dict) and "analysis_id" in body), f"malformed request ({label}) must not be analysed")

    summary = {
        "live": (live or {}).get("status"),
        "ready_http": ready_status,
        "mode": (ready or {}).get("mode"),
        "analysis_status": analysis.get("status"),
        "verdict": analysis.get("verdict"),
        "fixture_generated": analysis.get("fixture_generated"),
        "checks_passed": checks.passed,
    }
    return checks, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument(
        "--expect",
        choices=("fixture", "partial", "unavailable", "live-no-key", "any"),
        default="any",
    )
    args = parser.parse_args()

    try:
        checks, summary = run(args.base_url.rstrip("/"), args.expect)
    except (URLError, TimeoutError, OSError) as error:
        print(f"smoke: could not reach {args.base_url}: {error}", file=sys.stderr)
        return 1
    for failure in checks.failures:
        print(f"smoke: FAIL {failure}", file=sys.stderr)
    print(json.dumps({**summary, "checks_failed": len(checks.failures)}, indent=2))
    return 1 if checks.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
