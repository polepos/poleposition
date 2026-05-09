from fastapi import APIRouter

from {{package_name}}.modules.{{module_name}}.schemas import {{class_name}}PromptRequest, {{class_name}}PromptResponse
from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


router = APIRouter()


@router.post("/respond", response_model={{class_name}}PromptResponse)
def respond(payload: {{class_name}}PromptRequest) -> {{class_name}}PromptResponse:
    return {{class_name}}Service().respond(payload)
