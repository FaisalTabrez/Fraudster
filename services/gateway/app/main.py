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
            return {"status": "ready", "ready": True, "mode": "fixture"}
        detectors_state = await app.state.detectors.readiness()
        reasons = [
            f"{name} detector not ready ({state['state']})"
            for name, state in detectors_state.items()
            if not state["ready"]
        ]
        if reasons:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready" if reasons else "ready",
            "ready": not reasons,
            "mode": "live",
            "detectors": detectors_state,
            "reasons": reasons,
        }

    return app


app = create_app()
