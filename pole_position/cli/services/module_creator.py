from pathlib import Path


def add_module(module_name: str, cwd: Path | None = None) -> None:
    project_root = cwd or Path.cwd()
    package_root = _find_package_root(project_root)
    package_name = package_root.name
    modules_root = package_root / "modules"
    module_root = modules_root / module_name

    if module_root.exists():
        raise RuntimeError(f"Module already exists: {module_name}")

    _write_module_files(module_root, package_name, module_name)
    _update_modules_init(modules_root / "__init__.py", module_name)
    _update_api_router(package_root / "api" / "router.py", package_name, module_name)
    _update_db_models(package_root / "db" / "models.py", package_name, module_name)


def _find_package_root(project_root: Path) -> Path:
    src_root = project_root / "src"
    if not src_root.exists():
        raise RuntimeError("Current directory does not look like a PolePosition project.")

    candidates = [
        path
        for path in src_root.iterdir()
        if path.is_dir() and (path / "api" / "router.py").exists() and (path / "modules").exists()
    ]

    if len(candidates) != 1:
        raise RuntimeError("Could not determine the application package under src/.")

    return candidates[0]


def _write_module_files(module_root: Path, package_name: str, module_name: str) -> None:
    module_root.mkdir(parents=True)
    class_name = _to_class_name(module_name)
    display_name = class_name.replace("_", " ")

    files = {
        "__init__.py": _module_init_content(),
        "model.py": _model_content(package_name, module_name, class_name),
        "repository.py": _repository_content(package_name, module_name, class_name),
        "schemas.py": _schemas_content(package_name, module_name, class_name),
        "service.py": _service_content(package_name, module_name, class_name, display_name),
        "router.py": _router_content(package_name, module_name, class_name),
    }

    for file_name, content in files.items():
        (module_root / file_name).write_text(content, encoding="utf-8")


def _update_modules_init(path: Path, module_name: str) -> None:
    content = path.read_text(encoding="utf-8")
    export_line = f'    "{module_name}",\n'

    if export_line in content:
        return

    if "__all__ = [" not in content:
        raise RuntimeError(f"Unsupported modules init layout: {path}")

    updated = content.replace("__all__ = [\n", f"__all__ = [\n{export_line}")
    path.write_text(updated, encoding="utf-8")


def _update_api_router(path: Path, package_name: str, module_name: str) -> None:
    content = path.read_text(encoding="utf-8")
    import_line = (
        f"from {package_name}.modules.{module_name}.router import router as {module_name}_router\n"
    )
    include_line = (
        f'api_router.include_router({module_name}_router, prefix="/{module_name}", '
        f'tags=["{module_name}"])\n'
    )

    if import_line not in content:
        content += import_line

    if include_line not in content:
        content += include_line

    path.write_text(content, encoding="utf-8")


def _update_db_models(path: Path, package_name: str, module_name: str) -> None:
    content = path.read_text(encoding="utf-8")
    import_line = f"    from {package_name}.modules.{module_name} import model  # noqa: F401\n"

    if import_line in content:
        return

    if "def import_models() -> None:\n" not in content:
        raise RuntimeError(f"Unsupported db models layout: {path}")

    content += import_line
    path.write_text(content, encoding="utf-8")


def _module_init_content() -> str:
    return '''__all__ = [
    "model",
    "repository",
    "router",
    "schemas",
    "service",
]
'''


def _model_content(package_name: str, module_name: str, class_name: str) -> str:
    return f'''from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from {package_name}.db.base import Base


class {class_name}(Base):
    __tablename__ = "{module_name}"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
'''


def _repository_content(package_name: str, module_name: str, class_name: str) -> str:
    return f'''from sqlalchemy import select
from sqlalchemy.orm import Session

from {package_name}.modules.{module_name}.model import {class_name}


class {class_name}Repository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[{class_name}]:
        statement = select({class_name}).order_by({class_name}.id.asc())
        return list(self.db.scalars(statement))

    def create(self, *, name: str) -> {class_name}:
        item = {class_name}(name=name)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
'''


def _schemas_content(package_name: str, module_name: str, class_name: str) -> str:
    return f'''from pydantic import BaseModel, ConfigDict, Field


class {class_name}Create(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class {class_name}Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
'''


def _service_content(
    package_name: str,
    module_name: str,
    class_name: str,
    display_name: str,
) -> str:
    return f'''from sqlalchemy.orm import Session

from {package_name}.modules.{module_name}.model import {class_name}
from {package_name}.modules.{module_name}.repository import {class_name}Repository
from {package_name}.modules.{module_name}.schemas import {class_name}Create


class {class_name}Service:
    def __init__(self, db: Session) -> None:
        self.repository = {class_name}Repository(db)

    def list_{module_name}(self) -> list[{class_name}]:
        return self.repository.list()

    def create_{module_name}(self, payload: {class_name}Create) -> {class_name}:
        return self.repository.create(name=payload.name)
'''


def _router_content(package_name: str, module_name: str, class_name: str) -> str:
    return f'''from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from {package_name}.api.deps import db_session
from {package_name}.modules.{module_name}.schemas import {class_name}Create, {class_name}Read
from {package_name}.modules.{module_name}.service import {class_name}Service


router = APIRouter()


@router.get("/", response_model=list[{class_name}Read])
def list_{module_name}(db: Session = Depends(db_session)) -> list[{class_name}Read]:
    return {class_name}Service(db).list_{module_name}()


@router.post("/", response_model={class_name}Read, status_code=status.HTTP_201_CREATED)
def create_{module_name}(payload: {class_name}Create, db: Session = Depends(db_session)) -> {class_name}Read:
    return {class_name}Service(db).create_{module_name}(payload)
'''


def _to_class_name(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))
