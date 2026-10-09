from __future__ import annotations

from dataclasses import dataclass


class DetectorUnavailable(RuntimeError):
    """Raised while the reviewed SmishX adapter has not been installed."""


@dataclass(frozen=True)
class TextDetector:
    model_name: str
    api_key_configured: bool

    @property
    def state(self) -> str:
        if not self.api_key_configured or self.model_name == "configure-me":
            return "not_configured"
        return "not_implemented"

    @property
    def ready(self) -> bool:
        return False

    async def predict(self, text: str) -> dict[str, object]:
        del text
        raise DetectorUnavailable(
            "The SmishX adapter is not installed. The bootstrap does not emit a canned live prediction."
        )
