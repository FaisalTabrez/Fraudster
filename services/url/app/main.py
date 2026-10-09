from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .detector import DetectorUnavailable, UrlDetector


UrlValue = Annotated[str, Field(min_length=1, max_length=2048)]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    urls: list[UrlValue] = Field(min_length=1, max_length=5)

    @field_validator("urls", mode="before")
    @classmethod
    def check_raw_url_lengths(cls, value: object) -> object:
        if isinstance(value, list):
            for url in value:
                if not isinstance(url, str):
                    continue
                if len(url) > 2048:
                    raise ValueError("URL exceeds 2048 characters")
                if any(0xD800 <= ord(character) <= 0xDFFF for character in url):
                    raise ValueError("URL contains non-scalar Unicode")
        return value

    @field_validator("urls")
    @classmethod
    def reject_blank_urls(cls, urls: list[str]) -> list[str]:
        if any(not url.strip() for url in urls):
            raise ValueError("URLs cannot be blank")
        return urls


def create_app(detector: UrlDetector | None = None) -> FastAPI:
    resolved = detector or UrlDetector()
    app = FastAPI(title="Fraudster URL detector", version="0.1.0")
    app.state.detector = resolved

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Never echo submitted URL strings, including malformed Unicode, in errors.
        return JSONResponse(status_code=422, content={"detail": "Invalid URL request."})

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "live", "version": "0.1.0"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        if resolved.ready:
            return {
                "status": "ready",
                "ready": True,
                "adapter": "phishing-url-detector",
                "upstream_commit": resolved.upstream_commit,
            }
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
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
                detail={"code": "unavailable", "message": str(exc)},
            ) from None

    return app


app = create_app()
