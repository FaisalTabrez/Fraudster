"""PRI-02 acceptance checks, run end to end through the real gateway.

These tests use the real gateway code, the real text service, and (on Python 3.13) the real
URL service. Only the transport is in memory. No paid key, model download or network is used.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest

from tests.integration.support import (
    ROOT,
    assert_contract,
    conversation,
    fixed_response_service,
    fixture_text_service,
    fixture_url_service,
    gateway,
    manual,
    request_validator,
    requires_url_service,
    slow_service,
    text_service,
    url_service,
)

IP_URL = "http://198.51.100.24/pay"
DEEP_LINK = "https://www.example.test/account/orders/12345?ref=email&view=full"


# --- fixture mode ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fixture_mode_marks_every_response_as_demo_data(monkeypatch: pytest.MonkeyPatch) -> None:
    async with gateway(monkeypatch, demo_mode=True) as client:
        ready = await client.get("/health/ready")
        assert (ready.status_code, ready.json()["mode"]) == (200, "fixture")
        bodies = []
        for payload in (
            manual("Your OTP is 314159. Do not share it with anyone."),
            manual(urls=[IP_URL]),
            manual("Weekend sale: 30 percent discount.", [DEEP_LINK]),
            conversation(("sender-a", "Act now, your account will be suspended."), ("sender-a", "Send your OTP to verify.")),
        ):
            response = await client.post("/v1/analyze", json=payload)
            assert response.status_code == 200
            bodies.append(response.json())
    for body in bodies:
        assert_contract(body)
        assert body["fixture_generated"] is True
        assert any("demo" in limitation.lower() or "fixture" in limitation.lower() for limitation in body["limitations"])


@pytest.mark.asyncio
@pytest.mark.parametrize("example", sorted((ROOT / "contracts" / "examples").glob("*request*.json")), ids=lambda p: p.name)
async def test_published_request_examples_are_accepted(monkeypatch: pytest.MonkeyPatch, example: Path) -> None:
    payload = json.loads(example.read_text(encoding="utf-8"))
    assert not list(request_validator().iter_errors(payload))
    async with gateway(monkeypatch, demo_mode=True) as client:
        response = await client.post("/v1/analyze", json=payload)
    assert response.status_code == 200
    assert_contract(response.json())


# --- unavailable mode -----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unconfigured_text_service_is_not_ready_and_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    assert not os.environ.get("TEXT_API_KEY"), "the test run must not depend on a provider key"
    service = text_service()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=service), base_url="http://text") as client:
        ready = await client.get("/health/ready")
        predict = await client.post("/predict", json={"text": "hello"})
    assert ready.status_code == 503 and ready.json()["status"] == "not_configured"
    assert predict.status_code == 503 and predict.json()["detail"]["code"] == "not_configured"


@pytest.mark.asyncio
async def test_default_live_mode_reports_unavailable_never_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    # Real text service (unconfigured) and a URL service that is not running.
    async with gateway(monkeypatch, text=text_service(), url=None) as client:
        ready = await client.get("/health/ready")
        assert ready.status_code == 503 and ready.json()["mode"] == "live"
        response = await client.post("/v1/analyze", json=manual("Verify your account now.", [IP_URL]))
    body = response.json()
    assert response.status_code == 200
    assert_contract(body)
    assert body["status"] == "unavailable"
    assert (body["verdict"], body["severity"]) == ("unknown", "unknown")
    assert body["coverage"]["text"] == "unavailable" and body["coverage"]["url"] == "unavailable"
    assert body["fixture_generated"] is False and body["evidence"] == []


@pytest.mark.asyncio
async def test_unavailable_text_with_working_url_service_is_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    async with gateway(monkeypatch, text=text_service(), url=fixture_url_service()) as client:
        response = await client.post("/v1/analyze", json=manual(f"Pay the fee now at {IP_URL}"))
    body = response.json()
    assert_contract(body)
    assert body["status"] == "partial"
    assert (body["coverage"]["text"], body["coverage"]["url"]) == ("unavailable", "complete")
    assert body["evidence"] and all(item["source_module"] == "url" for item in body["evidence"])
    assert all(item["quote"] in f"Pay the fee now at {IP_URL}" for item in body["evidence"])


@pytest.mark.asyncio
async def test_url_service_outage_does_not_touch_a_link_free_text_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async with gateway(monkeypatch, demo_mode=False, text=fixture_text_service(), url=None) as client:
        response = await client.post("/v1/analyze", json=manual("Confirm your PIN by replying now."))
    body = response.json()
    assert_contract(body)
    assert body["coverage"]["url"] == "not_applicable"
    assert body["status"] == "complete" and body["verdict"] == "suspected_scam" and body["evidence"]



# --- real URL service (Python 3.13) ---------------------------------------------------------

@requires_url_service
@pytest.mark.asyncio
async def test_real_url_service_gives_input_dependent_grounded_results(monkeypatch: pytest.MonkeyPatch) -> None:
    async with gateway(monkeypatch, text=text_service(), url=url_service()) as client:
        deep = (await client.post("/v1/analyze", json=manual(urls=[DEEP_LINK]))).json()
        ip = (await client.post("/v1/analyze", json=manual(urls=["http://203.0.113.45/login/verify-account"]))).json()
    for body, url in ((deep, DEEP_LINK), (ip, "http://203.0.113.45/login/verify-account")):
        assert_contract(body)
        assert body["fixture_generated"] is False and body["coverage"]["url"] == "complete"
        assert body["evidence"] and all(item["quote"] == url for item in body["evidence"])
    assert deep["module_results"]["url"]["score"] != ip["module_results"]["url"]["score"]


@requires_url_service
@pytest.mark.asyncio
async def test_real_text_and_url_services_together_are_partial_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    text = f"Your parcel is held. Pay the fee at {IP_URL}"
    async with gateway(monkeypatch, text=text_service(), url=url_service()) as client:
        body = (await client.post("/v1/analyze", json=manual(text))).json()
    assert_contract(body)
    assert body["status"] == "partial"
    assert (body["coverage"]["text"], body["coverage"]["url"]) == ("unavailable", "complete")
    assert all(item["quote"] in text for item in body["evidence"])


# --- timeout and misbehaving detectors ------------------------------------------------------

@pytest.mark.asyncio
async def test_overall_deadline_preserves_the_completed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    started = time.perf_counter()
    async with gateway(
        monkeypatch, text=slow_service(30), url=fixture_url_service(), analysis_timeout_seconds=0.4
    ) as client:
        response = await client.post("/v1/analyze", json=manual(f"Pay the fee now at {IP_URL}"))
    elapsed = time.perf_counter() - started
    body = response.json()
    assert_contract(body)
    assert elapsed < 5, "the gateway must answer at its deadline, not wait for the slow service"
    assert body["status"] == "partial"
    assert (body["coverage"]["text"], body["coverage"]["url"]) == ("unavailable", "complete")
    assert "deadline" in body["module_results"]["text"]["detail"]
    assert body["verdict"] == "suspected_scam" and body["evidence"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service",
    [
        pytest.param(lambda: fixed_response_service(b"<html>not json</html>", media_type="text/html"), id="not-json"),
        pytest.param(lambda: fixed_response_service(b'{"verdict": "suspected_scam"}'), id="missing-fields"),
        pytest.param(lambda: fixed_response_service(b"{}", status_code=500), id="http-500"),
        pytest.param(
            lambda: fixed_response_service(json.dumps({
                "status": "complete", "version": "x", "raw_score_type": "x", "verdict": "suspected_scam",
                "severity": "high", "score": None, "evidence": [], "fixture_generated": False,
            }).encode()),
            id="scam-without-evidence",
        ),
        pytest.param(
            lambda: fixed_response_service(json.dumps({
                "status": "complete", "version": "x", "raw_score_type": "x", "verdict": "suspected_scam",
                "severity": "high", "score": None, "fixture_generated": False,
                "evidence": [{"id": "e1", "indicator_type": "made_up", "source_module": "text",
                              "quote": "text that was never submitted", "explanation": "invented"}],
            }).encode()),
            id="evidence-not-in-input",
        ),
    ],
)
async def test_misbehaving_detector_never_produces_a_positive_result(
    monkeypatch: pytest.MonkeyPatch, service
) -> None:
    async with gateway(monkeypatch, text=service(), url=None) as client:
        response = await client.post("/v1/analyze", json=manual("Please confirm the delivery slot."))
    body = response.json()
    assert response.status_code == 200
    assert_contract(body)
    assert body["verdict"] != "suspected_scam"


# --- malformed requests ---------------------------------------------------------------------

MALFORMED = [
    pytest.param({"urls": [], "messages": [], "source": "manual"}, id="no-input"),
    pytest.param({"text": "   ", "urls": [], "messages": [], "source": "manual"}, id="blank-text"),
    pytest.param({"text": "hello"}, id="missing-source"),
    pytest.param({"text": "hello", "source": "telepathy"}, id="unknown-source"),
    pytest.param({"text": "hello", "source": "manual", "extra": 1}, id="unknown-field"),
    pytest.param({"text": "x" * 10001, "source": "manual"}, id="text-too-long"),
    pytest.param({"urls": [f"http://a{i}.test/" for i in range(6)], "source": "manual"}, id="six-urls"),
    pytest.param({"urls": [" "], "source": "manual"}, id="blank-url"),
    pytest.param({"urls": ["http://a.test/" + "x" * 2048], "source": "manual"}, id="url-too-long"),
    pytest.param(
        {"messages": [{"id": f"m{i}", "sender_id": "a", "text": "hi"} for i in range(21)], "source": "conversation"},
        id="twenty-one-messages",
    ),
    pytest.param({"messages": [{"id": "m1", "sender_id": "a"}], "source": "conversation"}, id="message-without-text"),
    pytest.param(
        {"messages": [{"id": "m1", "sender_id": "a", "text": "hi"}, {"id": "m1", "sender_id": "b", "text": "yo"}],
         "source": "conversation"},
        id="duplicate-message-ids",
    ),
    pytest.param({"text": ["not", "a", "string"], "source": "manual"}, id="wrong-type"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", MALFORMED)
async def test_malformed_requests_are_rejected_with_422(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    async with gateway(monkeypatch, demo_mode=True) as client:
        response = await client.post("/v1/analyze", json=payload)
    assert response.status_code == 422
    assert "analysis_id" not in response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [b"not json at all", b"[1, 2, 3]", b"", b'{"text": '])
async def test_non_object_bodies_are_rejected_with_422(monkeypatch: pytest.MonkeyPatch, content: bytes) -> None:
    async with gateway(monkeypatch, demo_mode=True) as client:
        response = await client.post("/v1/analyze", content=content, headers={"Content-Type": "application/json"})
    assert response.status_code == 422


# --- sender separation ----------------------------------------------------------------------

URGENT = "Act now, your account will be suspended."
SECRET = "Send your OTP to verify the account."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expect_scam", "evidence_ids"),
    [
        pytest.param(conversation(("sender-a", URGENT), ("sender-a", SECRET)), True, {"m1", "m2"}, id="same-sender"),
        pytest.param(conversation(("sender-a", URGENT), ("sender-b", SECRET)), False, set(), id="different-senders"),
        pytest.param(
            conversation(("sender-a", URGENT), ("sender-a ", SECRET)), False, set(), id="whitespace-distinct-senders"
        ),
        pytest.param(
            conversation(("me", URGENT), ("me", SECRET), ("sender-c", "See you soon."), protected="me"),
            False, set(), id="protected-sender-excluded",
        ),
        pytest.param(
            conversation(("me", URGENT), ("sender-c", URGENT), ("sender-c", SECRET), protected="me"),
            True, {"m2", "m3"}, id="protected-sender-does-not-hide-others",
        ),
    ],
)
async def test_sender_separation_end_to_end(
    monkeypatch: pytest.MonkeyPatch, payload: dict, expect_scam: bool, evidence_ids: set[str]
) -> None:
    async with gateway(monkeypatch, text=None, url=None) as client:
        response = await client.post("/v1/analyze", json=payload)
    body = response.json()
    assert response.status_code == 200
    assert_contract(body)
    assert body["coverage"]["conversation"] == "complete"
    assert (body["verdict"] == "suspected_scam") is expect_scam
    assert {item["message_id"] for item in body["evidence"]} == evidence_ids
    submitted = {message["id"]: message["text"] for message in payload["messages"]}
    for item in body["evidence"]:
        assert item["quote"] == submitted[item["message_id"]]
