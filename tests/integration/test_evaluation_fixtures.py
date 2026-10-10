"""PRI-01 checks: the frozen-set rules hold and the harness reports honestly.

Nothing here asserts detection accuracy. Verdict agreement on fixture-generated output is a
contract check and is never treated as a result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.integration.support import ROOT, assert_contract

sys.path.insert(0, str(ROOT / "evaluation"))

import fixture_set  # noqa: E402
import run_evaluation  # noqa: E402
import validate_fixtures  # noqa: E402


def scenarios(name: str) -> list[dict[str, Any]]:
    return fixture_set.load(fixture_set.SETS[name])["scenarios"]


# --- the sets themselves --------------------------------------------------------------------

def test_committed_sets_satisfy_the_structural_rules() -> None:
    errors, _notes, summary = validate_fixtures.validate()
    assert errors == []
    assert summary["counts"] == {"development": 30, "holdout": 20}
    assert summary["categories"]["conversation"] == 6 and summary["categories"]["failure"] == 5


def test_sets_do_not_overclaim_review() -> None:
    """Two-reviewer sign-off is a human step. The files must not pretend it happened."""
    for name in ("development", "holdout"):
        document = fixture_set.load(fixture_set.SETS[name])
        assert document["metadata"]["freeze"]["status"] == "draft"
        assert document["metadata"]["synthetic"] is True
        if not fixture_set.FREEZE_FILE.exists():
            assert all(not s["reviewers"] for s in document["scenarios"])


def test_no_template_or_thread_crosses_the_split() -> None:
    development = {s["group"] for s in scenarios("development")}
    holdout = {s["group"] for s in scenarios("holdout")}
    assert development.isdisjoint(holdout)


def test_every_request_in_the_sets_is_a_valid_public_request() -> None:
    from tests.integration.support import request_validator

    validator = request_validator()
    for name in ("development", "holdout"):
        for scenario in scenarios(name):
            if scenario["id"] == "HO-19":  # the deliberately malformed request
                assert list(validator.iter_errors(scenario["input"]))
            else:
                assert not list(validator.iter_errors(scenario["input"])), scenario["id"]


def test_canonical_hash_ignores_key_order_and_whitespace() -> None:
    document = fixture_set.load(fixture_set.SETS["development"])
    reordered = json.loads(json.dumps(document, sort_keys=True))
    assert fixture_set.canonical_hash(document) == fixture_set.canonical_hash(reordered)
    reordered["scenarios"][0]["support"] += "!"
    assert fixture_set.canonical_hash(document) != fixture_set.canonical_hash(reordered)


# --- the validator catches what it claims to catch -----------------------------------------

@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Copies of both sets that a test can break, with the validator pointed at them."""
    paths = {}
    for name in ("development", "holdout"):
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(fixture_set.SETS[name].read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(fixture_set, "SETS", {**fixture_set.SETS, **paths})
    monkeypatch.setattr(fixture_set, "FREEZE_FILE", tmp_path / "FREEZE.json")

    def edit(name: str, change) -> None:
        document = json.loads(paths[name].read_text(encoding="utf-8"))
        change(document)
        paths[name].write_text(json.dumps(document), encoding="utf-8")

    return edit


def problems() -> str:
    return "\n".join(validate_fixtures.validate()[0])


def test_validator_rejects_a_real_domain(sandbox) -> None:
    sandbox("development", lambda d: d["scenarios"][0]["input"].update(text="Visit http://bank.com/login now"))
    assert "not a reserved" in problems()


def test_validator_rejects_a_near_duplicate_across_splits(sandbox) -> None:
    def copy_text(document: dict) -> None:
        document["scenarios"][0]["input"]["text"] = scenarios("holdout")[0]["input"]["text"]

    sandbox("development", copy_text)
    assert "near-duplicate across splits" in problems()


def test_validator_rejects_a_group_shared_between_splits(sandbox) -> None:
    sandbox("holdout", lambda d: d["scenarios"][0].update(group=scenarios("development")[0]["group"]))
    assert "appears in both splits" in problems()


def test_validator_rejects_wrong_counts_and_missing_categories(sandbox) -> None:
    sandbox("development", lambda d: d["scenarios"].pop())
    assert "expected 30 scenarios" in problems()
    sandbox("holdout", lambda d: [s.update(category="promotion") for s in d["scenarios"] if s["category"] == "failure"])
    assert "failure scenarios" in problems()


def test_validator_rejects_a_thread_that_is_not_a_conversation(sandbox) -> None:
    sandbox("development", lambda d: next(s for s in d["scenarios"] if s["category"] == "conversation")["input"].update(messages=[]))
    assert "2 to 20 messages" in problems()


def test_validator_refuses_a_frozen_claim_without_two_reviewers(sandbox) -> None:
    sandbox("development", lambda d: d["metadata"]["freeze"].update(status="frozen"))
    message = problems()
    assert "lack two distinct reviewers" in message and "FREEZE.json is missing" in message


def test_freeze_needs_two_distinct_reviewers_and_resolved_ambiguity(sandbox, capsys) -> None:
    def review(document: dict) -> None:
        for scenario in document["scenarios"]:
            scenario["reviewers"] = ["reviewer-one", "reviewer-two"]

    sandbox("development", review)
    assert validate_fixtures.freeze(["development"]) == 1  # ambiguous scenarios have no resolution yet
    assert "ambiguous scenarios lack a resolution" in capsys.readouterr().err

    def resolve(document: dict) -> None:
        for scenario in document["scenarios"]:
            if scenario["ambiguous"]:
                scenario["resolution"] = "agreed after discussion"

    sandbox("development", resolve)
    assert validate_fixtures.freeze(["development"]) == 0
    recorded = fixture_set.load_freeze()["sets"]["development"]["sha256"]
    assert recorded == fixture_set.canonical_hash(fixture_set.load(fixture_set.SETS["development"]))


def test_one_reviewer_listed_twice_is_not_two_reviewers(sandbox, capsys) -> None:
    sandbox("development", lambda d: [s.update(reviewers=["same", "same"]) for s in d["scenarios"]])
    assert validate_fixtures.freeze(["development"]) == 1
    assert "lack two reviewers" in capsys.readouterr().err


# --- the harness ----------------------------------------------------------------------------

class CapturingPoster:
    """Wraps a poster and keeps every 200 response for schema validation."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.bodies: list[dict[str, Any]] = []

    def __call__(self, payload, condition):
        status, body, latency = self.inner(payload, condition)
        if status == 200 and body is not None:
            self.bodies.append(body)
        return status, body, latency


@pytest.mark.parametrize("name", ["bootstrap", "development", "holdout"])
def test_in_process_run_holds_the_contract_for_every_scenario(name: str) -> None:
    document = fixture_set.load(fixture_set.SETS[name])
    with run_evaluation.in_process_poster() as gateway:
        poster = CapturingPoster(gateway)
        records = run_evaluation.run_scenarios(document["scenarios"], poster, can_apply_conditions=True)
    report = run_evaluation.build_report(records, set_name=name, document=document, mode="in-process")

    assert report["skipped"] == []
    assert report["request_errors"] == 0
    assert report["contract_violations"] == {}
    assert report["expectation_failures"] == {}
    assert report["scenario_count"] == len(document["scenarios"])
    for body in poster.bodies:
        assert_contract(body)


def test_failure_scenarios_hit_their_stated_conditions() -> None:
    document = fixture_set.load(fixture_set.SETS["development"])
    failures = [s for s in document["scenarios"] if s["category"] == "failure"]
    with run_evaluation.in_process_poster() as gateway:
        records = run_evaluation.run_scenarios(failures, gateway, can_apply_conditions=True)
    by_id = {r["id"]: r for r in records}
    assert by_id["DEV-28"]["status"] == "partial"
    assert by_id["DEV-29"]["status"] == "complete"
    assert by_id["DEV-30"]["status"] == "unavailable" and by_id["DEV-30"]["actual"] == "unknown"


def test_conditions_are_skipped_not_faked_against_a_running_gateway() -> None:
    calls: list[Any] = []

    def refuse(payload, condition):
        calls.append(payload)
        return 200, None, 0.0

    failures = [s for s in scenarios("development") if s.get("condition")]
    records = run_evaluation.run_scenarios(failures, refuse, can_apply_conditions=False)
    assert calls == [] and all("skipped" in r for r in records)


def test_report_never_claims_fixture_output_as_detection_performance() -> None:
    document = fixture_set.load(fixture_set.SETS["development"])
    with run_evaluation.in_process_poster() as gateway:
        records = run_evaluation.run_scenarios(document["scenarios"], gateway, can_apply_conditions=True)
    report = run_evaluation.build_report(records, set_name="development", document=document, mode="in-process")
    assert report["reportable_as_detection_performance"] is False
    reasons = " ".join(report["reasons_not_reportable"])
    assert "not frozen" in reasons and "in-process" in reasons and "fixture-generated" in reasons
    assert report["fixture_sha256"] == fixture_set.canonical_hash(document)
    assert set(report["scam"]) == {"true_positive", "false_positive", "false_negative", "precision", "recall"}
    assert report["latency_ms"]["basis"] == "in-process call"


def test_report_surfaces_a_violation_instead_of_hiding_it() -> None:
    bad = {"risk_score": 0, "probability_calibrated": True, "coverage": {"text": "complete"},
           "verdict": "suspected_scam", "evidence": [], "status": "unavailable", "severity": "high"}
    found = run_evaluation.contract_violations(bad)
    assert len(found) == 5


def test_holdout_needs_an_explicit_final_run(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["run_evaluation.py", "--in-process", "--set", "holdout"])
    assert run_evaluation.main() == 2
    assert "never tune against it" in capsys.readouterr().err


def test_check_expectations_fails_when_the_gateway_is_unreachable(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def refused(*_args, **_kwargs):
        raise run_evaluation.URLError("connection refused")

    monkeypatch.setattr(run_evaluation, "urlopen", refused)  # Windows takes ~2 s per refused connect
    monkeypatch.setattr(sys, "argv", ["run_evaluation.py", "--set", "bootstrap", "--base-url", "http://127.0.0.1:9/api",
                                      "--check-expectations"])
    assert run_evaluation.main() == 1
    assert "6 errors" in capsys.readouterr().err


def test_output_file_is_only_written_when_requested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "out" / "report.json"
    monkeypatch.setattr(sys, "argv", ["run_evaluation.py", "--in-process", "--set", "bootstrap", "--output", str(target)])
    assert run_evaluation.main() == 0
    assert json.loads(target.read_text(encoding="utf-8"))["set"] == "bootstrap"
