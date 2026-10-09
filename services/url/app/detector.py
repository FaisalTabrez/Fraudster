"""Private, string-only adapter for the pinned phishing-url-detector release."""

from __future__ import annotations

import hashlib

from .upstream.classify import ClassificationResult, classify
from .upstream.model import LogisticModel, load_model


RULE_FEATURES = {
    "ip_host": "has_ip_host",
    "at_symbol": "has_at_symbol",
    "punycode": "has_punycode",
    "homograph": "has_homograph",
    "suspicious_tld": "suspicious_tld",
    "shortener": "is_shortener",
    "no_https": "is_https",
    "many_subdomains": "num_subdomains",
    "suspicious_keywords": "num_suspicious_keywords",
    "suspicious_keyword_single": "num_suspicious_keywords",
    "double_slash_path": "has_double_slash_in_path",
    "many_hyphens": "num_hyphens",
    "long_url": "url_length",
    "digit_heavy_host": "digit_ratio_host",
}


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
        evidence = [item for index, result in enumerate(results) for item in _evidence(index, result)]
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


def _evidence(index: int, result: ClassificationResult) -> list[dict[str, object]]:
    digest = hashlib.sha256(f"{index}\0{result.url}".encode("utf-8")).hexdigest()[:16]
    def item(indicator: str, value: float | int, explanation: str) -> dict[str, object]:
        return {
            "id": f"url-{digest}-{indicator}",
            "indicator_type": indicator,
            "source_module": "url",
            "quote": result.url[:2000],
            "observed_value": value,
            "message_id": None,
            "explanation": explanation,
        }

    observations = [
        item("url_feature_path_length", result.features["path_length"],
             "Observed path length in the submitted URL string."),
    ]
    for hit in result.reasons:
        feature = RULE_FEATURES[hit.rule_id]
        observations.append(item(
            f"url_feature_{feature}", result.features[feature],
            f"Observed {feature} triggered the {hit.points}-point heuristic rule: {hit.reason}",
        ))
    for contribution in result.contributions:
        direction = (
            "raised" if contribution.contribution > 0 else
            "lowered" if contribution.contribution < 0 else "did not change"
        )
        observations.append(item(
            f"url_model_feature_{contribution.name}", contribution.value,
            f"Observed {contribution.name} {direction} the pinned model's output; "
            f"signed logit contribution {contribution.contribution:.4f}. "
            "This is a model explanation, not a verified destination property.",
        ))
    observations.extend([
        item("upstream_heuristic_score_0_100", result.heuristic_score,
             "Rule points summed and capped at 100; this is a heuristic score."),
        item("upstream_model_output_0_1", result.ml_probability,
             "Pinned model output on a 0–1 scale; it is not a calibrated fraud probability."),
        item("upstream_blended_score_0_100", result.final_score,
             f"Upstream blend of model output and heuristic score placed this URL in the "
             f"{result.band} band. The band does not verify the destination or guarantee safety."),
    ])
    return observations
