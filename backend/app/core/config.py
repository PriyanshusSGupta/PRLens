from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/prlens"
    github_app_id: str = ""
    github_webhook_secret: str = ""
    github_private_key: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str = ""
    encryption_key: str = ""
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    session_duration_hours: int = 24
    otp_expiry_minutes: int = 10
    severity_threshold_block: str = "low"
    severity_threshold_warn: str = "medium"
    min_confidence: float = 0.3
    max_diff_size: int = 5000
    enable_security: bool = True
    enable_reliability: bool = True
    enable_performance: bool = True
    enable_testing: bool = True
    enable_llm: bool = False
    smtp_host: str = "console"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@prlens.dev"
    smtp_use_tls: bool = True

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
