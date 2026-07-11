from {{package_name}}.bootstrap.logging import get_logger


logger = get_logger(__name__)


class {{class_name}}Service:
    """Internal {{module_name}} service.

    This module is service-only: it exposes no HTTP routes and owns no database
    table. Call this service from other modules, lifecycle hooks, or background
    tasks. Replace the placeholder logic with the real behavior.
    """

    def process(self, message: str) -> str:
        logger.info("Processing {{module_name}}", extra={"text": message})
        return message.strip()
