from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .engine import PaddleEngine
from .extraction import MAX_BYTES, InvalidImage, decode_image, extract, unavailable


def create_app(engine=None, *, load_model: bool = True) -> FastAPI:
    app = FastAPI(title="Fraudster optional OCR service", version="0.1.0")
    if engine is None and load_model:
        try:
            engine = PaddleEngine(Path(os.environ.get("OCR_MODEL_DIR", "services/ocr/models")))
        except Exception:
            engine = None
    app.state.engine = engine

    @app.post("/extract")
    async def extraction(request: Request):
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_BYTES:
                return JSONResponse(unavailable("Image exceeds the 5 MB upload limit."), status_code=413)
            data.extend(chunk)
        try:
            image = await run_in_threadpool(decode_image, bytes(data), request.headers.get("content-type", ""))
        except InvalidImage as error:
            return JSONResponse(unavailable(str(error)), status_code=error.status_code)
        try:
            code, result = await run_in_threadpool(extract, image, app.state.engine)
            return JSONResponse(result, status_code=code)
        finally:
            image.close()

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "live", "version": "0.1.0"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        if app.state.engine is not None:
            return {"status": "ready", "ready": True, "adapter": "paddleocr", "language": "en"}
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "ready": False,
            "adapter": "paddleocr",
            "detail": "Optional English CPU OCR dependencies or prepared models are unavailable.",
        }

    return app


app = create_app()
