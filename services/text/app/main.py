from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from .detector import DetectorUnavailable, TextDetector


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=10000)


def create_app(detector: TextDetector | None = None) -> FastAPI:
    provider = os.getenv("TEXT_PROVIDER", "anthropic").strip().lower()
    resolved = detector or TextDetector(
        model_name=os.getenv("TEXT_MODEL", "configure-me"),
        api_key_configured=bool(api_key := os.getenv("TEXT_API_KEY")),
        api_key=api_key,
        provider=provider,
        api_base_url=os.getenv("TEXT_API_BASE_URL") or None,
        request_timeout_seconds=float(os.getenv("TEXT_TIMEOUT_SECONDS", "8")),
    )
    app = FastAPI(title="Fraudster text detector", version="0.1.0")
    app.state.detector = resolved

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "live", "version": "0.1.0"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        if not resolved.ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": resolved.state,
            "ready": resolved.ready,
            "adapter": "smishx-derived-text-only",
            "provider": resolved.provider,
            "version": resolved.version,
        }

    @app.post("/predict")
    async def predict(payload: PredictRequest) -> dict[str, object]:
        try:
            return await resolved.predict(payload.text)
        except DetectorUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": exc.code, "message": str(exc)},
            ) from None

    return app


app = create_app()
