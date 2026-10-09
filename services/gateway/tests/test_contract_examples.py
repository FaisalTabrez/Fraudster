from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[3]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_request_example_matches_frozen_schema() -> None:
    schema = load(ROOT / "contracts" / "analysis-request.schema.json")
    example = load(ROOT / "contracts" / "examples" / "manual-request.json")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)


def test_response_examples_match_frozen_schema() -> None:
    schema = load(ROOT / "contracts" / "analysis-response.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for name in ("fixture-response.json", "unavailable-response.json"):
        validator.validate(load(ROOT / "contracts" / "examples" / name))


def test_extraction_example_matches_frozen_schema() -> None:
    schema = load(ROOT / "contracts" / "extraction-response.schema.json")
    example = load(ROOT / "contracts" / "examples" / "extraction-unavailable.json")
    Draft202012Validator(schema).validate(example)


def test_response_schema_rejects_ungrounded_suspected_scam() -> None:
    schema = load(ROOT / "contracts" / "analysis-response.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    example = load(ROOT / "contracts" / "examples" / "fixture-response.json")

    without_evidence = deepcopy(example)
    without_evidence["evidence"] = []
    with pytest.raises(ValidationError):
        validator.validate(without_evidence)

    ungrounded = deepcopy(example)
    ungrounded["evidence"][0]["quote"] = None
    ungrounded["evidence"][0]["observed_value"] = None
    with pytest.raises(ValidationError):
        validator.validate(ungrounded)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("text", "t" * 10001),
        ("urls", [f"https://example{index}.test" for index in range(6)]),
        ("conversation_id", "c" * 129),
    ],
)
def test_request_schema_rejects_values_beyond_frozen_limits(field: str, value: object) -> None:
    schema = load(ROOT / "contracts" / "analysis-request.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    example = load(ROOT / "contracts" / "examples" / "manual-request.json")
    example[field] = value
    with pytest.raises(ValidationError):
        validator.validate(example)
