from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Webhook Configuration
    webhook_target_url: str = ""
    shared_secret: str = "dev-secret-change-in-production"

    # Database
    database_url: str = "sqlite:///./university_portal.db"

    # Scheduler
    scheduler_timezone: str = "UTC"

    # Webhook retry settings
    webhook_max_retries: int = 3
    webhook_retry_delays: str = "5,30,120"

    # App settings
    app_name: str = "University Portal Simulator"
    debug: bool = True

    @property
    def retry_delays(self) -> list[int]:
        return [int(x.strip()) for x in self.webhook_retry_delays.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()