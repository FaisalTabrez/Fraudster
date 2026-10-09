"""Private, string-only adapter for the pinned phishing-url-detector release."""

from __future__ import annotations

import hashlib

from .upstream.classify import ClassificationResult, classify
from .upstream.model import LogisticModel, load_model


class DetectorUnavailable(RuntimeError):
    """Raised when the reviewed JSON model cannot be used."""


class UrlDetector:
    upstream_commit = "8648994a2e2ff25eac8fe23b46705ecbcd27f296"
    version = f"phishing-url-detector@{upstream_commit[:12]}"

    def __init__(self) -> None:
        try:
            self._model: LogisticModel | None = load_model()
        except (OSError, ValueError, KeyError, TypeError):
            self._model = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    async def predict(self, urls: list[str]) -> dict[str, object]:
        if self._model is None:
            raise DetectorUnavailable("Pinned URL model metadata is unavailable.")
        if not urls:
            raise DetectorUnavailable("No URL input was supplied.")

        results = [classify(url, model=self._model) for url in urls]
        verdict, severity = _aggregate_band(results)
        evidence = [_evidence(index, result) for index, result in enumerate(results)]
        return {
            "status": "complete",
            "version": self.version,
            "raw_score_type": "upstream_blended_score_0_100",
            "verdict": verdict,
            "severity": severity,
            "score": max(result.final_score for result in results),
            "evidence": evidence,
            "detail": "String-only URL analysis. A lower upstream band is not a safety guarantee.",
            "fixture_generated": False,
        }


def _aggregate_band(results: list[ClassificationResult]) -> tuple[str, str]:
    if any(result.band == "Dangerous" for result in results):
        return "suspected_scam", "high"
    if any(result.band == "Suspicious" for result in results):
        return "unknown", "medium"
    return "legitimate", "low"


def _evidence(index: int, result: ClassificationResult) -> dict[str, object]:
    digest = hashlib.sha256(f"{index}\0{result.url}".encode("utf-8")).hexdigest()[:16]
    return {
        "id": f"url-{digest}",
        "indicator_type": "string_only_url_classification",
        "source_module": "url",
        "quote": result.url[:2000],
        "observed_value": result.final_score,
        "message_id": None,
        "explanation": (
            f"The pinned string-only model and heuristic rules placed this URL in the "
            f"{result.band} band. This does not verify the destination or guarantee safety."
        ),
    }
