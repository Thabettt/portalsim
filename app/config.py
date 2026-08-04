from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Webhook Configuration
    webhook_target_url: str = ""
    shared_secret: str = "dev-secret-change-in-production"
    n8n_attendance_webhook_url: str = ""
    n8n_internship_final_status_webhook_url: str = "http://34.123.5.126:5678/webhook/7b32c10f-5576-48ac-8589-ef2944c7d93d"
    n8n_progress_reports_aggregated_report_webhook_url: str = "http://34.123.5.126:5678/webhook/eb24c07a-a02e-40c5-b4e0-00a2564fc9ac"
    n8n_progress_report_reject_webhook_url: str = "http://34.123.5.126:5678/webhook/progress-report-status-change"
    n8n_internship_rejected_webhook_url: str = "http://34.123.5.126:5678/webhook/internship-status-change"
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

    # App settings
    app_name: str = "University Portal Simulator"
    debug: bool = True

    @property
    def retry_delays(self) -> list[int]:
        return [int(x.strip()) for x in self.webhook_retry_delays.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
