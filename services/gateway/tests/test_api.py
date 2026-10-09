from __future__ import annotations

import asyncio

import httpx
import pytest

from services.gateway.app.clients.detectors import unavailable_result
from services.gateway.app.main import create_app
from services.gateway.app.models import CoverageStatus, Evidence, ModuleResult, Severity, Verdict
from services.gateway.app.settings import Settings


async def request(app, method: str, path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.request(method, path, **kwargs)


class UnavailableClients:
    async def text(self, _text: str) -> ModuleResult:
        return unavailable_result("text", "text adapter not configured")

    async def url(self, _urls: list[str]) -> ModuleResult:
        return unavailable_result("url", "URL adapter not configured")


class PartialClients:
    async def text(self, _text: str) -> ModuleResult:
        await asyncio.sleep(0.1)
        return unavailable_result("text", "unexpected completion")

    async def url(self, urls: list[str]) -> ModuleResult:
        return ModuleResult(
            status=CoverageStatus.COMPLETE,
            version="test-url-1",
            raw_score_type="test_feature",
            verdict=Verdict.LEGITIMATE,
            severity=Severity.LOW,
            score=0,
            evidence=[
                Evidence(
                    id="url-test-evidence",
                    indicator_type="submitted_url",
                    source_module="url",
                    quote=urls[0],
                    observed_value=0,
                    explanation="Test stub completed before the gateway deadline.",
                )
            ],
        )


class ConcurrentClients:
    def __init__(self) -> None:
        self.started: set[str] = set()
        self.both_started = asyncio.Event()

    async def _complete(self, name: str) -> ModuleResult:
        self.started.add(name)
        if self.started == {"text", "url"}:
            self.both_started.set()
        await asyncio.wait_for(self.both_started.wait(), timeout=0.25)
        return ModuleResult(
            status=CoverageStatus.COMPLETE,
            version=f"test-{name}-1",
            raw_score_type="test_result",
            verdict=Verdict.LEGITIMATE,
            severity=Severity.LOW,
            score=0,
        )

    async def text(self, _text: str) -> ModuleResult:
        return await self._complete("text")

    async def url(self, _urls: list[str]) -> ModuleResult:
        return await self._complete("url")


@pytest.mark.asyncio
async def test_fixture_mode_is_explicit_and_never_returns_aggregate_score() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "text": "Send your OTP to verify the account.",
            "urls": [],
            "messages": [],
            "source": "manual",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["fixture_generated"] is True
    assert payload["risk_score"] is None
    assert payload["probability_calibrated"] is False
    assert payload["verdict"] == "suspected_scam"
    assert payload["evidence"]


@pytest.mark.asyncio
async def test_all_applicable_detectors_unavailable_is_unknown() -> None:
    settings = Settings(demo_mode=False)
    app = create_app(settings, detectors=UnavailableClients())
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "text": "hello",
            "urls": ["https://example.test"],
            "messages": [],
            "source": "manual",
        },
    )
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["verdict"] == "unknown"
    assert payload["severity"] == "unknown"
    assert payload["risk_score"] is None
    assert payload["coverage"]["text"] == "unavailable"
    assert payload["coverage"]["url"] == "unavailable"


@pytest.mark.asyncio
async def test_applicable_detector_calls_start_concurrently() -> None:
    clients = ConcurrentClients()
    app = create_app(
        Settings(demo_mode=False, analysis_timeout_seconds=0.5),
        detectors=clients,
    )
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "text": "hello",
            "urls": ["https://example.test"],
            "messages": [],
            "source": "manual",
        },
    )
    payload = response.json()
    assert response.status_code == 200
    assert clients.started == {"text", "url"}
    assert payload["status"] == "complete"
    assert payload["coverage"]["text"] == "complete"
    assert payload["coverage"]["url"] == "complete"


@pytest.mark.asyncio
async def test_one_module_timeout_preserves_completed_result() -> None:
    settings = Settings(demo_mode=False, analysis_timeout_seconds=0.02)
    app = create_app(settings, detectors=PartialClients())
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "text": "hello",
            "urls": ["https://example.test/path"],
            "messages": [],
            "source": "manual",
        },
    )
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["coverage"]["text"] == "unavailable"
    assert payload["coverage"]["url"] == "complete"
    assert any(item["id"] == "url-test-evidence" for item in payload["evidence"])


@pytest.mark.asyncio
async def test_wrong_request_shape_is_rejected() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={"text": "", "urls": [], "messages": [], "source": "manual", "extra": "no"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_request_accepts_documented_maximum_lengths() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    url_prefix = "https://example.test/"
    urls = [
        f"{url_prefix}{index}{'u' * (2048 - len(url_prefix) - 1)}"
        for index in range(5)
    ]
    messages = [
        {
            "id": f"{index:02d}{'m' * 126}",
            "sender_id": "s" * 128,
            "text": "n" * 2000,
        }
        for index in range(20)
    ]
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "text": "t" * 10000,
            "urls": urls,
            "messages": messages,
            "sender_id": "p" * 128,
            "conversation_id": "c" * 128,
            "source": "conversation",
        },
    )
    assert response.status_code == 200
    assert response.json()["risk_score"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"text": "t" * 10001, "source": "manual"},
        {"urls": [f"https://example{index}.test" for index in range(6)], "source": "manual"},
        {"urls": ["u" * 2049], "source": "manual"},
        {
            "messages": [
                {"id": f"m{index}", "sender_id": "sender", "text": "neutral"}
                for index in range(21)
            ],
            "source": "conversation",
        },
        {
            "messages": [{"id": "m1", "sender_id": "sender", "text": "t" * 2001}],
            "source": "conversation",
        },
        {
            "messages": [{"id": "m" * 129, "sender_id": "sender", "text": "neutral"}],
            "source": "conversation",
        },
        {
            "messages": [{"id": "m1", "sender_id": "s" * 129, "text": "neutral"}],
            "source": "conversation",
        },
        {"text": "neutral", "conversation_id": "c" * 129, "source": "manual"},
        {
            "messages": [
                {"id": "duplicate", "sender_id": "sender", "text": "first"},
                {"id": "duplicate", "sender_id": "sender", "text": "second"},
            ],
            "source": "conversation",
        },
    ],
)
async def test_request_rejects_values_beyond_documented_limits(payload: dict) -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_conversation_rules_do_not_join_different_senders() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    split = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "messages": [
                {"id": "m1", "sender_id": "sender-a", "text": "Act now, this is urgent."},
                {"id": "m2", "sender_id": "sender-b", "text": "Send your OTP to verify."}
            ],
            "source": "conversation"
        },
    )
    assert split.json()["verdict"] == "unknown"

    same = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "messages": [
                {"id": "m1", "sender_id": "sender-a", "text": "Act now, this is urgent."},
                {"id": "m2", "sender_id": "sender-a", "text": "Send your OTP to verify."}
            ],
            "source": "conversation"
        },
    )
    payload = same.json()
    assert payload["verdict"] == "suspected_scam"
    assert {item["message_id"] for item in payload["evidence"]} == {"m1", "m2"}


@pytest.mark.asyncio
async def test_protected_sender_messages_are_excluded_from_policy() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    messages = [
        {"id": "self-urgent", "sender_id": "me", "text": "Act now, this is urgent."},
        {"id": "self-secret", "sender_id": "me", "text": "Send your OTP to verify."},
        {"id": "other-neutral", "sender_id": "sender-a", "text": "See you tomorrow."},
    ]

    included = await request(
        app,
        "POST",
        "/v1/analyze",
        json={"messages": messages, "source": "conversation"},
    )
    assert included.json()["verdict"] == "suspected_scam"
    assert {item["message_id"] for item in included.json()["evidence"]} == {
        "self-urgent",
        "self-secret",
    }

    excluded = await request(
        app,
        "POST",
        "/v1/analyze",
        json={"messages": messages, "sender_id": "me", "source": "conversation"},
    )
    payload = excluded.json()
    assert payload["verdict"] == "unknown"
    assert payload["module_results"]["conversation"]["evidence"] == []


def test_suspected_scam_module_requires_grounded_evidence() -> None:
    with pytest.raises(ValueError, match="grounded evidence"):
        ModuleResult(
            status=CoverageStatus.COMPLETE,
            version="test-1",
            raw_score_type="test_result",
            verdict=Verdict.SUSPECTED_SCAM,
            severity=Severity.HIGH,
            score=1,
        )

    with pytest.raises(ValueError, match="quote or observed value"):
        Evidence(
            id="ungrounded",
            indicator_type="test",
            source_module="text",
            explanation="An explanation alone cannot ground a positive verdict.",
        )


@pytest.mark.asyncio
async def test_readiness_is_independent_from_liveness() -> None:
    app = create_app(Settings(demo_mode=False))
    assert (await request(app, "GET", "/health/live")).status_code == 200
    ready = await request(app, "GET", "/health/ready")
    assert ready.status_code == 503
    assert ready.json()["ready"] is False


@pytest.mark.asyncio
async def test_extract_is_explicitly_unavailable() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/extract")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
