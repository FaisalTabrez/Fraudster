"""Shared loading and hashing for the evaluation fixture sets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
FREEZE_FILE = FIXTURES / "FREEZE.json"

# The bootstrap file holds the six contract examples that predate the sprint sets.
SETS = {
    "bootstrap": FIXTURES / "scenarios.json",
    "development": FIXTURES / "development.json",
    "holdout": FIXTURES / "holdout.json",
}

VERDICTS = ("legitimate", "spam", "suspected_scam", "unknown")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(document: dict[str, Any]) -> str:
    """Hash parsed content, not file bytes, so line endings never change the value."""
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_freeze() -> dict[str, Any] | None:
    return load(FREEZE_FILE) if FREEZE_FILE.exists() else None
