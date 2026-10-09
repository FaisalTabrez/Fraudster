from __future__ import annotations

from ipaddress import IPv6Address
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .detector import DetectorUnavailable, UrlDetector
from .upstream.urlparse import parse_url


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
    def reject_malformed_urls(cls, urls: list[str]) -> list[str]:
        for url in urls:
            # Browsers treat backslashes in HTTP(S) URLs as separators. The
            # pinned string parser does not, which could change the host.
            if "\\" in url:
                raise ValueError("URL contains a backslash")
            parsed = parse_url(url)
            host = parsed.host
            if parsed.scheme not in {"http", "https"} or not host:
                raise ValueError("Only web URLs with a host can be analyzed")
            # Browsers decode percent escapes in hosts and treat these IDNA
            # dot equivalents as label separators; the pinned parser does not.
            if "%" in host or any(dot in host for dot in "\u3002\uff0e\uff61"):
                raise ValueError("URL host requires browser normalization")
            if any(character.isspace() or ord(character) < 32 for character in url):
                raise ValueError("URL contains whitespace or control characters")
            if host.startswith("["):
                try:
                    IPv6Address(host[1:-1])
                except ValueError:
                    raise ValueError("Invalid IP host") from None
                authority = parsed.href.split("://", 1)[1].split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
                host_and_port = authority.rsplit("@", 1)[-1].lower()
                if not host.endswith("]") or (
                    host_and_port != host and (not parsed.port or host_and_port != f"{host}:{parsed.port}")
                ):
                    raise ValueError("Invalid IP host")
            elif ":" in host or "[" in host or "]" in host:
                raise ValueError("Invalid host or port")
            if parsed.port and (int(parsed.port) > 65535):
                raise ValueError("Invalid port")
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
