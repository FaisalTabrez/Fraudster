#!/usr/bin/env python3
"""Small no-dependency smoke check for a running Fraudster public origin."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise RuntimeError(detail)


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
    parser.add_argument("--expect", choices=("fixture", "partial", "unavailable", "any"), default="any")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        live_status, live = get_json(f"{base}/health/live")
        ready_status, ready = get_json(f"{base}/health/ready")
        payload = {
            "text": "Urgent: send your OTP to verify your account.",
            "urls": [] if args.expect == "unavailable" else ["http://192.0.2.10/verify"],
            "messages": [],
            "source": "manual",
        }
        analyze_status, analysis = post_json(
            f"{base}/v1/analyze",
            payload,
        )
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"smoke: connection or JSON failure: {exc}", file=sys.stderr)
        return 1

    try:
        require(live_status == 200 and live["status"] == "live", "liveness check failed")
        require(ready_status in (200, 503), f"unexpected readiness HTTP {ready_status}")
        require(analyze_status == 200, f"analysis returned HTTP {analyze_status}")
        require(analysis["risk_score"] is None, "aggregate risk_score must remain null")
        require(analysis["probability_calibrated"] is False, "aggregate probability must not be calibrated")
        require(set(analysis["coverage"]) == {"text", "url", "conversation", "reputation"}, "coverage keys changed")
        if analysis["verdict"] == "suspected_scam":
            require(bool(analysis["evidence"]), "positive scam verdict must cite evidence")
        if args.expect == "fixture":
            require(analysis["fixture_generated"] is True, "fixture mode must identify demo data")
            require(ready_status == 200 and ready["mode"] == "fixture", "fixture mode must report ready")
        if args.expect == "unavailable":
            require(analysis["fixture_generated"] is False, "live unavailable mode must not return fixture data")
            require(analysis["status"] == "unavailable", "expected an unavailable result")
            require(analysis["verdict"] == "unknown", "unavailable result must have an unknown verdict")
        if args.expect == "partial":
            require(analysis["fixture_generated"] is False, "live partial mode must not return fixture data")
            require(analysis["status"] == "partial", "expected a partial result")
            require(analysis["coverage"]["url"] == "complete", "partial mode must preserve URL coverage")
            require(analysis["coverage"]["text"] == "unavailable", "partial mode must expose unavailable text coverage")
    except (KeyError, RuntimeError) as exc:
        print(f"smoke: FAIL {exc}", file=sys.stderr)
        return 1

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
