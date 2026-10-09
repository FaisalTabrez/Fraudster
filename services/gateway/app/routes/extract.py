"""The sole public OCR boundary; bounded multipart upload -> private service."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

router = APIRouter(prefix="/v1")
MAX_BYTES = 5_000_000
MAX_BODY = MAX_BYTES + 65_536  # bounded multipart envelope, not an image allowance


def failure(detail: str, code: int = 503):
    return JSONResponse({"status": "unavailable", "text": None, "boxes": [], "image": None,
                         "detail": detail}, status_code=code)


class Box(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)


class Dimensions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: str
    text: str | None
    boxes: list[Box]
    image: Dimensions | None
    detail: str | None

    @model_validator(mode="after")
    def valid(self):
        if self.status not in {"complete", "unavailable"}:
            raise ValueError("Invalid extraction status")
        if self.status == "complete" and (not self.text or not self.boxes or self.image is None):
            raise ValueError("Incomplete extraction")
        if self.status == "unavailable" and (self.text is not None or self.boxes):
            raise ValueError("Unexpected unavailable extraction")
        if self.image is not None:
            if self.image.width * self.image.height > 20_000_000:
                raise ValueError("Invalid image size")
            if any(b.x + b.width > self.image.width or b.y + b.height > self.image.height for b in self.boxes):
                raise ValueError("Invalid box coordinates")
        return self


@router.post("/extract")
async def extract(request: Request):
    if not request.headers.get("content-type", "").startswith("multipart/form-data;"):
        return failure("Upload one PNG/JPEG in the multipart file field.", 415)
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            return failure("Upload exceeds the 5 MB image limit or multipart envelope limit.", 413)
        body.extend(chunk)

    async def receive():
        return {"type": "http.request", "body": bytes(body), "more_body": False}

    # Parse only after bounding the entire body. Starlette's file size defaults
    # alone do not enforce an upload limit. Every temporary upload is closed.
    bounded = Request(request.scope, receive)
    try:
        async with bounded.form(max_files=1, max_fields=0) as form:
            upload = form.get("file")
            if not isinstance(upload, UploadFile) or len(form) != 1:
                return failure("Upload exactly one image in the file field.", 422)
            if upload.content_type not in {"image/png", "image/jpeg"}:
                return failure("Only PNG and JPEG images are supported.", 415)
            data = await upload.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return failure("Image exceeds the 5 MB upload limit.", 413)
            content_type = upload.content_type
    except (HTTPException, ValueError):
        return failure("Invalid multipart image upload.", 422)
    try:
        settings = request.app.state.settings
        async with httpx.AsyncClient(timeout=settings.analysis_timeout_seconds,
                                     transport=getattr(request.app.state, "ocr_transport", None)) as client:
            response = await client.post(settings.ocr_service_url.rstrip("/") + "/extract",
                                         content=data, headers={"Content-Type": content_type})
        if response.status_code not in {200, 413, 415, 422, 503}:
            return failure("OCR service is unavailable. You can still paste text manually.")
        result = Extraction.model_validate(response.json())
        if (response.status_code == 200) != (result.status == "complete"):
            return failure("OCR service returned an invalid extraction response.")
        # Do not relay upstream exception messages or stack traces.
        result.detail = ("English OCR; review and correct text before analysis." if result.status == "complete"
                         else {413: "Image exceeds the 5 MB or 20 million pixel limit.",
                               415: "Only static PNG and JPEG images are supported.",
                               422: "Invalid image or no readable text extracted. Try another image or paste text.",
                               503: "OCR unavailable or extraction failed. You can still paste text manually."}[response.status_code])
        return JSONResponse(result.model_dump(), status_code=response.status_code)
    except (httpx.HTTPError, ValueError):
        return failure("OCR service is unavailable. You can still paste text manually.")
