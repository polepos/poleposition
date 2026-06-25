from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from {{package_name}}.db.base import Base


class {{class_name}}(Base):
    __tablename__ = "{{module_name}}"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
