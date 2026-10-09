from __future__ import annotations

from typing import Any

import httpx

from ..models import CoverageStatus, ModuleResult
from ..settings import Settings


class DetectorClients:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def text(self, text: str) -> ModuleResult:
        return await self._post(
            "text",
            self.settings.text_service_url,
            {"text": text},
        )

    async def url(self, urls: list[str]) -> ModuleResult:
        return await self._post(
            "url",
            self.settings.url_service_url,
            {"urls": urls},
        )

    async def _post(self, name: str, base_url: str, payload: dict[str, Any]) -> ModuleResult:
        endpoint = f"{base_url.rstrip('/')}/predict"
        try:
            async with httpx.AsyncClient(timeout=self.settings.detector_timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
            if response.status_code >= 400:
                return unavailable_result(name, f"{name} service returned HTTP {response.status_code}")
            return ModuleResult.model_validate(response.json())
        except httpx.TimeoutException:
            return unavailable_result(name, f"{name} service deadline exceeded")
        except (httpx.HTTPError, ValueError, TypeError):
            return unavailable_result(name, f"{name} service response was unavailable")


def unavailable_result(name: str, detail: str) -> ModuleResult:
    return ModuleResult(
        status=CoverageStatus.UNAVAILABLE,
        version="not_available",
        raw_score_type="none",
        detail=detail,
    )


def not_applicable_result(name: str) -> ModuleResult:
    return ModuleResult(
        status=CoverageStatus.NOT_APPLICABLE,
        version="not_applicable",
        raw_score_type="none",
        detail=f"No {name} input was supplied.",
    )
