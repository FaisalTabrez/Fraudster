from __future__ import annotations

import asyncio

import httpx
import pytest

from services.gateway.app.clients.detectors import DetectorClients, unavailable_result
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


class ReadinessClients(UnavailableClients):
    def __init__(self, *, text: bool, url: bool) -> None:
        self.checks = {
            "text": {"ready": text, "status": "ready" if text else "unavailable", "service": "text"},
            "url": {"ready": url, "status": "ready" if url else "unavailable", "service": "url"},
        }

    async def readiness(self) -> dict[str, dict[str, object]]:
        return self.checks


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


class BlankEvidenceClients(UngroundedClients):
    async def text(self, _text: str) -> ModuleResult:
        # Bypass model validation to exercise the gateway boundary itself.
        blank = Evidence.model_construct(
            id="blank", indicator_type="secret_request", source_module="text",
            quote=" ", observed_value=None, message_id=None, explanation="Blank stub.",
        )
        return ModuleResult(
            status=CoverageStatus.COMPLETE, version="test-1", raw_score_type="none",
            verdict=Verdict.SUSPECTED_SCAM, severity=Severity.HIGH, evidence=[blank],
        )


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
async def test_blank_detector_quote_cannot_support_scam_verdict() -> None:
    with pytest.raises(ValueError):
        Evidence(
            id="blank", indicator_type="secret_request", source_module="text",
            quote=" ", explanation="Blank quote.",
        )
    app = create_app(Settings(demo_mode=False), detectors=BlankEvidenceClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "text": "Hello there", "source": "manual",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "unknown"
    assert body["evidence"] == []
    assert body["module_results"]["text"]["verdict"] == "unknown"


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
@pytest.mark.parametrize("payload", [
    {"source": "manual", "text": " " * 10000 + "x"},
    {"source": "manual", "urls": [" " * 2048 + "x"]},
    {"source": "manual", "text": "hello", "sender_id": " " * 128 + "x"},
    {"source": "manual", "text": "hello", "conversation_id": " " * 128 + "x"},
    {"source": "conversation", "messages": [
        {"id": " " * 128 + "x", "sender_id": "other", "text": "hello"},
    ]},
    {"source": "conversation", "messages": [
        {"id": "m1", "sender_id": " " * 128 + "x", "text": "hello"},
    ]},
    {"source": "conversation", "messages": [
        {"id": "m1", "sender_id": "other", "text": " " * 2000 + "x"},
    ]},
])
async def test_raw_wire_lengths_reject_padded_overlong_values(payload: dict) -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_documented_maximum_lengths_are_accepted() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "source": "conversation",
        "text": "t" * 10000,
        "urls": ["u" * 2047 + str(index) for index in range(5)],
        "messages": [
            {"id": f"{index:02d}" + "m" * 126, "sender_id": "s" * 128, "text": "n" * 2000}
            for index in range(20)
        ],
        "sender_id": "p" * 128,
        "conversation_id": "c" * 128,
    })
    assert response.status_code == 200
    assert response.json()["risk_score"] is None


def test_suspected_scam_and_numeric_model_guards() -> None:
    with pytest.raises(ValueError, match="grounded evidence"):
        ModuleResult(
            status=CoverageStatus.COMPLETE, version="test-1", raw_score_type="test",
            verdict=Verdict.SUSPECTED_SCAM, severity=Severity.HIGH,
        )
    with pytest.raises(ValueError, match="quote or observed value"):
        Evidence(
            id="missing", indicator_type="test", source_module="text",
            explanation="No observation.",
        )
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            ModuleResult(status=CoverageStatus.COMPLETE, version="test-1", raw_score_type="test", score=value)
        with pytest.raises(ValueError):
            Evidence(id="bad", indicator_type="test", source_module="url", observed_value=value, explanation="Bad number.")
    for value in (True, False, "1", "0.5"):
        with pytest.raises(ValueError):
            ModuleResult(status=CoverageStatus.COMPLETE, version="test-1", raw_score_type="test", score=value)
    for value in (0, 0.0, False):
        evidence = Evidence(
            id="valid", indicator_type="test", source_module="url",
            observed_value=value, explanation="Concrete observation.",
        )
        assert evidence.observed_value == value


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
async def test_whitespace_distinct_sender_ids_do_not_share_signals() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "source": "conversation",
        "messages": [
            {"id": " urgent-id ", "sender_id": "sender-a", "text": "Act now, this is urgent."},
            {"id": " secret-id ", "sender_id": " sender-a ", "text": "Send your OTP to verify."},
        ],
    })
    assert response.status_code == 200
    assert response.json()["verdict"] == "unknown"
    assert response.json()["evidence"] == []


@pytest.mark.asyncio
async def test_whitespace_distinct_protected_sender_and_exact_message_ids() -> None:
    app = create_app(Settings(demo_mode=False), detectors=UnavailableClients())
    response = await request(app, "POST", "/v1/analyze", json={
        "source": "conversation",
        "sender_id": "sender-a",
        "messages": [
            {"id": "protected", "sender_id": "sender-a", "text": "Act now and send your OTP."},
            {"id": " urgent-id ", "sender_id": " sender-a ", "text": "  Act now, this is urgent.  "},
            {"id": " secret-id ", "sender_id": " sender-a ", "text": "Send your OTP to verify."},
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "suspected_scam"
    assert {item["message_id"] for item in body["evidence"]} == {" urgent-id ", " secret-id "}
    assert all(item["message_id"] != "protected" for item in body["evidence"])
    assert next(item["quote"] for item in body["evidence"] if item["message_id"] == " urgent-id ") == "  Act now, this is urgent.  "


@pytest.mark.asyncio
async def test_whitespace_distinct_message_ids_remain_unique() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/analyze", json={
        "source": "conversation",
        "messages": [
            {"id": "m1", "sender_id": "sender-a", "text": "This is urgent."},
            {"id": " m1 ", "sender_id": "sender-a", "text": "Send your OTP to verify."},
        ],
    })
    assert response.status_code == 200
    assert {item["message_id"] for item in response.json()["evidence"]} == {"m1", " m1 "}


@pytest.mark.asyncio
async def test_blank_top_level_text_is_not_an_applicable_check_when_url_is_supplied() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/analyze", json={
        "source": "manual", "text": "   ", "urls": ["https://example.test"],
    })
    assert response.status_code == 200
    assert response.json()["coverage"]["text"] == "not_applicable"
    assert response.json()["coverage"]["url"] == "complete"


@pytest.mark.asyncio
async def test_readiness_is_independent_from_liveness() -> None:
    app = create_app(Settings(demo_mode=False), detectors=ReadinessClients(text=False, url=True))
    assert (await request(app, "GET", "/health/live")).status_code == 200
    ready = await request(app, "GET", "/health/ready")
    assert ready.status_code == 503
    assert ready.json() == {
        "status": "not_ready",
        "ready": False,
        "mode": "live",
        "detectors": {
            "text": {"ready": False, "status": "unavailable", "service": "text"},
            "url": {"ready": True, "status": "ready", "service": "url"},
        },
        "reasons": ["text detector is not ready"],
    }


@pytest.mark.asyncio
async def test_live_readiness_succeeds_when_required_detectors_are_ready() -> None:
    app = create_app(Settings(demo_mode=False), detectors=ReadinessClients(text=True, url=True))
    ready = await request(app, "GET", "/health/ready")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert ready.json()["reasons"] == []


@pytest.mark.asyncio
async def test_detector_readiness_probes_only_fixed_private_health_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.host == "private-url":
            return httpx.Response(200, json={"ready": True})
        return httpx.Response(503, json={"ready": False, "detail": "provider detail is not relayed"})

    real_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("services.gateway.app.clients.detectors.httpx.AsyncClient", client_factory)
    clients = DetectorClients(Settings(text_service_url="http://private-text", url_service_url="http://private-url"))

    result = await clients.readiness()

    assert set(requested) == {"http://private-text/health/ready", "http://private-url/health/ready"}
    assert result == {
        "text": {"ready": False, "status": "unavailable", "service": "text"},
        "url": {"ready": True, "status": "ready", "service": "url"},
    }


@pytest.mark.asyncio
async def test_fixture_readiness_does_not_probe_private_detectors() -> None:
    app = create_app(Settings(demo_mode=True), detectors=UnavailableClients())
    ready = await request(app, "GET", "/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "ready": True, "mode": "fixture", "detectors": {}}


@pytest.mark.asyncio
async def test_extract_is_explicitly_unavailable() -> None:
    app = create_app(Settings(demo_mode=True))
    response = await request(app, "POST", "/v1/extract")
    assert response.status_code == 415
    assert response.json()["status"] == "unavailable"
