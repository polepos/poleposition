import pytest
from pydantic import ValidationError

from {{project_import_name}}.settings import DEFAULT_AUTH_SECRET_KEY, Settings


def test_production_rejects_default_auth_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_secret_key=DEFAULT_AUTH_SECRET_KEY)


def test_production_allows_custom_auth_secret() -> None:
    settings = Settings(app_env="production", auth_secret_key="a-real-secret")

    assert settings.auth_secret_key == "a-real-secret"


def test_non_production_allows_default_auth_secret() -> None:
    settings = Settings(
        app_env="development",
        auth_secret_key=DEFAULT_AUTH_SECRET_KEY,
    )

    assert settings.app_env == "development"
