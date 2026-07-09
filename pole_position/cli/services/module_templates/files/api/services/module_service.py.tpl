from sqlalchemy.orm import Session

from {{package_name}}.bootstrap.logging import get_logger
from {{package_name}}.modules.{{module_name}}.model import {{class_name}}
from {{package_name}}.modules.{{module_name}}.repository import {{class_name}}Repository
from {{package_name}}.modules.{{module_name}}.schemas import {{class_name}}Create


logger = get_logger(__name__)


class {{class_name}}Service:
    def __init__(self, db: Session) -> None:
        self.repository = {{class_name}}Repository(db)

    def list_{{module_name}}(self) -> list[{{class_name}}]:
        logger.info("Listing {{module_name}}")
        return self.repository.list()

    def create_{{module_name}}(self, payload: {{class_name}}Create) -> {{class_name}}:
        logger.info("Creating {{module_name}}", extra={"item_name": payload.name})
        return self.repository.create(name=payload.name)
