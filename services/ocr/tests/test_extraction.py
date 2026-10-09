import io
import struct
import zlib
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image

from services.ocr.app.extraction import MAX_BYTES, MAX_PIXELS, InvalidImage, decode_image
from services.ocr.app.main import create_app


def image_bytes(fmt="PNG", size=(120, 60)):
    stream = io.BytesIO()
    Image.new("RGB", size, "white").save(stream, format=fmt)
    return stream.getvalue()


def png_header(width, height):
    payload = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    def chunk(kind, value):
        return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", payload) + chunk(b"IDAT", zlib.compress(b"")) + chunk(b"IEND", b"")


async def post(app, data, mime="image/png"):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/extract", content=data, headers={"Content-Type": mime})


@pytest.mark.parametrize("fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
@pytest.mark.asyncio
async def test_complete_extraction_has_dimensions_and_clipped_integer_boxes(fmt, mime):
    engine = Mock()
    engine.recognize.return_value = [[[[1.3, 2.2], [125, 2.2], [125, 65], [1.3, 65]], ("Synthetic text", 0.9)]]
    response = await post(create_app(engine), image_bytes(fmt), mime)
    assert response.status_code == 200
    assert response.json()["text"] == "Synthetic text"
    assert response.json()["image"] == {"width": 120, "height": 60}
    assert response.json()["boxes"] == [{"text": "Synthetic text", "x": 1, "y": 2, "width": 119, "height": 58}]


@pytest.mark.parametrize("data,mime,code", [
    (b"x" * (MAX_BYTES + 1), "image/png", 413),
    (png_header(5000, 4001), "image/png", 413),
    (b"not an image", "image/png", 422),
    (image_bytes("GIF"), "image/png", 415),
    (image_bytes(), "image/jpeg", 415),
    (image_bytes(), "application/octet-stream", 415),
    (image_bytes()[:40], "image/png", 422),
], ids=["too-many-bytes", "too-many-pixels", "invalid", "wrong-format", "wrong-mime", "unsupported", "truncated"])
@pytest.mark.asyncio
async def test_bad_inputs_are_rejected_before_engine(data, mime, code):
    engine = Mock()
    response = await post(create_app(engine), data, mime)
    assert response.status_code == code
    assert response.json()["status"] == "unavailable"
    assert response.json()["text"] is None
    engine.recognize.assert_not_called()


def test_exact_limits_pass_header_size_validation_before_decode(monkeypatch):
    # Corrupt header at the exact pixel limit must reach verification, rather
    # than get a size rejection. This avoids allocating a giant test image.
    with pytest.raises(InvalidImage) as error:
        decode_image(png_header(5000, 4000), "image/png")
    assert error.value.status_code == 422
    assert 5000 * 4000 == MAX_PIXELS
    data = image_bytes()
    with decode_image(data + b"\0" * (MAX_BYTES - len(data)), "image/png") as image:
        assert image.size == (120, 60)


@pytest.mark.parametrize("kind,code", [("missing", 503), ("empty", 422), ("failure", 503)])
@pytest.mark.asyncio
async def test_failure_states_are_explicit_and_do_not_expose_exception(kind, code):
    engine = None if kind == "missing" else Mock()
    if kind == "empty":
        engine.recognize.return_value = []
    elif kind == "failure":
        engine.recognize.side_effect = RuntimeError("PRIVATE raw text secret")
    response = await post(create_app(engine, load_model=False), image_bytes())
    body = response.json()
    assert response.status_code == code
    assert body["status"] == "unavailable" and body["text"] is None and body["boxes"] == []
    assert body["image"] == {"width": 120, "height": 60}
    assert "PRIVATE" not in response.text


def test_missing_models_never_construct_paddle_or_download(tmp_path):
    from services.ocr.app.engine import PaddleEngine
    with pytest.raises(FileNotFoundError):
        PaddleEngine(tmp_path)


def test_oversized_dimensions_rejected_before_verification_and_pixel_decode(monkeypatch):
    verify = Mock(side_effect=AssertionError("Image verification should not run"))
    decode = Mock(side_effect=AssertionError("Pixel decode should not run"))
    monkeypatch.setattr(Image.Image, "verify", verify)
    monkeypatch.setattr(Image.Image, "convert", decode)
    with pytest.raises(InvalidImage) as error:
        decode_image(png_header(5000, 4001), "image/png")
    assert error.value.status_code == 413
    verify.assert_not_called()
    decode.assert_not_called()


def test_unreviewed_weights_rejected_before_paddle_import(tmp_path):
    from services.ocr.app.engine import verify_assets
    directory = tmp_path / "det"
    directory.mkdir()
    (directory / "inference.pdiparams").write_bytes(b"synthetic unreviewed weights")
    with pytest.raises(ValueError, match="fingerprint"):
        verify_assets(tmp_path)
