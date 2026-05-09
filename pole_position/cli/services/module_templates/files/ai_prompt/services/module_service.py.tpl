from {{package_name}}.bootstrap.logging import get_logger
from {{package_name}}.modules.{{module_name}}.orchestrator import {{class_name}}Orchestrator
from {{package_name}}.modules.{{module_name}}.schemas import {{class_name}}PromptRequest, {{class_name}}PromptResponse


logger = get_logger(__name__)


class {{class_name}}Service:
    def __init__(self, orchestrator: {{class_name}}Orchestrator | None = None) -> None:
        self.orchestrator = orchestrator or {{class_name}}Orchestrator()

    def respond(self, payload: {{class_name}}PromptRequest) -> {{class_name}}PromptResponse:
        logger.info("Generating AI response", extra={"topic": payload.topic})
        return self.orchestrator.respond(payload)
