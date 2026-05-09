from {{package_name}}.bootstrap.logging import get_logger
from {{package_name}}.modules.{{module_name}}.schemas import (
    {{class_name}}Request,
    {{class_name}}Response,
)


logger = get_logger(__name__)


class {{class_name}}Service:
    def describe(self) -> {{class_name}}Response:
        logger.info("Describing {{module_name}} API")
        return {{class_name}}Response(
            name="{{module_name}}",
            message="{{class_name}} API is ready.",
        )

    def handle(self, payload: {{class_name}}Request) -> {{class_name}}Response:
        logger.info("Handling {{module_name}} request", extra={"payload_name": payload.name})
        return {{class_name}}Response(
            name=payload.name,
            message=f"{payload.name} was handled by {{module_name}}.",
        )
