from __future__ import annotations

from fastapi import FastAPI, Response, status


def create_app() -> FastAPI:
    app = FastAPI(title="Fraudster optional OCR service", version="0.1.0")

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "live", "version": "0.1.0"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_implemented",
            "ready": False,
            "adapter": "paddleocr",
            "detail": "No OCR model is downloaded in the P0 bootstrap.",
        }

    return app


app = create_app()
