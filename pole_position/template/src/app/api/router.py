from fastapi import APIRouter

from {{project_import_name}}.modules.races.router import router as races_router
from {{project_import_name}}.modules.status.router import router as status_router


api_router = APIRouter()
api_router.include_router(status_router, tags=["status"])
api_router.include_router(races_router, prefix="/races", tags=["races"])
