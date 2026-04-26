from fastapi import FastAPI

from {{project_import_name}}.api.router import api_router
from {{project_import_name}}.bootstrap.errors import add_exception_handlers
from {{project_import_name}}.bootstrap.lifespan import lifespan
from {{project_import_name}}.bootstrap.logging import setup_logging
from {{project_import_name}}.bootstrap.middleware import add_middleware
from {{project_import_name}}.settings import get_settings


settings = get_settings()
setup_logging(log_level=settings.log_level)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    add_middleware(application)
    add_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
