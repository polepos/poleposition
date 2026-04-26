import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from {{project_import_name}}.db.base import Base
from {{project_import_name}}.db.models import import_models
from {{project_import_name}}.db.session import get_engine
from {{project_import_name}}.settings import get_settings


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.started_at = datetime.now(timezone.utc)

    import_models()
    Base.metadata.create_all(bind=get_engine())

    logger.info(
        "Application starting",
        extra={
            "app_name": settings.app_name,
            "environment": settings.app_env,
        },
    )
    yield
    logger.info(
        "Application shutting down",
        extra={
            "app_name": settings.app_name,
            "environment": settings.app_env,
        },
    )
