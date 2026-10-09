import asyncio
import json

import httpx
import pytest

from services.text.app.detector import DetectorUnavailable, TextDetector
from services.text.app.main import create_app


@pytest.mark.asyncio
async def test_text_service_starts_without_credentials_and_refuses_canned_prediction() -> None:
    app = create_app(TextDetector(model_name="configure-me", api_key_configured=False))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/ready")).status_code == 503
        prediction = await client.post("/predict", json={"text": "hello"})
    assert prediction.status_code == 503
    assert prediction.json()["detail"]["code"] == "not_configured"


def test_structured_result_keeps_literal_evidence_and_versions() -> None:
    detector = TextDetector(model_name="provider-model", api_key_configured=True, api_key="test")
    text = "Your verification code is 123456. Do not share it."

    result = detector._validated_result(
        text,
        {
            "verdict": "legitimate",
            "severity": "low",
            "evidence": [
                {
                    "indicator_type": "otp_notification",
                    "quote": "Do not share it.",
                    "explanation": "The notification tells the recipient to keep the code private.",
                }
            ],
        },
    )

    assert result["verdict"] == "legitimate"
    assert result["score"] is None
    assert result["evidence"][0]["quote"] == "Do not share it."
    assert "model=provider-model" in result["version"]
    assert "prompt=smishx-text-v1" in result["version"]


def test_structured_result_rejects_quote_not_in_submitted_text() -> None:
    detector = TextDetector(model_name="provider-model", api_key_configured=True, api_key="test")

    with pytest.raises(DetectorUnavailable, match="quote not found"):
        detector._validated_result(
            "Ordinary delivery update",
            {
                "verdict": "suspected_scam",
                "severity": "high",
                "evidence": [
                    {
                        "indicator_type": "credential_request",
                        "quote": "Send your password",
                        "explanation": "Requests a credential.",
                    }
                ],
            },
        )


@pytest.mark.asyncio
async def test_provider_timeout_is_total_deadline_for_slow_stream(monkeypatch) -> None:
    response_body = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"verdict": "unknown", "severity": "unknown", "evidence": []}
                        )
                    }
                }
            ]
        }
    ).encode()

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for byte in response_body:
                await asyncio.sleep(0.03)
                yield bytes([byte])

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=SlowStream())

    real_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("services.text.app.detector.httpx.AsyncClient", client_factory)
    detector = TextDetector(
        model_name="provider-model",
        api_key_configured=True,
        api_key="test",
        request_timeout_seconds=0.05,
    )

    with pytest.raises(DetectorUnavailable) as exc_info:
        await detector.predict("Ambiguous text")

    assert exc_info.value.code == "provider_timeout"


@pytest.mark.asyncio
async def test_provider_response_rejects_whitespace_only_evidence_quote(monkeypatch) -> None:
    async def provider_response_with_blank_quote(
        _detector: TextDetector, _text: str
    ) -> dict[str, object]:
        return {
            "verdict": "suspected_scam",
            "severity": "high",
            "evidence": [
                {
                    "indicator_type": "credential_request",
                    "quote": " ",
                    "explanation": "Claims the blank quote is evidence.",
                }
            ],
        }
    monkeypatch.setattr(TextDetector, "_call_provider", provider_response_with_blank_quote)
    detector = TextDetector(model_name="provider-model", api_key_configured=True, api_key="test")
    with pytest.raises(DetectorUnavailable) as exc_info:
        await detector.predict("Message containing a space")
    assert exc_info.value.code == "invalid_provider_response"
