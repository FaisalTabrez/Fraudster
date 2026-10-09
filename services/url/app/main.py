from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated

from .detector import DetectorUnavailable, UrlDetector


UrlValue = Annotated[str, Field(min_length=1, max_length=2048)]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    urls: list[UrlValue] = Field(min_length=1, max_length=5)


def create_app(detector: UrlDetector | None = None) -> FastAPI:
    resolved = detector or UrlDetector()
    app = FastAPI(title="Fraudster URL detector", version="0.1.0")
    app.state.detector = resolved

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "live", "version": "0.1.0"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_implemented",
            "ready": False,
            "adapter": "phishing-url-detector",
            "upstream_commit": resolved.upstream_commit,
        }

    @app.post("/predict")
    async def predict(payload: PredictRequest) -> dict[str, object]:
        try:
            return await resolved.predict(payload.urls)
        except DetectorUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "not_implemented", "message": str(exc)},
            ) from None

    return app


app = create_app()
