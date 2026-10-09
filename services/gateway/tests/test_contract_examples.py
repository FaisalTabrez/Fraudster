from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


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
