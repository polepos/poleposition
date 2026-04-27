from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from {{project_import_name}}.app import create_app
from {{project_import_name}}.db.base import Base
from {{project_import_name}}.db.models import import_models
from {{project_import_name}}.db.session import get_engine, get_session_factory
from {{project_import_name}}.settings import get_settings


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch, tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    yield

    Base.metadata.drop_all(bind=get_engine())
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    import_models()
    Base.metadata.create_all(bind=get_engine())
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def race_payload() -> dict[str, str]:
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=14)
    return {
        "name": "Monaco Grand Prix",
        "circuit": "Circuit de Monaco",
        "country": "Monaco",
        "scheduled_at": scheduled_at.isoformat(),
    }
