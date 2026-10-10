"""Bounded in-memory image validation and contract-shaped OCR results."""
from __future__ import annotations

import io
import math
import warnings

from PIL import Image, UnidentifiedImageError

MAX_BYTES = 5_000_000  # 5 MB, decimal; shared with browser/gateway
MAX_PIXELS = 20_000_000


def unavailable(detail: str, image: dict | None = None) -> dict:
    return {"status": "unavailable", "text": None, "boxes": [], "image": image, "detail": detail}


class InvalidImage(ValueError):
    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail)
        self.status_code = status_code


def decode_image(data: bytes, content_type: str) -> Image.Image:
    if len(data) > MAX_BYTES:
        raise InvalidImage("Image exceeds the 5 MB upload limit.", 413)
    if content_type not in {"image/png", "image/jpeg"}:
        raise InvalidImage("Only PNG and JPEG images are supported.", 415)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"PNG", "JPEG"} or source.get_format_mimetype() != content_type:
                    raise InvalidImage("Image format does not match PNG/JPEG content type.", 415)
                if source.width * source.height > MAX_PIXELS:
                    raise InvalidImage("Image exceeds the 20 million decoded pixel limit.", 413)
                if getattr(source, "n_frames", 1) != 1:
                    raise InvalidImage("Animated images are unsupported.", 415)
                # Header limits above run before verification or pixel decoding.
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                return source.convert("RGB")
    except InvalidImage:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise InvalidImage("Image exceeds the decoded pixel limit.", 413) from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise InvalidImage("Invalid or damaged PNG/JPEG image.") from None


def extract(image: Image.Image, engine) -> tuple[int, dict]:
    dimensions = {"width": image.width, "height": image.height}
    if engine is None:
        return 503, unavailable("OCR model is unavailable. You can still paste text manually.", dimensions)
    try:
        lines = engine.recognize(image)
        boxes = []
        for points, recognized in lines:
            text = recognized[0]
            if not isinstance(text, str) or not text.strip():
                continue
            xs, ys = zip(*points)
            x = max(0, min(image.width, math.floor(min(xs))))
            y = max(0, min(image.height, math.floor(min(ys))))
            right = max(x, min(image.width, math.ceil(max(xs))))
            bottom = max(y, min(image.height, math.ceil(max(ys))))
            boxes.append({"text": text, "x": x, "y": y, "width": right - x, "height": bottom - y})
        if not boxes:
            return 422, unavailable("No readable text was extracted. Try a clearer image or paste text manually.", dimensions)
        return 200, {"status": "complete", "text": "\n".join(box["text"] for box in boxes),
                     "boxes": boxes, "image": dimensions, "detail": "English OCR; review and correct text before analysis."}
    except Exception:
        # Never include library errors: they may contain supplied text or paths.
        return 503, unavailable("OCR extraction failed. Try another image or paste text manually.", dimensions)
