from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "{{project_name}}"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite:///./poleposition.db")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
