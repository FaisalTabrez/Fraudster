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

    async def _check(self, name: str) -> ModuleResult:
        self.started.add(name)
        if len(self.started) == 2:
            self.both_started.set()
        await asyncio.wait_for(self.both_started.wait(), timeout=0.2)
        return ModuleResult(status=CoverageStatus.COMPLETE, version="test-1", raw_score_type="none")

    async def text(self, _text: str) -> ModuleResult:
        return await self._check("text")

    async def url(self, _urls: list[str]) -> ModuleResult:
        return await self._check("url")


class UngroundedClients:
    async def text(self, _text: str) -> ModuleResult:
        return ModuleResult(
            status=CoverageStatus.COMPLETE, version="test-1", raw_score_type="none",
            verdict=Verdict.SUSPECTED_SCAM, severity=Severity.HIGH,
            evidence=[Evidence(
                id="invented", indicator_type="secret_request", source_module="text",
                quote="Send your password", explanation="Invented by stub.",
            )],
        )

    async def url(self, _urls: list[str]) -> ModuleResult:
        return unavailable_result("url", "not configured")


class FailingClients(PartialClients):
    async def text(self, _text: str) -> ModuleResult:
        raise RuntimeError("test detector failure")


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
        json={"text": "hello", "urls": [], "messages": [], "source": "manual"},
    )
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["verdict"] == "unknown"
    assert payload["severity"] == "unknown"
    assert payload["coverage"]["text"] == "unavailable"
    assert payload["coverage"]["url"] == "not_applicable"


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
async def test_applicable_detectors_start_concurrently() -> None:
    clients = ConcurrentClients()
    app = create_app(Settings(demo_mode=False), detectors=clients)
    response = await request(app, "POST", "/v1/analyze", json={
        "text": "hello", "urls": ["https://example.test"], "source": "manual",
    })
    assert response.status_code == 200
    assert clients.started == {"text", "url"}
    assert response.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_all_requested_remote_checks_fail_unknown_and_null_score() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "text": "hello", "urls": ["https://example.test"], "source": "manual",
    })
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["verdict"] == "unknown"
    assert body["risk_score"] is None
    assert body["coverage"]["text"] == body["coverage"]["url"] == "unavailable"


@pytest.mark.asyncio
async def test_one_detector_failure_preserves_other_result() -> None:
    app = create_app(Settings(demo_mode=False), detectors=FailingClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "text": "hello", "urls": ["https://example.test"], "source": "manual",
    })
    body = response.json()
    assert body["status"] == "partial"
    assert body["coverage"]["text"] == "unavailable"
    assert body["coverage"]["url"] == "complete"
    assert body["risk_score"] is None


@pytest.mark.asyncio
async def test_ungrounded_detector_warning_is_not_reported_as_scam() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UngroundedClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "text": "Hello there", "source": "manual",
    })
    body = response.json()
    assert body["verdict"] == "unknown"
    assert body["evidence"] == []
    assert body["module_results"]["text"]["verdict"] == "unknown"
    assert body["module_results"]["text"]["score"] is None


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
async def test_duplicate_message_ids_are_rejected() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/analyze", json={
        "source": "conversation",
        "messages": [
            {"id": "same", "sender_id": "sender-a", "text": "Act now"},
            {"id": "same", "sender_id": "sender-b", "text": "Send your OTP"},
        ],
    })
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
async def test_conversation_excludes_protected_sender_and_grounds_warning() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "sender_id": "me",
            "messages": [
                {"id": "mine", "sender_id": "me", "text": "Urgent: send your OTP now."},
                {"id": "other", "sender_id": "sender-a", "text": "Send your OTP to verify."},
            ],
            "source": "conversation",
        },
    )
    payload = response.json()
    assert payload["verdict"] == "unknown"
    assert payload["coverage"]["conversation"] == "complete"
    assert payload["evidence"] == []

    response = await request(
        app,
        "POST",
        "/v1/analyze",
        json={
            "sender_id": "me",
            "messages": [
                {"id": "mine", "sender_id": "me", "text": "Urgent: send your OTP now."},
                {"id": "urgent", "sender_id": "sender-a", "text": "Your account is suspended. Act now."},
                {"id": "request", "sender_id": "sender-a", "text": "Send your OTP to verify."},
            ],
            "source": "conversation",
        },
    )
    payload = response.json()
    assert payload["verdict"] == "suspected_scam"
    assert {item["message_id"] for item in payload["evidence"]} == {"urgent", "request"}
    assert all(item["quote"] for item in payload["evidence"])


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
