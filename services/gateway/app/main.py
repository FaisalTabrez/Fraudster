from __future__ import annotations

from fastapi import FastAPI, Response, status

from .clients.detectors import DetectorClients
from .routes.analyze import router as analyze_router
from .routes.extract import router as extract_router
from .settings import Settings


def create_app(settings: Settings | None = None, detectors: DetectorClients | None = None) -> FastAPI:
    resolved = settings or Settings()
    app = FastAPI(
        title="Fraudster analysis gateway",
        version="0.1.0",
        description="One public contract for text, URL, and client-supplied conversation analysis.",
    )
    app.state.settings = resolved
    app.state.detectors = detectors or DetectorClients(resolved)
    app.include_router(analyze_router)
    app.include_router(extract_router)

    @app.get("/health/live")
    async def live() -> dict[str, object]:
        return {"status": "live", "version": "0.1.0"}

    @app.get("/health/ready")
    async def ready(response: Response) -> dict[str, object]:
        if resolved.demo_mode:
            return {"status": "ready", "ready": True, "mode": "fixture", "detectors": {}}
        detectors_ready = await app.state.detectors.readiness()
        unavailable = [name for name, check in detectors_ready.items() if check["ready"] is not True]
        is_ready = not unavailable
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "ready" if is_ready else "not_ready",
            "ready": is_ready,
            "mode": "live",
            "detectors": detectors_ready,
            "reasons": [f"{name} detector is not ready" for name in unavailable],
        }

    return app


app = create_app()
