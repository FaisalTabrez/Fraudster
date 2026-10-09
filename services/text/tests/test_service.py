import httpx
import pytest

from services.text.app.detector import TextDetector
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
