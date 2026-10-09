#!/usr/bin/env python3
"""Run the authored scenarios against a configured gateway and report measured output."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen


def post(url: str, payload: dict) -> tuple[dict, float]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=15) as response:
        body = json.load(response)
    return body, (time.perf_counter() - started) * 1000


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return round(ordered[index], 2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "scenarios.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    fixture_document = json.loads(args.fixtures.read_text(encoding="utf-8"))
    records = []
    latencies = []
    confusion: Counter[str] = Counter()
    for scenario in fixture_document["scenarios"]:
        response, latency_ms = post(f"{args.base_url.rstrip('/')}/v1/analyze", scenario["input"])
        expected = scenario["expected_verdict"]
        actual = response["verdict"]
        latencies.append(latency_ms)
        confusion[f"{expected}->{actual}"] += 1
        records.append(
            {
                "id": scenario["id"],
                "expected": expected,
                "actual": actual,
                "status": response["status"],
                "fixture_generated": response["fixture_generated"],
                "latency_ms": round(latency_ms, 2),
                "matched": expected == actual,
            }
        )

    report = {
        "scope": "authored synthetic bootstrap scenarios; not a real-world accuracy claim",
        "scenario_count": len(records),
        "fixture_document": fixture_document["metadata"],
        "confusion": dict(sorted(confusion.items())),
        "matched_count": sum(record["matched"] for record in records),
        "p50_latency_ms": round(statistics.median(latencies), 2) if latencies else None,
        "p95_latency_ms": percentile(latencies, 0.95),
        "records": records,
    }
    output = json.dumps(report, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
