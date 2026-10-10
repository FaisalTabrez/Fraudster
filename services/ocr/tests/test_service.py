import httpx
import pytest

from services.ocr.app.main import create_app


@pytest.mark.asyncio
async def test_optional_ocr_service_has_live_but_not_ready_health() -> None:
    app = create_app(load_model=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health/live")).status_code == 200
        ready = await client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["ready"] is False
