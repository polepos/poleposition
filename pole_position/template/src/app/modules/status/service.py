from datetime import datetime, timezone

from fastapi import FastAPI

from {{project_import_name}} import __version__
from {{project_import_name}}.modules.status.schemas import StatusResponse
from {{project_import_name}}.settings import get_settings


def get_status(app: FastAPI) -> StatusResponse:
    settings = get_settings()
    started_at = getattr(app.state, "started_at", datetime.now(timezone.utc))
    now = datetime.now(timezone.utc)

    return StatusResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=__version__,
        uptime_seconds=max(int((now - started_at).total_seconds()), 0),
        timestamp=now,
    )
