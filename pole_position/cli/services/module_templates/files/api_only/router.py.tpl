from fastapi import APIRouter

from {{package_name}}.modules.{{module_name}}.schemas import (
    {{class_name}}Request,
    {{class_name}}Response,
)
from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


router = APIRouter()


@router.get("/", response_model={{class_name}}Response)
def describe_{{module_name}}() -> {{class_name}}Response:
    return {{class_name}}Service().describe()


@router.post("/", response_model={{class_name}}Response)
def handle_{{module_name}}(payload: {{class_name}}Request) -> {{class_name}}Response:
    return {{class_name}}Service().handle(payload)
