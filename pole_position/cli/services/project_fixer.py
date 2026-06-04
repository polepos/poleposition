import ast
from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.module_creator import (
    MODEL_IMPORTS_MARKER,
    MODULE_EXPORTS_MARKER,
    ROUTER_IMPORTS_MARKER,
    ROUTER_INCLUDES_MARKER,
)
from pole_position.cli.services.project_checker import _discover_core_project

SETTINGS_MARKERS = [
    "    # polepos:auth-settings",
    "    # polepos:integration-settings",
    "    # polepos:llm-settings",
]

ENV_MARKERS = [
    "# polepos:auth-env",
    "# polepos:integration-env",
    "# polepos:llm-env",
]


@dataclass(frozen=True)
class ProjectFixResult:
    project_root: Path
    package_root: Path
    fixed_files: tuple[Path, ...]

    @property
    def package_name(self) -> str:
        return self.package_root.name


def fix_project(cwd: Path | None = None) -> ProjectFixResult:
    project_root, package_root = _discover_core_project(cwd)
    fixed_files: list[Path] = []

    _collect_changed(
        fixed_files, _fix_api_router(package_root / "api" / "router.py")
    )
    _collect_changed(
        fixed_files, _fix_db_models(package_root / "db" / "models.py")
    )
    _collect_changed(
        fixed_files,
        _fix_modules_init(package_root / "modules" / "__init__.py"),
    )
    _collect_changed(fixed_files, _fix_settings(package_root / "settings.py"))
    _collect_changed(fixed_files, _fix_env(project_root / ".env.example"))

    return ProjectFixResult(
        project_root=project_root,
        package_root=package_root,
        fixed_files=tuple(dict.fromkeys(fixed_files)),
    )


def _collect_changed(
    fixed_files: list[Path], changed_path: Path | None
) -> None:
    if changed_path is not None:
        fixed_files.append(changed_path)


def _fix_api_router(path: Path) -> Path | None:
    lines = _read_lines(path)
    if lines is None:
        return None

    changed = False
    if ROUTER_IMPORTS_MARKER not in lines:
        _insert_before_api_router(lines, ROUTER_IMPORTS_MARKER)
        changed = True

    if ROUTER_INCLUDES_MARKER not in lines:
        _insert_after_last_router_include(lines, ROUTER_INCLUDES_MARKER)
        changed = True

    if changed:
        _write_lines(path, lines)
        return path

    return None


def _insert_before_api_router(lines: list[str], marker: str) -> None:
    for index, line in enumerate(lines):
        if line.startswith("api_router ="):
            while index > 0 and lines[index - 1] == "":
                index -= 1
            lines.insert(index, marker)
            return

    lines.append(marker)


def _insert_after_last_router_include(lines: list[str], marker: str) -> None:
    insert_index = _last_api_router_include_end_index(lines)
    if insert_index is None:
        lines.append(marker)
        return

    lines.insert(insert_index, marker)


def _last_api_router_include_end_index(lines: list[str]) -> int | None:
    try:
        tree = ast.parse("\n".join(lines) + "\n")
    except SyntaxError:
        return None

    include_end_indexes: list[int] = []
    for node in tree.body:
        if not isinstance(node, ast.Expr):
            continue
        if not _is_api_router_include_call(node.value):
            continue
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is not None:
            include_end_indexes.append(end_lineno)

    if not include_end_indexes:
        return None

    return include_end_indexes[-1]


def _is_api_router_include_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "api_router"
    )


def _fix_db_models(path: Path) -> Path | None:
    lines = _read_lines(path)
    if lines is None or MODEL_IMPORTS_MARKER in lines:
        return None

    for index, line in enumerate(lines):
        if not line.startswith("def import_models("):
            continue
        insert_index = index + 1
        while insert_index < len(lines) and lines[
            insert_index
        ].strip().startswith("#"):
            insert_index += 1
        lines.insert(insert_index, MODEL_IMPORTS_MARKER)
        _write_lines(path, lines)
        return path

    return None


def _fix_modules_init(path: Path) -> Path | None:
    lines = _read_lines(path)
    if lines is None or MODULE_EXPORTS_MARKER in lines:
        return None

    for index, line in enumerate(lines):
        if line.strip() == "]":
            lines.insert(index, MODULE_EXPORTS_MARKER)
            _write_lines(path, lines)
            return path

    lines.append(MODULE_EXPORTS_MARKER)
    _write_lines(path, lines)
    return path


def _fix_settings(path: Path) -> Path | None:
    return _ensure_markers_before_anchor(
        path=path,
        markers=SETTINGS_MARKERS,
        anchor="    model_config = SettingsConfigDict(",
    )


def _fix_env(path: Path) -> Path | None:
    return _ensure_markers_before_anchor(
        path=path,
        markers=ENV_MARKERS,
        anchor=None,
    )


def _ensure_markers_before_anchor(
    *,
    path: Path,
    markers: list[str],
    anchor: str | None,
) -> Path | None:
    lines = _read_lines(path)
    if lines is None:
        return None

    missing_markers = [marker for marker in markers if marker not in lines]
    if not missing_markers:
        return None

    insert_index = len(lines)
    if anchor is not None:
        for index, line in enumerate(lines):
            if line == anchor:
                insert_index = index
                break

    for marker in missing_markers:
        lines.insert(insert_index, marker)
        insert_index += 1

    _write_lines(path, lines)
    return path


def _read_lines(path: Path) -> list[str] | None:
    if not path.is_file():
        return None

    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return None


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
