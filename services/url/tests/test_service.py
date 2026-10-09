from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path

import httpx
import pytest

from services.gateway.app.models import ModuleResult
from services.url.app import detector as detector_module
from services.url.app.main import create_app
from services.url.app.upstream.features import FEATURE_NAMES, extract_features
from services.url.app.upstream.model import load_model


async def request(app, method: str, path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_url_service_is_ready_and_returns_input_dependent_results() -> None:
    app = create_app()
    ready = await request(app, "GET", "/health/ready")
    benign = await request(app, "POST", "/predict", json={"urls": ["https://example.com"]})
    suspicious = await request(app, "POST", "/predict", json={"urls": ["http://192.168.1.10/verify"]})

    assert ready.status_code == 200
    assert ready.json()["upstream_commit"] == "8648994a2e2ff25eac8fe23b46705ecbcd27f296"
    assert benign.status_code == suspicious.status_code == 200
    low, high = benign.json(), suspicious.json()
    ModuleResult.model_validate(low)
    ModuleResult.model_validate(high)
    assert low["status"] == high["status"] == "complete"
    assert low["score"] < high["score"]
    assert low["verdict"] == "legitimate"
    assert high["verdict"] == "suspected_scam"
    assert high["raw_score_type"] == "upstream_blended_score_0_100"
    assert high["fixture_generated"] is False
    assert high["evidence"][0]["quote"] == "http://192.168.1.10/verify"
    assert "not a safety guarantee" in high["detail"]


@pytest.mark.asyncio
async def test_predict_uses_only_submitted_url_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_network(*_args, **_kwargs):
        raise AssertionError("URL analysis attempted a network request")

    monkeypatch.setattr(socket, "create_connection", forbid_network)
    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    monkeypatch.setattr(urllib.request, "urlopen", forbid_network)
    app = create_app()
    response = await request(app, "POST", "/predict", json={
        "urls": ["https://github.com/user/repo", "http://safe.com@evil.xyz/login"]
    })
    assert response.status_code == 200
    assert response.json()["verdict"] == "suspected_scam"
    assert {item["quote"] for item in response.json()["evidence"]} == {
        "https://github.com/user/repo", "http://safe.com@evil.xyz/login",
    }


@pytest.mark.asyncio
async def test_model_is_loaded_once_and_missing_model_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    original = detector_module.load_model
    calls = 0

    def counted_load():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(detector_module, "load_model", counted_load)
    detector = detector_module.UrlDetector()
    await detector.predict(["https://example.com"])
    await detector.predict(["https://example.com"])
    assert calls == 1

    def missing_model():
        raise FileNotFoundError("test model missing")

    monkeypatch.setattr(detector_module, "load_model", missing_model)
    app = create_app()
    assert (await request(app, "GET", "/health/ready")).status_code == 503
    response = await request(app, "POST", "/predict", json={"urls": ["https://example.com"]})
    assert response.status_code == 503
    assert "test model missing" not in response.text


def test_model_feature_order_matches_pinned_extractor(tmp_path: Path) -> None:
    path = Path(detector_module.__file__).with_name("upstream") / "model_meta.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    assert metadata["feature_names"] == FEATURE_NAMES
    assert len(FEATURE_NAMES) == 20
    assert list(extract_features("https://example.com")) == FEATURE_NAMES
    assert load_model().feature_names == FEATURE_NAMES

    metadata["feature_names"][0], metadata["feature_names"][1] = (
        metadata["feature_names"][1], metadata["feature_names"][0]
    )
    changed = tmp_path / "misordered.json"
    changed.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="feature order"):
        load_model(changed)


@pytest.mark.asyncio
@pytest.mark.parametrize("urls", [[], ["   "], ["x" * 2049], ["x"] * 6])
async def test_request_limits_are_enforced(urls: list[str]) -> None:
    response = await request(create_app(), "POST", "/predict", json={"urls": urls})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_maximum_length_and_duplicate_urls_keep_valid_unique_evidence() -> None:
    url = "https://example.test/" + "a" * (2048 - len("https://example.test/"))
    response = await request(create_app(), "POST", "/predict", json={"urls": [url, url]})
    assert response.status_code == 200
    body = response.json()
    ModuleResult.model_validate(body)
    assert len(body["evidence"]) == 2
    assert len({item["id"] for item in body["evidence"]}) == 2
    assert all(item["quote"] == url[:2000] for item in body["evidence"])


@pytest.mark.asyncio
@pytest.mark.parametrize("escaped", [b"\\ud800", b"\\udc00"])
async def test_unpaired_surrogate_url_is_rejected_without_internal_error(escaped: bytes) -> None:
    # Send escaped JSON bytes because a Python HTTP client may reject raw surrogates first.
    body = b'{"urls":["' + escaped + b'"]}'
    response = await request(
        create_app(), "POST", "/predict", content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid URL request."}
    assert "Traceback" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["https://göögle.example/path", "https://example.test/😀"])
async def test_valid_unicode_scalar_url_is_still_accepted(url: str) -> None:
    response = await request(
        create_app(), "POST", "/predict", json={"urls": [url]},
    )
    assert response.status_code == 200
    ModuleResult.model_validate(response.json())
