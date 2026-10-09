from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Source(StrEnum):
    MANUAL = "manual"
    SCREENSHOT = "screenshot"
    QR = "qr"
    CONVERSATION = "conversation"


class Verdict(StrEnum):
    LEGITIMATE = "legitimate"
    SPAM = "spam"
    SUSPECTED_SCAM = "suspected_scam"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class CoverageStatus(StrEnum):
    COMPLETE = "complete"
    NOT_APPLICABLE = "not_applicable"
    NOT_RUN = "not_run"
    UNAVAILABLE = "unavailable"


class AnalysisStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=128)
    sender_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2000)
    timestamp: datetime | None = None


UrlValue = Annotated[str, Field(min_length=1, max_length=2048)]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str | None = Field(default=None, max_length=10000)
    urls: list[UrlValue] = Field(default_factory=list, max_length=5)
    messages: list[Message] = Field(default_factory=list, max_length=20)
    sender_id: str | None = Field(default=None, min_length=1, max_length=128)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)
    source: Source

    @model_validator(mode="after")
    def validate_meaningful_input(self) -> AnalysisRequest:
        if not ((self.text and self.text.strip()) or self.urls or self.messages):
            raise ValueError("at least text, one URL, or one historical message is required")
        if len({message.id for message in self.messages}) != len(self.messages):
            raise ValueError("message ids must be unique within a request")
        return self


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    indicator_type: str = Field(min_length=1, max_length=64)
    source_module: Literal["text", "url", "conversation", "reputation"]
    quote: str | None = Field(default=None, max_length=2000)
    observed_value: str | int | float | bool | None = None
    message_id: str | None = Field(default=None, max_length=128)
    explanation: str = Field(min_length=1, max_length=500)


class ModuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CoverageStatus
    version: str
    raw_score_type: str
    verdict: Verdict = Verdict.UNKNOWN
    severity: Severity = Severity.UNKNOWN
    score: float | int | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    detail: str | None = Field(default=None, max_length=300)
    fixture_generated: bool = False


class Coverage(BaseModel):
    text: CoverageStatus
    url: CoverageStatus
    conversation: CoverageStatus
    reputation: CoverageStatus


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    verdict: Verdict
    severity: Severity
    risk_score: None = None
    probability_calibrated: Literal[False] = False
    evidence: list[Evidence]
    coverage: Coverage
    module_results: dict[str, ModuleResult]
    recommendation: str
    limitations: list[str]
    versions: dict[str, str]
    processing_ms: int = Field(ge=0)
    fixture_generated: bool = False
