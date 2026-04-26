from fastapi import FastAPI
from fastapi.responses import JSONResponse

from {{project_import_name}}.domain.exceptions import DomainError, NotFoundError


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(_, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DomainError)
    async def handle_domain_error(_, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
