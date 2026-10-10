from __future__ import annotations

import os
import asyncio
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

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
    # One admitted upload/decode/inference per process; no waiting queue.
    app.state.ocr_slots = BoundedSemaphore(1)

    def process_image(data, content_type):
        image = None
        try:
            image = decode_image(data, content_type)
            return extract(image, app.state.engine)
        except InvalidImage as error:
            return error.status_code, unavailable(str(error))
        except Exception:
            return 503, unavailable("OCR extraction failed. You can still paste text manually.")
        finally:
            if image is not None:
                image.close()
            # The actual worker owns the slot, including after caller cancellation.
            app.state.ocr_slots.release()

    @app.post("/extract")
    async def extraction(request: Request):
        if not app.state.ocr_slots.acquire(blocking=False):
            return JSONResponse(unavailable("OCR is busy. Try again after the current image finishes."),
                                status_code=503, headers={"Retry-After": "1"})
        worker_started = False
        try:
            data = bytearray()
            async for chunk in request.stream():
                if len(data) + len(chunk) > MAX_BYTES:
                    return JSONResponse(unavailable("Image exceeds the 5 MB upload limit."), status_code=413)
                data.extend(chunk)
            worker = asyncio.get_running_loop().run_in_executor(
                None, process_image, bytes(data), request.headers.get("content-type", ""))
            worker_started = True
            # Cancellation does not free capacity while CPU work still runs.
            code, result = await asyncio.shield(worker)
            return JSONResponse(result, status_code=code)
        finally:
            if not worker_started:
                app.state.ocr_slots.release()

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
