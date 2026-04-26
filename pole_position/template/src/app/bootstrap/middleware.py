from uuid import uuid4

from fastapi import FastAPI, Request


def add_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def attach_request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
