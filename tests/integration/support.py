"""Helpers that wire the real gateway to the real private services without sockets."""

from __future__ import annotations

import asyncio
import functools
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from jsonschema import Draft202012Validator

from services.gateway.app.clients import detectors as detector_clients
from services.gateway.app.main import create_app
from services.gateway.app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))

URL_SERVICE_AVAILABLE = sys.version_info >= (3, 13)
requires_url_service = pytest.mark.skipif(
    not URL_SERVICE_AVAILABLE,
    reason="the pinned URL adapter needs Python 3.13+; it is exercised in the url-python-313 CI job",
)


def response_validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "contracts" / "analysis-response.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def request_validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "contracts" / "analysis-request.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


class RoutingTransport(httpx.AsyncBaseTransport):
    """Routes the gateway's private service hostnames to ASGI apps, or refuses the connection.

    A host mapped to ``None`` behaves like a service that is not running.
    """

    def __init__(self, apps: dict[str, FastAPI | None]) -> None:
        self.apps = apps

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        app = self.apps.get(request.url.host)
        if app is None:
            raise httpx.ConnectError("service is not running", request=request)
        return await httpx.ASGITransport(app=app).handle_async_request(request)


def slow_service(seconds: float) -> FastAPI:
    """A private service that answers far too late for any gateway deadline."""
    app = FastAPI()

    @app.post("/predict")
    async def predict() -> dict[str, object]:
        await asyncio.sleep(seconds)
        return {}

    return app


@asynccontextmanager
async def gateway(
    monkeypatch: pytest.MonkeyPatch,
    *,
    demo_mode: bool = False,
    text: FastAPI | None = None,
    url: FastAPI | None = None,
    analysis_timeout_seconds: float = 5.0,
) -> AsyncIterator[httpx.AsyncClient]:
    """A client for a gateway whose text and URL services are the given ASGI apps.

    The gateway's own detector client code runs unchanged; only the transport is swapped.
    """
    real_client = httpx.AsyncClient
    routed = SimpleNamespace(
        AsyncClient=functools.partial(real_client, transport=RoutingTransport({"text": text, "url": url})),
        TimeoutException=httpx.TimeoutException,
        HTTPError=httpx.HTTPError,
    )
    monkeypatch.setattr(detector_clients, "httpx", routed)
    app = create_app(Settings(_env_file=None, demo_mode=demo_mode, analysis_timeout_seconds=analysis_timeout_seconds))
    async with real_client(transport=httpx.ASGITransport(app=app), base_url="http://gateway") as client:
        yield client


def text_service() -> FastAPI:
    """The real text service, unconfigured, exactly as CI and a clean checkout run it."""
    from services.text.app.main import create_app as create_text

    return create_text()


def url_service() -> FastAPI:
    from services.url.app.main import create_app as create_url

    return create_url()


def manual(text: str | None = None, urls: list[str] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"urls": urls or [], "messages": [], "source": "manual"}
    if text is not None:
        body["text"] = text
    return body


def conversation(*pairs: tuple[str, str], protected: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "messages": [{"id": f"m{i}", "sender_id": sender, "text": text} for i, (sender, text) in enumerate(pairs, 1)],
        "urls": [],
        "source": "conversation",
    }
    if protected is not None:
        body["sender_id"] = protected
    return body


def fixture_text_service() -> FastAPI:
    """Stands in for a configured text service, which needs a provider key that CI does not have."""
    from services.gateway.app.risk.fixtures import fixture_text_result

    app = FastAPI()

    @app.post("/predict")
    async def predict(payload: dict[str, Any]) -> dict[str, Any]:
        return fixture_text_result(payload["text"]).model_dump(mode="json")

    return app


def fixture_url_service() -> FastAPI:
    """Stands in for the private URL service where the pinned adapter's Python is not available."""
    from services.gateway.app.risk.fixtures import fixture_url_result

    app = FastAPI()

    @app.post("/predict")
    async def predict(payload: dict[str, Any]) -> dict[str, Any]:
        return fixture_url_result(payload["urls"]).model_dump(mode="json")

    return app


def fixed_response_service(content: bytes, *, status_code: int = 200, media_type: str = "application/json") -> FastAPI:
    """A private service that always answers with the given bytes, to model a misbehaving detector."""
    from fastapi import Response

    app = FastAPI()

    @app.post("/predict")
    async def predict() -> Response:
        return Response(content=content, status_code=status_code, media_type=media_type)

    return app


def assert_contract(body: dict[str, Any]) -> None:
    """Invariants every 200 response must hold, on top of the frozen JSON schema."""
    errors = sorted(response_validator().iter_errors(body), key=lambda error: list(error.path))
    assert not errors, [error.message for error in errors]
    assert body["risk_score"] is None
    assert body["probability_calibrated"] is False
    assert set(body["coverage"]) == {"text", "url", "conversation", "reputation"}
    if body["verdict"] == "suspected_scam":
        assert body["evidence"], "a positive scam verdict must cite evidence"
    if body["status"] == "unavailable":
        assert (body["verdict"], body["severity"]) == ("unknown", "unknown")
