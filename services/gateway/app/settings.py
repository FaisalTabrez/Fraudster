from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    text_service_url: str = "http://text:8000"
    url_service_url: str = "http://url:8000"
    ocr_service_url: str = "http://ocr:8000"
    analysis_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    demo_mode: bool = False

    @property
    def detector_timeout_seconds(self) -> float:
        return min(5.0, max(0.1, self.analysis_timeout_seconds * 0.6))
