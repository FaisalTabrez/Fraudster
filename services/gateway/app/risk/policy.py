from __future__ import annotations

from ..models import (
    AnalysisStatus,
    CoverageStatus,
    ModuleResult,
    Severity,
    Verdict,
)


def analysis_status(results: dict[str, ModuleResult]) -> AnalysisStatus:
    applicable = [
        result.status
        for name, result in results.items()
        if name != "reputation" and result.status != CoverageStatus.NOT_APPLICABLE
    ]
    completed = sum(status == CoverageStatus.COMPLETE for status in applicable)
    unavailable = sum(status == CoverageStatus.UNAVAILABLE for status in applicable)
    if unavailable and completed == 0:
        return AnalysisStatus.UNAVAILABLE
    if unavailable:
        return AnalysisStatus.PARTIAL
    return AnalysisStatus.COMPLETE


def aggregate_verdict(
    status: AnalysisStatus, results: dict[str, ModuleResult]
) -> tuple[Verdict, Severity]:
    if status == AnalysisStatus.UNAVAILABLE:
        return Verdict.UNKNOWN, Severity.UNKNOWN

    available = [result for result in results.values() if result.status == CoverageStatus.COMPLETE]
    scam = next((result for result in available if result.verdict == Verdict.SUSPECTED_SCAM and result.evidence), None)
    if scam:
        return Verdict.SUSPECTED_SCAM, Severity.HIGH
    if any(result.verdict == Verdict.SPAM for result in available):
        return Verdict.SPAM, Severity.LOW
    if available and all(result.verdict == Verdict.LEGITIMATE for result in available):
        return Verdict.LEGITIMATE, Severity.LOW
    return Verdict.UNKNOWN, Severity.UNKNOWN


def recommendation(verdict: Verdict, status: AnalysisStatus) -> str:
    if verdict == Verdict.SUSPECTED_SCAM:
        return "Pause and verify the request through a separate trusted channel before responding or paying."
    if verdict == Verdict.SPAM:
        return "Treat this as unsolicited content and avoid interacting unless you independently recognize the sender."
    if status != AnalysisStatus.COMPLETE:
        return "Some checks were unavailable. Verify independently before acting on the message or link."
    if verdict == Verdict.LEGITIMATE:
        return "No authored warning rule matched, but continue to verify unexpected requests independently."
    return "The available checks were inconclusive. Verify the sender and requested action independently."
