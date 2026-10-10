#!/usr/bin/env python3
"""Check the development and holdout sets against the PRI-01 acceptance rules.

Exit status 0 means the structural rules hold. It does not mean the labels have been
reviewed: that is reported separately as freeze readiness, and only a human review of
every label can make a set ready to freeze.
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fixture_set  # noqa: E402

EXPECTED_COUNTS = {"development": 30, "holdout": 20}
REQUIRED_CATEGORIES = (
    "benign_notification", "promotion", "delivery", "job",
    "credential_scam", "fake_offer", "payment_pressure",
)
MIN_CONVERSATIONS = 6
MIN_FAILURES = 5
NEAR_DUPLICATE_JACCARD = 0.6
DETECTOR_CONDITIONS = {"ok", "unavailable", "slow"}
SAFE_SUFFIXES = (".test", ".example", ".invalid", ".localhost")
SAFE_DOMAINS = ("example.com", "example.org", "example.net")
SAFE_NETWORKS = [ipaddress.ip_network(value) for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+", re.I)


def input_texts(scenario: dict[str, Any]) -> list[str]:
    body = scenario.get("input", {})
    texts = [body["text"]] if isinstance(body.get("text"), str) else []
    texts += [message.get("text", "") for message in body.get("messages", []) if isinstance(message, dict)]
    return texts


def input_urls(scenario: dict[str, Any]) -> list[str]:
    body = scenario.get("input", {})
    urls = [url for url in body.get("urls", []) if isinstance(url, str)]
    for text in input_texts(scenario):
        urls += [match.rstrip(".,;:!?)]}") for match in URL_PATTERN.findall(text)]
    return urls


def host_is_reserved(url: str) -> bool:
    host = (urlsplit(url if "://" in url else f"http://{url}").hostname or "").lower()
    if not host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host.endswith(SAFE_SUFFIXES) or host in SAFE_DOMAINS or host.endswith(tuple("." + d for d in SAFE_DOMAINS))
    return any(address in network for network in SAFE_NETWORKS)


def words(scenario: dict[str, Any]) -> frozenset[str]:
    joined = " ".join(input_texts(scenario) + input_urls(scenario)).lower()
    return frozenset(re.findall(r"[a-z]{3,}", joined))


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 0.0


def check_scenario(split: str, scenario: dict[str, Any], errors: list[str]) -> None:
    sid = scenario.get("id", "<missing id>")

    def fail(message: str) -> None:
        errors.append(f"{split}/{sid}: {message}")

    for key in ("id", "split", "group", "category", "case_kind", "provenance", "expected_verdict", "input", "support", "reviewers"):
        if key not in scenario:
            fail(f"missing field '{key}'")
    if scenario.get("expected_verdict") not in fixture_set.VERDICTS:
        fail(f"expected_verdict must be one of {fixture_set.VERDICTS}")
    if scenario.get("provenance") != "synthetic_authored":
        fail("provenance must be 'synthetic_authored' (label real sources explicitly before adding any)")
    if not isinstance(scenario.get("reviewers"), list):
        fail("reviewers must be a list")
    if scenario.get("split") != split:
        fail(f"split must be '{split}' to match the file it is in")
    wanted_kind = {"conversation": "conversation", "failure": "failure"}.get(scenario.get("category"), "detection")
    if scenario.get("case_kind") != wanted_kind:
        fail(f"case_kind must be '{wanted_kind}' for category '{scenario.get('category')}'")
    if not str(scenario.get("support", "")).strip():
        fail("support (the label rationale) is required")
    for url in input_urls(scenario):
        if not host_is_reserved(url):
            fail(f"URL host is not a reserved .test/.example/.invalid name or documentation IP: {url}")

    category = scenario.get("category")
    messages = scenario.get("input", {}).get("messages", [])
    if category == "conversation":
        ids = [message.get("id") for message in messages]
        if not 2 <= len(messages) <= 20:
            fail("a conversation thread needs 2 to 20 messages")
        if len(set(ids)) != len(ids):
            fail("message ids must be unique")
        if scenario.get("input", {}).get("source") != "conversation":
            fail("conversation scenarios must use source 'conversation'")
    elif messages:
        fail("only conversation scenarios may carry messages")

    if category == "failure":
        if not isinstance(scenario.get("expected_http_status"), int):
            fail("failure scenarios must state an integer expected_http_status")
        if scenario.get("expected_http_status") == 200 and "expected_status" not in scenario:
            fail("a failure scenario that returns 200 must state expected_status (complete, partial or unavailable)")
        if "expected_status" in scenario and scenario["expected_status"] not in ("complete", "partial", "unavailable"):
            fail("expected_status must be complete, partial or unavailable")
        for name, state in scenario.get("condition", {}).get("detectors", {}).items():
            if name not in ("text", "url") or state not in DETECTOR_CONDITIONS:
                fail(f"condition.detectors.{name}={state!r} is not one of {sorted(DETECTOR_CONDITIONS)}")


def validate() -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    notes: list[str] = []
    documents: dict[str, dict[str, Any]] = {}
    for split in ("development", "holdout"):
        path = fixture_set.SETS[split]
        if not path.exists():
            errors.append(f"{split}: {path.name} is missing")
            continue
        documents[split] = fixture_set.load(path)

    seen_ids: dict[str, str] = {}
    groups: dict[str, set[str]] = {}
    for split, document in documents.items():
        metadata = document.get("metadata", {})
        scenarios = document.get("scenarios", [])
        if metadata.get("split") != split:
            errors.append(f"{split}: metadata.split must be '{split}'")
        if metadata.get("synthetic") is not True:
            errors.append(f"{split}: metadata.synthetic must be true")
        if len(scenarios) != EXPECTED_COUNTS[split]:
            errors.append(f"{split}: expected {EXPECTED_COUNTS[split]} scenarios, found {len(scenarios)}")
        for scenario in scenarios:
            check_scenario(split, scenario, errors)
            sid = scenario.get("id")
            if sid in seen_ids:
                errors.append(f"{split}/{sid}: id already used in {seen_ids[sid]}")
            seen_ids[sid] = split
            groups.setdefault(scenario.get("group", ""), set()).add(split)

    for group, splits in groups.items():
        if len(splits) > 1:
            errors.append(f"group '{group}' appears in both splits; a template or thread must stay in one split")

    # Near duplicates must share a group inside a split and never cross splits.
    everything = [(split, s) for split, doc in documents.items() for s in doc.get("scenarios", [])]
    vectors = [(split, s, words(s)) for split, s in everything]
    for index, (split_a, a, words_a) in enumerate(vectors):
        for split_b, b, words_b in vectors[index + 1:]:
            if jaccard(words_a, words_b) < NEAR_DUPLICATE_JACCARD:
                continue
            if split_a != split_b:
                errors.append(f"near-duplicate across splits: {a['id']} ({split_a}) and {b['id']} ({split_b})")
            elif a.get("group") != b.get("group"):
                errors.append(f"near-duplicates must share a group: {a['id']} and {b['id']}")

    categories = Counter(s.get("category") for _, s in everything)
    for category in REQUIRED_CATEGORIES:
        if not categories[category]:
            errors.append(f"no scenario with category '{category}'")
    if categories["conversation"] < MIN_CONVERSATIONS:
        errors.append(f"need at least {MIN_CONVERSATIONS} conversation threads, found {categories['conversation']}")
    if categories["failure"] < MIN_FAILURES:
        errors.append(f"need at least {MIN_FAILURES} failure scenarios, found {categories['failure']}")
    verdicts = Counter(s.get("expected_verdict") for _, s in everything)
    for verdict in fixture_set.VERDICTS:
        if not verdicts[verdict]:
            errors.append(f"no scenario expects verdict '{verdict}'")

    # Freeze readiness is reported, and enforced only for sets that claim to be frozen.
    freeze_file = fixture_set.load_freeze()
    for split, document in documents.items():
        freeze = document.get("metadata", {}).get("freeze", {})
        scenarios = document.get("scenarios", [])
        short = [s["id"] for s in scenarios if len({r for r in s.get("reviewers", []) if str(r).strip()}) < 2]
        unresolved = [s["id"] for s in scenarios if s.get("ambiguous") and not str(s.get("resolution", "")).strip()]
        if freeze.get("status") == "frozen":
            if short:
                errors.append(f"{split}: frozen but {len(short)} scenarios lack two distinct reviewers: {', '.join(short)}")
            if unresolved:
                errors.append(f"{split}: frozen but ambiguous scenarios have no resolution: {', '.join(unresolved)}")
            recorded = (freeze_file or {}).get("sets", {}).get(split, {}).get("sha256")
            if recorded != fixture_set.canonical_hash(document):
                errors.append(f"{split}: frozen but FREEZE.json is missing or does not match the content hash")
        else:
            ambiguous = [s["id"] for s in scenarios if s.get("ambiguous")]
            notes.append(
                f"{split}: NOT FROZEN. {len(short)} of {len(scenarios)} scenarios still need two reviewers; "
                f"{len(ambiguous)} are flagged ambiguous ({', '.join(ambiguous) or 'none'})."
            )
    summary = {
        "counts": {split: len(doc.get("scenarios", [])) for split, doc in documents.items()},
        "categories": dict(sorted(categories.items())),
        "verdicts": dict(sorted(verdicts.items())),
        "documents": documents,
    }
    return errors, notes, summary


def freeze(splits: list[str]) -> int:
    """Record content hashes, only when every label has two reviewers and ambiguity is resolved."""
    errors, _notes, summary = validate()
    blocking = [e for e in errors if "frozen but" not in e]
    if blocking:
        print("Cannot freeze: fix the structural errors first.", file=sys.stderr)
        for error in blocking:
            print(f"  - {error}", file=sys.stderr)
        return 1
    existing = fixture_set.load_freeze() or {"sets": {}}
    for split in splits:
        document = summary["documents"][split]
        scenarios = document["scenarios"]
        short = [s["id"] for s in scenarios if len({r for r in s["reviewers"] if str(r).strip()}) < 2]
        unresolved = [s["id"] for s in scenarios if s.get("ambiguous") and not str(s.get("resolution", "")).strip()]
        if short or unresolved:
            print(f"Cannot freeze {split}: {len(short)} scenarios lack two reviewers, "
                  f"{len(unresolved)} ambiguous scenarios lack a resolution.", file=sys.stderr)
            return 1
        stamp = datetime.date.today().isoformat()
        existing["sets"][split] = {"sha256": fixture_set.canonical_hash(document), "frozen_on": stamp}
    fixture_set.FREEZE_FILE.write_text(
        json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {fixture_set.FREEZE_FILE.name}. Now set metadata.freeze.status to 'frozen' and frozen_at "
          "in each frozen file, then rerun this check.")
    return 0


def render_review_sheet(blind: bool = False) -> str:
    """A markdown sheet for the two reviewers: every scenario, its proposed label and why.

    With ``blind`` the proposed label and rationale are left out, so a reviewer labels from the
    text alone and the two sets of labels can be compared afterwards.
    """
    errors, _notes, summary = validate()
    lines = [
        "# Label review sheet",
        "",
        "Generated by `python evaluation/validate_fixtures.py --review-sheet`. Do not edit this file: record",
        "agreement by adding your handle to `reviewers` in the fixture, and resolve disagreement in the pull request.",
        "",
        "Label policy: `suspected_scam` needs deceptive pressure, impersonation, or a request for a secret or payment; "
        "`spam` is unsolicited promotion; `legitimate` is an expected notice or ordinary message with no such request; "
        "`unknown` means the supplied evidence is not enough. Judge the supplied text alone. Do not look at any detector output.",
        "",
        (
            "Blind sheet: the drafter's labels and notes are hidden. Label each scenario from the text alone, then "
            "compare with the fixture labels and discuss every difference. Two different people must review every scenario."
            if blind else
            "For each scenario: (1) form your own label before reading the proposed one, (2) mark agree or disagree, "
            "(3) for disagreement, say which label and why. Two different people must review every scenario."
        ),
        "",
    ]
    if errors:
        lines += ["> The fixtures have structural errors; run the validator and fix them before reviewing.", ""]
    for split, document in summary["documents"].items():
        lines += [f"## {split.capitalize()} ({len(document['scenarios'])} scenarios)", ""]
        for s in document["scenarios"]:
            flag = "  **AMBIGUOUS: needs a discussion and a resolution note**" if s.get("ambiguous") and not blind else ""
            lines += [f"### {s['id']} - {s['category']} ({s['case_kind']}){flag}", ""]
            body = s["input"]
            if body.get("text") is not None:
                lines.append(f"Text: `{body['text']}`")
            for url in body.get("urls", []):
                lines.append(f"URL: `{url}`")
            for message in body.get("messages", []):
                lines.append(f"- `{message['id']}` **{message['sender_id']}**: {message['text']}")
            if body.get("sender_id"):
                lines.append(f"Protected sender (the user, excluded from analysis): `{body['sender_id']}`")
            if s.get("condition"):
                lines.append(f"Condition: `{json.dumps(s['condition'], sort_keys=True)}`")
            expectation = {k: s[k] for k in ("expected_http_status", "expected_status") if k in s}
            if expectation or s.get("expected"):
                lines.append(f"Expected behavior: `{json.dumps({**expectation, **s.get('expected', {})}, sort_keys=True)}`")
            if blind:
                lines += [
                    "",
                    "- Your label (legitimate / spam / suspected_scam / unknown): ",
                    "- Why, in one line: ",
                    "",
                ]
            else:
                lines += [
                    "",
                    f"- Proposed label: **{s['expected_verdict']}**",
                    f"- Rationale: {s['support']}",
                    f"- Reviewers so far: {', '.join(s['reviewers']) or 'none'}",
                    "- [ ] Reviewer 1 agrees   - [ ] Reviewer 2 agrees   - Disagreement / resolution: ",
                    "",
                ]
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", nargs="+", choices=("development", "holdout"),
                        help="record the content hash of reviewed sets in FREEZE.json")
    parser.add_argument("--require-frozen", action="store_true", help="fail unless both sets are frozen")
    parser.add_argument("--review-sheet", nargs="?", const="-", metavar="PATH",
                        help="write the reviewer checklist as markdown to PATH (default: standard output)")
    parser.add_argument("--blind", action="store_true",
                        help="with --review-sheet, hide the proposed labels so a reviewer labels independently")
    args = parser.parse_args()
    if args.blind and not args.review_sheet:
        parser.error("--blind only applies to --review-sheet")
    if args.review_sheet:
        sheet = render_review_sheet(blind=args.blind)
        if args.review_sheet == "-":
            sys.stdout.write(sheet)
        else:
            target = Path(args.review_sheet)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(sheet, encoding="utf-8")
            print(f"Wrote {target}")
        return 0
    if args.freeze:
        return freeze(args.freeze)

    errors, notes, summary = validate()
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    for note in notes:
        print(f"NOTE  {note}")
    if args.require_frozen and any("NOT FROZEN" in note for note in notes):
        errors.append("sets are not frozen")
    if errors:
        print(f"{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    counts = summary["counts"]
    print(f"OK  development={counts.get('development')} holdout={counts.get('holdout')}  "
          f"categories={summary['categories']}  verdicts={summary['verdicts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
