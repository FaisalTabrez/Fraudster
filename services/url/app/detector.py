from __future__ import annotations


class DetectorUnavailable(RuntimeError):
    """Raised while the pinned URL detector adapter and model are absent."""


class UrlDetector:
    upstream_commit = "8648994a2e2ff25eac8fe23b46705ecbcd27f296"

    @property
    def ready(self) -> bool:
        return False

    async def predict(self, urls: list[str]) -> dict[str, object]:
        del urls
        raise DetectorUnavailable(
            "The inspected feature extractor and JSON model have not been copied into this service."
        )
