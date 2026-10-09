from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable
from uuid import uuid4

from fastapi import APIRouter, Request, Response, status

from ..clients.detectors import not_applicable_result, unavailable_result
from ..models import (
    AnalysisRequest,
    AnalysisResponse,
    Coverage,
    CoverageStatus,
    Evidence,
    ModuleResult,
    Severity,
    Verdict,
)
from ..risk.conversation import evaluate_conversation
from ..risk.fixtures import fixture_text_result, fixture_url_result
from ..risk.policy import aggregate_verdict, analysis_status, recommendation


router = APIRouter(prefix="/v1")
URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+", re.I)


def collect_urls(request: AnalysisRequest) -> list[str]:
    candidates = list(request.urls)
    if request.text:
        candidates.extend(match.rstrip(".,;:!?)]}") for match in URL_PATTERN.findall(request.text))
    seen: set[str] = set()
    deduplicated: list[str] = []
    for value in candidates:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            deduplicated.append(value)
    return deduplicated[:5]


def _ground_detector_result(name: str, result: ModuleResult, inputs: list[str]) -> ModuleResult:
    """Keep detector evidence tied to the submitted text or URL strings."""
    if result.status not in (CoverageStatus.COMPLETE, CoverageStatus.UNAVAILABLE):
        return unavailable_result(name, f"{name} service returned an invalid coverage status")
    if result.status == CoverageStatus.UNAVAILABLE:
        return unavailable_result(name, result.detail or f"{name} service was unavailable")

    evidence = [
        item for item in result.evidence
        if item.source_module == name
        and item.message_id is None
        and (
            (bool(item.quote and item.quote.strip()) and any(item.quote in value for value in inputs))
            or (
                name == "url" and isinstance(item.observed_value, str)
                and bool(item.observed_value.strip())
                and any(item.observed_value in value for value in inputs)
            )
        )
    ]
    result = result.model_copy(update={"evidence": evidence})
    if result.verdict == Verdict.SUSPECTED_SCAM and not evidence:
        result = result.model_copy(update={
            "verdict": Verdict.UNKNOWN,
            "severity": Severity.UNKNOWN,
            "score": None,
            "detail": "Detector warning lacked evidence in the supplied input.",
        })
    return result


async def _collect_live_results(
    tasks: dict[str, Awaitable[ModuleResult]], timeout_seconds: float
) -> dict[str, ModuleResult]:
    named_tasks = {name: asyncio.create_task(task) for name, task in tasks.items()}
    if not named_tasks:
        return {}
    done, pending = await asyncio.wait(named_tasks.values(), timeout=timeout_seconds)
    reverse = {task: name for name, task in named_tasks.items()}
    results: dict[str, ModuleResult] = {}
    for task in done:
        name = reverse[task]
        try:
            results[name] = task.result()
        except (Exception, asyncio.CancelledError):
            results[name] = unavailable_result(name, f"{name} service response was unavailable")
    for task in pending:
        name = reverse[task]
        task.cancel()
        results[name] = unavailable_result(name, "overall analysis deadline exceeded")
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    return results


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(payload: AnalysisRequest, request: Request) -> AnalysisResponse:
    started = time.perf_counter()
    settings = request.app.state.settings
    clients = request.app.state.detectors
    urls = collect_urls(payload)

    results: dict[str, ModuleResult] = {
        "text": not_applicable_result("text"),
        "url": not_applicable_result("URL"),
        "conversation": not_applicable_result("conversation"),
        "reputation": ModuleResult(
            status=CoverageStatus.NOT_RUN,
            version="not_configured",
            raw_score_type="none",
            detail="No reputation provider is configured in the bootstrap.",
        ),
    }

    if payload.messages:
        results["conversation"] = evaluate_conversation(payload.messages, payload.sender_id)

    if settings.demo_mode:
        if payload.text:
            results["text"] = fixture_text_result(payload.text)
        if urls:
            results["url"] = fixture_url_result(urls)
    else:
        tasks: dict[str, Awaitable[ModuleResult]] = {}
        if payload.text:
            tasks["text"] = clients.text(payload.text)
        if urls:
            tasks["url"] = clients.url(urls)
        live_results = await _collect_live_results(tasks, settings.analysis_timeout_seconds)
        for name, result in live_results.items():
            inputs = [payload.text] if name == "text" and payload.text else urls
            results[name] = _ground_detector_result(name, result, inputs)

    response_status = analysis_status(results)
    verdict, severity = aggregate_verdict(response_status, results)
    evidence: list[Evidence] = [item for result in results.values() for item in result.evidence]
    limitations = ["A result from this prototype is not a guarantee that a message or URL is safe."]
    if settings.demo_mode:
        limitations.append("Detector outputs are fixture-generated demo data, not live model inference.")
    unavailable = [name for name, result in results.items() if result.status == CoverageStatus.UNAVAILABLE]
    if unavailable:
        limitations.append(f"Unavailable checks: {', '.join(unavailable)}.")

    return AnalysisResponse(
        analysis_id=str(uuid4()),
        status=response_status,
        verdict=verdict,
        severity=severity,
        evidence=evidence,
        coverage=Coverage(**{name: result.status for name, result in results.items()}),
        module_results=results,
        recommendation=recommendation(verdict, response_status),
        limitations=limitations,
        versions={"gateway": "0.1.0", **{name: result.version for name, result in results.items()}},
        processing_ms=max(0, round((time.perf_counter() - started) * 1000)),
        fixture_generated=settings.demo_mode,
    )


@router.post("/extract", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
async def extract_unavailable(response: Response) -> dict[str, object]:
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "unavailable",
        "text": None,
        "boxes": [],
        "image": None,
        "detail": "OCR is an optional P1 adapter and is not installed in the bootstrap.",
    }
