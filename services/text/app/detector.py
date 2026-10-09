from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


ADAPTER_VERSION = "smishx-text-adapter-0.1.0"
PROMPT_VERSION = "smishx-text-v1"
SMISHX_COMMIT = "116a8c827741e0572563f678d25ed04306b1e3ff"
DEFAULT_API_BASE_URL = "https://api.openai.com/v1"

Verdict = Literal["legitimate", "spam", "suspected_scam", "unknown"]
Severity = Literal["low", "medium", "high", "unknown"]


class DetectorUnavailable(RuntimeError):
    """Raised when the configured provider cannot produce a validated result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ProviderEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    indicator_type: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    quote: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=500)

    @field_validator("quote")
    @classmethod
    def reject_blank_quote(cls, quote: str) -> str:
        if not quote.strip():
            raise ValueError("evidence quote cannot be blank")
        return quote


class ProviderPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Verdict
    severity: Severity
    evidence: list[ProviderEvidence] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_category(self) -> ProviderPrediction:
        allowed_severity: dict[str, set[str]] = {
            "legitimate": {"low"},
            "spam": {"low", "medium"},
            "suspected_scam": {"medium", "high"},
            "unknown": {"unknown"},
        }
        if self.severity not in allowed_severity[self.verdict]:
            raise ValueError("severity is inconsistent with verdict")
        if self.verdict != "unknown" and not self.evidence:
            raise ValueError("a non-unknown verdict requires quoted evidence")
        return self


SYSTEM_PROMPT = f"""You are the text-only classification stage of Fraudster.
This prompt is version {PROMPT_VERSION} and adapts the category semantics reviewed in
SmishX commit {SMISHX_COMMIT}. Classify only the submitted message text.

Return exactly one verdict:
- legitimate: an expected notification or ordinary personal/work message without a scam request;
- spam: unsolicited advertising or promotion without evidence of credential/payment theft;
- suspected_scam: deceptive pressure, impersonation, or a request for credentials, secrets, or payment;
- unknown: the text alone does not support one of the other categories.

Evidence must quote exact, contiguous text from the submitted message. Do not rewrite quotes.
Use lowercase snake_case indicator_type values. Do not open, follow, expand, or browse any URL.
Do not claim a sender, brand, domain, or link is authentic. Do not output a probability, score,
or model confidence. If the text is ambiguous, return unknown with severity unknown.
"""


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "severity", "evidence"],
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["legitimate", "spam", "suspected_scam", "unknown"],
        },
        "severity": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "evidence": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["indicator_type", "quote", "explanation"],
                "properties": {
                    "indicator_type": {
                        "type": "string",
                        "pattern": "^[a-z0-9_]{1,64}$",
                    },
                    "quote": {"type": "string", "minLength": 1, "maxLength": 2000},
                    "explanation": {"type": "string", "minLength": 1, "maxLength": 500},
                },
            },
        },
    },
}


@dataclass(frozen=True)
class TextDetector:
    model_name: str
    api_key_configured: bool
    api_key: str | None = None
    api_base_url: str = DEFAULT_API_BASE_URL
    request_timeout_seconds: float = 8.0

    @property
    def state(self) -> str:
        if not self.api_key_configured or not self.api_key or self.model_name == "configure-me":
            return "not_configured"
        return "ready"

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    @property
    def version(self) -> str:
        return f"{ADAPTER_VERSION};model={self.model_name};prompt={PROMPT_VERSION}"

    async def predict(self, text: str) -> dict[str, object]:
        if not self.ready:
            raise DetectorUnavailable(
                "not_configured",
                "Set TEXT_MODEL and TEXT_API_KEY before using the live text adapter.",
            )

        try:
            payload = await self._call_provider(text)
            prediction = ProviderPrediction.model_validate(payload)
            return self._validated_result(text, prediction)
        except DetectorUnavailable:
            raise
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise DetectorUnavailable(
                "invalid_provider_response",
                "The text provider returned output that did not match the required schema.",
            ) from exc

    async def _call_provider(self, text: str) -> dict[str, Any]:
        endpoint = f"{self.api_base_url.rstrip('/')}/chat/completions"
        request = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "fraudster_text_analysis",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                },
            },
        }
        try:
            async with asyncio.timeout(self.request_timeout_seconds):
                async with httpx.AsyncClient(
                    timeout=self.request_timeout_seconds,
                    follow_redirects=False,
                ) as client:
                    async with client.stream(
                        "POST",
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request,
                    ) as response:
                        response.raise_for_status()
                        response_body = await response.aread()
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise DetectorUnavailable(
                "provider_timeout", "The text provider deadline was exceeded."
            ) from exc
        except httpx.HTTPError as exc:
            raise DetectorUnavailable(
                "provider_unavailable", "The text provider request failed."
            ) from exc

        body = json.loads(response_body)
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("provider message content must be a JSON string")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise TypeError("provider prediction must be an object")
        return parsed

    def _validated_result(
        self, text: str, prediction: ProviderPrediction | dict[str, Any]
    ) -> dict[str, object]:
        if isinstance(prediction, dict):
            prediction = ProviderPrediction.model_validate(prediction)

        evidence: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for candidate in prediction.evidence:
            if candidate.quote not in text:
                raise DetectorUnavailable(
                    "invalid_provider_response",
                    "The text provider returned an evidence quote not found in the submitted text.",
                )
            key = (candidate.indicator_type, candidate.quote)
            if key in seen:
                continue
            seen.add(key)
            digest = hashlib.sha256(
                f"{candidate.indicator_type}:{candidate.quote}".encode("utf-8")
            ).hexdigest()[:16]
            evidence.append(
                {
                    "id": f"text-{digest}",
                    "indicator_type": candidate.indicator_type,
                    "source_module": "text",
                    "quote": candidate.quote,
                    "observed_value": None,
                    "message_id": None,
                    "explanation": candidate.explanation,
                }
            )

        if prediction.verdict != "unknown" and not evidence:
            raise DetectorUnavailable(
                "invalid_provider_response",
                "The text provider returned a positive category without valid quoted evidence.",
            )

        return {
            "status": "complete",
            "version": self.version,
            "raw_score_type": "categorical_model_output",
            "verdict": prediction.verdict,
            "severity": prediction.severity,
            "score": None,
            "evidence": evidence,
            "detail": (
                f"Text-only analysis using prompt {PROMPT_VERSION}; URLs were not opened, "
                "followed, or expanded."
            ),
            "fixture_generated": False,
        }
