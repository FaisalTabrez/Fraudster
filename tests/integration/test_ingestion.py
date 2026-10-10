import io
import json
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from jsonschema import Draft202012Validator
from PIL import Image

from services.gateway.app.main import create_app
from services.gateway.app.settings import Settings
from services.ocr.app.main import create_app as create_ocr


def png():
    data = io.BytesIO()
    Image.new("RGB", (100, 50), "white").save(data, format="PNG")
    return data.getvalue()


def gateway(transport):
    app = create_app(Settings(demo_mode=True, ocr_service_url="http://private-ocr"))
    app.state.ocr_transport = transport
    return app


@pytest.mark.asyncio
async def test_gateway_ocr_review_analyze_contracts():
    engine = Mock()
    engine.recognize.return_value = [[[[0, 0], [90, 0], [90, 20], [0, 20]], ("Synthetic OCR example", 0.9)]]
    app = gateway(httpx.ASGITransport(app=create_ocr(engine)))
    schema = json.loads(Path("contracts/extraction-response.schema.json").read_text())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        extracted = await client.post("/v1/extract", files={"file": ("synthetic.png", png(), "image/png")})
        assert extracted.status_code == 200
        Draft202012Validator(schema).validate(extracted.json())
        # Only the deliberately corrected text enters the existing analysis route.
        for payload in [dict(text="Corrected synthetic text", urls=[], messages=[], source="screenshot"),
                        dict(urls=["https://example.test/qr"], messages=[], source="qr")]:
            analyzed = await client.post("/v1/analyze", json=payload)
            assert analyzed.status_code == 200
            assert analyzed.json()["fixture_generated"] is True
            assert analyzed.json()["risk_score"] is None


@pytest.mark.parametrize("kind,code", [("size", 413), ("mime", 415), ("extra", 422), ("invalid", 422)])
@pytest.mark.asyncio
async def test_gateway_upload_rejections_and_private_validation(kind, code):
    engine = Mock()
    app = gateway(httpx.ASGITransport(app=create_ocr(engine)))
    data, mime = png(), "image/png"
    if kind == "size": data = b"x" * 5_000_001
    if kind == "mime": mime = "text/plain"
    if kind == "invalid": data = b"not PNG"
    files = {"file": ("image.png", data, mime)}
    if kind == "extra": files["extra"] = ("image.png", png(), "image/png")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/extract", files=files)
    assert response.status_code == code
    assert response.json()["status"] == "unavailable"
    engine.recognize.assert_not_called()


@pytest.mark.parametrize("kind", ["offline", "timeout", "malformed", "redirect", "secrets"])
@pytest.mark.asyncio
async def test_gateway_never_exposes_ocr_errors_or_follows_redirects(kind):
    calls = []
    def upstream(request):
        calls.append(str(request.url))
        if kind == "offline": raise httpx.ConnectError("secret provider details")
        if kind == "timeout": raise httpx.ReadTimeout("private raw text")
        if kind == "redirect": return httpx.Response(302, headers={"Location": "https://example.test/forbidden"})
        if kind == "malformed": return httpx.Response(200, json={"text": "private provider content"})
        return httpx.Response(503, json={"status": "unavailable", "text": None, "boxes": [], "image": None,
                                         "detail": "PRIVATE secret provider exception"})
    app = gateway(httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/extract", files={"file": ("image.png", png(), "image/png")})
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert "PRIVATE" not in response.text and "secret" not in response.text
    assert calls == ["http://private-ocr/extract"]


@pytest.mark.asyncio
async def test_gateway_bounds_entire_body_before_multipart_parsing():
    upstream = Mock()
    app = gateway(httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/extract", content=b"x" * (5_000_000 + 65_537),
                                     headers={"Content-Type": "multipart/form-data; boundary=synthetic"})
    assert response.status_code == 413
    upstream.assert_not_called()


@pytest.mark.asyncio
async def test_gateway_busy_response_is_explicit_without_relaying_upstream_detail():
    def upstream(request):
        return httpx.Response(503, headers={"Retry-After": "1"}, json={"status": "unavailable", "text": None,
            "boxes": [], "image": None, "detail": "PRIVATE provider exception"})
    app = gateway(httpx.MockTransport(upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/extract", files={"file": ("image.png", png(), "image/png")})
    assert response.status_code == 503 and response.headers["retry-after"] == "1"
    assert "busy" in response.json()["detail"]
    assert "PRIVATE" not in response.text
