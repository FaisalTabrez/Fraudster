#!/usr/bin/env python3
"""Replay the API-level steps of docs/demo-script.md and print what actually happened.

This covers the demo steps that are requests to the gateway: the OTP notice, the no-link
scam, the IP-host link, the two-message conversation with a sender change, and the
detectors-unavailable restart. It does not drive the browser, so the on-screen parts of the
demo (Demo data badge, evidence cards, OCR/QR) still need a person or a browser test.

    python tests/e2e/demo_walkthrough.py --base-url http://127.0.0.1:8000 --mode fixture
    python tests/e2e/demo_walkthrough.py --base-url http://127.0.0.1:8000 --mode unavailable
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from smoke import conversation, request_json  # noqa: E402

URGENT = "Act now, your account will be suspended."
SECRET = "Send your OTP to verify the account."


class Walkthrough:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.rows: list[tuple[str, str, str, bool, float]] = []

    def step(self, name: str, payload: dict[str, Any], expected: str, judge: Callable[[dict[str, Any]], tuple[bool, str]]) -> dict[str, Any]:
        started = time.perf_counter()
        status, body = request_json(f"{self.base}/v1/analyze", payload)
        elapsed = (time.perf_counter() - started) * 1000
        body = body if isinstance(body, dict) else {}
        passed, actual = judge(body) if status == 200 else (False, f"HTTP {status}")
        passed = passed and body.get("risk_score") is None
        self.rows.append((name, expected, actual, passed, elapsed))
        return body


def summary(body: dict[str, Any]) -> str:
    coverage = ",".join(f"{k}={v}" for k, v in body.get("coverage", {}).items() if v != "not_applicable")
    return (f"{body.get('status')}/{body.get('verdict')}/{body.get('severity')}; coverage {coverage}; "
            f"{len(body.get('evidence', []))} evidence; risk_score={body.get('risk_score')}; "
            f"fixture_generated={body.get('fixture_generated')}")


def fixture_steps(walk: Walkthrough) -> None:
    walk.step(
        "1. Legitimate OTP notice",
        {"text": "Your OTP is 314159. Do not share it with anyone.", "urls": [], "messages": [], "source": "manual"},
        "complete/legitimate, fixture coverage complete, null score",
        lambda b: (b.get("verdict") == "legitimate" and b.get("coverage", {}).get("text") == "complete"
                   and b.get("fixture_generated") is True, summary(b)),
    )
    text = "Urgent: send your OTP to verify your account."
    walk.step(
        "2. No-link scam asking for an OTP",
        {"text": text, "urls": [], "messages": [], "source": "manual"},
        "suspected_scam with a quote taken from the message",
        lambda b: (b.get("verdict") == "suspected_scam" and bool(b.get("evidence"))
                   and all(e["quote"] in text for e in b["evidence"]), summary(b)),
    )
    walk.step(
        "3. IP-host link",
        {"urls": ["http://192.0.2.10/verify"], "messages": [], "source": "manual"},
        "suspected_scam citing an ip_address_host observation",
        lambda b: (b.get("verdict") == "suspected_scam"
                   and any(e["indicator_type"] == "ip_address_host" and e["observed_value"] == "192.0.2.10"
                           for e in b.get("evidence", [])), summary(b)),
    )
    walk.step(
        "4a. Conversation, same sender",
        conversation(("sender-a", URGENT), ("sender-a", SECRET), protected="me"),
        "suspected_scam citing m1 and m2",
        lambda b: (b.get("verdict") == "suspected_scam"
                   and {e["message_id"] for e in b.get("evidence", [])} == {"m1", "m2"}, summary(b)),
    )
    walk.step(
        "4b. Same conversation, second sender changed",
        conversation(("sender-a", URGENT), ("sender-b", SECRET), protected="me"),
        "no scam verdict, no evidence: the rule does not join different senders",
        lambda b: (b.get("verdict") != "suspected_scam" and not b.get("evidence"), summary(b)),
    )


def unavailable_steps(walk: Walkthrough) -> None:
    walk.step(
        "5a. Text and link with detectors unavailable",
        {"text": "Urgent: send your OTP to verify your account.", "urls": ["http://192.0.2.10/verify"],
         "messages": [], "source": "manual"},
        "unavailable/unknown/unknown, both checks unavailable, no evidence, null score",
        lambda b: (b.get("status") == "unavailable" and (b.get("verdict"), b.get("severity")) == ("unknown", "unknown")
                   and b.get("coverage", {}).get("text") == "unavailable"
                   and b.get("coverage", {}).get("url") == "unavailable"
                   and not b.get("evidence") and b.get("fixture_generated") is False, summary(b)),
    )
    walk.step(
        "5b. Conversation rules still run",
        conversation(("sender-a", URGENT), ("sender-a", SECRET)),
        "suspected_scam from the local rules, coverage conversation=complete",
        lambda b: (b.get("verdict") == "suspected_scam" and b.get("coverage", {}).get("conversation") == "complete",
                   summary(b)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument("--mode", choices=("fixture", "unavailable"), required=True)
    args = parser.parse_args()

    walk = Walkthrough(args.base_url)
    try:
        (fixture_steps if args.mode == "fixture" else unavailable_steps)(walk)
    except OSError as error:
        print(f"walkthrough: could not reach {args.base_url}: {error}", file=sys.stderr)
        return 1

    print("| Step | Expected | Actual | Result | ms |\n|---|---|---|---|---|")
    for name, expected, actual, passed, elapsed in walk.rows:
        print(f"| {name} | {expected} | {actual} | {'PASS' if passed else 'FAIL'} | {elapsed:.0f} |")
    failed = [row[0] for row in walk.rows if not row[3]]
    print(f"\n{len(walk.rows) - len(failed)}/{len(walk.rows)} steps matched.", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
