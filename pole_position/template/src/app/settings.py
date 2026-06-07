from functools import lru_cache
import json

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_AUTH_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    app_name: str = "{{project_name}}"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"
    log_format: str = "text"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="{{database_url_default}}",
    )
    cors_enabled: bool = True
    cors_allow_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    cors_allow_origin_regex: str | None = None
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["Authorization", "Content-Type", "X-Request-ID"]
    cors_expose_headers: list[str] = ["X-Request-ID"]
    cors_max_age: int = 600
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = True
    uvicorn_workers: int = 1
    uvicorn_access_log: bool = True
    uvicorn_proxy_headers: bool = True
    uvicorn_forwarded_allow_ips: str = "127.0.0.1"
    uvicorn_server_header: bool = True
    uvicorn_date_header: bool = True
    uvicorn_use_colors: bool | None = None
    uvicorn_timeout_keep_alive: int = 5
    uvicorn_timeout_graceful_shutdown: int | None = None
    uvicorn_timeout_worker_healthcheck: int = 5
    uvicorn_limit_concurrency: int | None = None
    uvicorn_limit_max_requests: int | None = None
    uvicorn_limit_max_requests_jitter: int = 0
    uvicorn_backlog: int = 2048
    auth_secret_key: str = DEFAULT_AUTH_SECRET_KEY
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 60
    auth_issuer: str = "{{project_name}}"
    # polepos:auth-settings
    # polepos:integration-settings
    # polepos:llm-settings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "log_format",
        "cors_allow_origin_regex",
        "uvicorn_use_colors",
        "uvicorn_timeout_graceful_shutdown",
        "uvicorn_limit_concurrency",
        "uvicorn_limit_max_requests",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"text", "json"}:
            raise ValueError("LOG_FORMAT must be either 'text' or 'json'.")
        return normalized

    @field_validator(
        "cors_allow_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "cors_expose_headers",
        mode="before",
    )
    @classmethod
    def parse_list_env(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            return []

        if stripped.startswith("["):
            return json.loads(stripped)

        return [item.strip() for item in stripped.split(",") if item.strip()]

    @model_validator(mode="after")
    def require_production_auth_secret(self) -> "Settings":
        if (
            self.app_env.strip().lower() == "production"
            and self.auth_secret_key == DEFAULT_AUTH_SECRET_KEY
        ):
            raise ValueError(
                "AUTH_SECRET_KEY must be changed from its default value "
                "when APP_ENV=production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
