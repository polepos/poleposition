from sqlalchemy.orm import Session

from {{package_name}}.bootstrap.logging import get_logger
from {{package_name}}.modules.{{module_name}}.model import {{class_name}}
from {{package_name}}.modules.{{module_name}}.repository import {{class_name}}Repository


logger = get_logger(__name__)


class {{class_name}}Service:
    """Internal {{module_name}} service.

    This module is service-only: it exposes no HTTP routes. Call this service
    from other modules, lifecycle hooks, or background tasks.
    """

    def __init__(self, db: Session) -> None:
        self.repository = {{class_name}}Repository(db)

    def list_{{module_name}}(self) -> list[{{class_name}}]:
        logger.info("Listing {{module_name}}")
        return self.repository.list()

    def create_{{module_name}}(self, *, name: str) -> {{class_name}}:
        logger.info("Creating {{module_name}}", extra={"item_name": name})
        return self.repository.create(name=name)
