from pathlib import Path

from pole_position.cli.services.pyproject_editor import (
    ensure_project_dependency,
)


def _ensure_project_dependency(path: Path, dependency: str | None) -> bool:
    if dependency is None:
        return False

    original = path.read_text(encoding="utf-8")
    ensure_project_dependency(path, dependency)
    return path.read_text(encoding="utf-8") != original
