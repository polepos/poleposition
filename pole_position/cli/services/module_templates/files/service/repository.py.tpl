from sqlalchemy import select
from sqlalchemy.orm import Session

from {{package_name}}.modules.{{module_name}}.model import {{class_name}}


class {{class_name}}Repository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[{{class_name}}]:
        statement = select({{class_name}}).order_by({{class_name}}.id.asc())
        return list(self.db.scalars(statement))

    def create(self, *, name: str) -> {{class_name}}:
        item = {{class_name}}(name=name)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
