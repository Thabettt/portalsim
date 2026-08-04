from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Webhook Configuration
    webhook_target_url: str = ""
    shared_secret: str = "dev-secret-change-in-production"
    n8n_attendance_webhook_url: str = ""
    n8n_internship_status_webhook_url: str = ""
    n8n_progress_report_status_webhook_url: str = ""
    n8n_warning_status_url: str = ""

    # Inbound Webhook Settings
    exam_remark_webhook_api_key: str = ""
    grades_lookup_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./university_portal.db"

    # Scheduler
    scheduler_timezone: str = "UTC"

    # Webhook retry settings
    webhook_max_retries: int = 3
    webhook_retry_delays: str = "5,30,120"

    # Attendance end-of-day chunked submission
    attendance_chunk_size: int = 200
    attendance_chunk_max_concurrency: int = 5
    attendance_chunk_max_retries: int = 3
    attendance_chunk_retry_delays: str = "2,4,8"
    attendance_chunk_timeout_seconds: float = 30.0

    # App settings
    app_name: str = "University Portal Simulator"
    debug: bool = True

    @property
    def retry_delays(self) -> list[int]:
        return [int(x.strip()) for x in self.webhook_retry_delays.split(",")]

    @property
    def attendance_retry_delays(self) -> list[int]:
        """Exponential backoff delays (seconds) between attendance chunk retries."""
        delays = [
            int(x.strip())
            for x in self.attendance_chunk_retry_delays.split(",")
            if x.strip()
        ]
        return delays or [2, 4, 8]


@lru_cache
def get_settings() -> Settings:
    return Settings()
