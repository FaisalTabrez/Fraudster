from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from services.gateway.app.main import create_app
from services.gateway.app.settings import Settings


@pytest.mark.asyncio
async def test_fixture_response_from_running_asgi_app_matches_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = json.loads((root / "contracts" / "analysis-response.schema.json").read_text(encoding="utf-8"))
    app = create_app(Settings(demo_mode=True))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/analyze",
            json={
                "text": "Urgent: send your OTP to verify the account.",
                "urls": ["http://192.168.1.10/verify", "http://192.168.1.10/verify"],
                "messages": [],
                "source": "manual"
            },
        )
    assert response.status_code == 200
    body = response.json()
    Draft202012Validator(schema).validate(body)
    assert body["fixture_generated"] is True
    assert body["risk_score"] is None
    assert body["coverage"]["text"] == "complete"
    assert body["coverage"]["url"] == "complete"
