#!/usr/bin/env python3
"""Small no-dependency smoke check for a running Fraudster public origin."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def get_json(url: str) -> tuple[int, dict]:
    try:
        with urlopen(url, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def post_json(url: str, payload: dict) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument("--expect", choices=("fixture", "unavailable", "any"), default="any")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        live_status, live = get_json(f"{base}/health/live")
        ready_status, ready = get_json(f"{base}/health/ready")
        analyze_status, analysis = post_json(
            f"{base}/v1/analyze",
            {
                "text": "Urgent: send your OTP to verify your account.",
                "urls": ["http://192.0.2.10/verify"],
                "messages": [],
                "source": "manual",
            },
        )
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"smoke: connection or JSON failure: {exc}", file=sys.stderr)
        return 1

    assert live_status == 200 and live["status"] == "live"
    assert ready_status in (200, 503)
    assert analyze_status == 200
    assert analysis["risk_score"] is None
    assert analysis["probability_calibrated"] is False
    assert set(analysis["coverage"]) == {"text", "url", "conversation", "reputation"}
    if analysis["verdict"] == "suspected_scam":
        assert analysis["evidence"], "positive scam verdict must cite evidence"
    if args.expect == "fixture":
        assert analysis["fixture_generated"] is True
        assert ready_status == 200 and ready["mode"] == "fixture"
    if args.expect == "unavailable":
        assert analysis["fixture_generated"] is False
        assert analysis["status"] == "unavailable"
        assert analysis["verdict"] == "unknown"

    print(
        json.dumps(
            {
                "live": live["status"],
                "ready_http": ready_status,
                "mode": ready.get("mode"),
                "analysis_status": analysis["status"],
                "verdict": analysis["verdict"],
                "fixture_generated": analysis["fixture_generated"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
