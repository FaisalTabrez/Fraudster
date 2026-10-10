import asyncio
from threading import Event
from unittest.mock import Mock

import httpx
import pytest

from services.ocr.app.main import create_app
from services.ocr.tests.test_extraction import image_bytes, post


def blocked_engine():
    started, finish = Event(), Event()
    engine = Mock()
    def recognize(image):
        started.set()
        assert finish.wait(5), "Test must release the synthetic inference"
        return [[[[0, 0], [90, 0], [90, 20], [0, 20]], ("Synthetic text", 0.9)]]
    engine.recognize.side_effect = recognize
    return engine, started, finish


async def wait_for_slot(app):
    async def available():
        while not app.state.ocr_slots.acquire(blocking=False):
            await asyncio.sleep(0.01)
        app.state.ocr_slots.release()
    await asyncio.wait_for(available(), 1)


@pytest.mark.asyncio
async def test_excess_requests_rejected_before_reading_or_decoding(monkeypatch):
    engine, started, finish = blocked_engine()
    app = create_app(engine)
    first = asyncio.create_task(post(app, image_bytes()))
    assert await asyncio.to_thread(started.wait, 1)
    reads = Mock()
    async def unread_upload():
        reads()
        yield image_bytes()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            excess = await asyncio.wait_for(asyncio.gather(*[
                client.post("/extract", content=unread_upload(), headers={"Content-Type": "image/png"})
                for _ in range(3)]), 0.5)
        assert all(response.status_code == 503 for response in excess)
        assert all(response.json()["status"] == "unavailable" for response in excess)
        reads.assert_not_called()
        assert engine.recognize.call_count == 1
    finally:
        finish.set()
        assert (await first).status_code == 200
    assert (await post(app, image_bytes())).status_code == 200


@pytest.mark.asyncio
async def test_cancellation_keeps_capacity_until_cpu_worker_finishes():
    engine, started, finish = blocked_engine()
    app = create_app(engine)
    first = asyncio.create_task(post(app, image_bytes()))
    assert await asyncio.to_thread(started.wait, 1)
    try:
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        excess = await asyncio.wait_for(post(app, image_bytes()), 0.5)
        assert excess.status_code == 503
        assert engine.recognize.call_count == 1
    finally:
        finish.set()
        await wait_for_slot(app)
    assert (await post(app, image_bytes())).status_code == 200


@pytest.mark.asyncio
async def test_caller_timeout_keeps_capacity_until_cpu_worker_finishes():
    engine, started, finish = blocked_engine()
    app = create_app(engine)
    first = asyncio.create_task(post(app, image_bytes()))
    assert await asyncio.to_thread(started.wait, 1)
    try:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(first, 0.01)
        assert (await asyncio.wait_for(post(app, image_bytes()), 0.5)).status_code == 503
    finally:
        finish.set()
        await wait_for_slot(app)
    assert (await post(app, image_bytes())).status_code == 200


@pytest.mark.asyncio
async def test_bad_upload_releases_admission_slot():
    app = create_app(load_model=False)
    assert (await post(app, b"invalid")).status_code == 422
    assert (await post(app, b"x" * 5_000_001)).status_code == 413
    assert (await post(app, image_bytes())).status_code == 503
    assert app.state.ocr_slots.acquire(blocking=False)
    app.state.ocr_slots.release()
