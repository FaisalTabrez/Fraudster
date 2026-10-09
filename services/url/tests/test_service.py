import httpx
import pytest

from services.url.app.main import create_app


@pytest.mark.asyncio
async def test_url_service_preserves_unavailable_boundary_until_model_is_installed() -> None:
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health/live")).status_code == 200
        ready = await client.get("/health/ready")
        prediction = await client.post("/predict", json={"urls": ["https://example.test"]})
    assert ready.status_code == 503
    assert ready.json()["upstream_commit"] == "8648994a2e2ff25eac8fe23b46705ecbcd27f296"
    assert prediction.status_code == 503
