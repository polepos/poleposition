import ast
import shutil
from pathlib import Path

from pole_position.cli.services.database_options import (
    DEFAULT_DATABASE,
    get_database_option,
)
from pole_position.cli.services.dependency_contract import (
    dependency_names_match,
    parse_dependency_entry,
)
from pole_position.cli.services.template_renderer import (
    build_context,
    render_project_files,
)

DATABASE_DEPENDENCIES = (
    "alembic",
    "psycopg",
    "sqlalchemy",
)


def create_project(
    project_name: str,
    package_name: str,
    project_path: Path,
    *,
    database: str = DEFAULT_DATABASE,
    no_bytecode: bool = False,
) -> None:
    template_dir = Path(__file__).resolve().parents[2] / "template"

    if not template_dir.exists():
        raise RuntimeError(f"Template directory not found: {template_dir}")

    database_option = get_database_option(database, package_name=package_name)

    shutil.copytree(
        template_dir,
        project_path,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    _rename_source_package(
        project_path=project_path,
        package_name=package_name,
    )

    context = build_context(
        project_name=project_name,
        package_name=package_name,
        database=database_option.name,
        no_bytecode=no_bytecode,
    )
    render_project_files(project_path=project_path, context=context)

    if not database_option.uses_database:
        _remove_database_scaffold(
            project_path=project_path,
            project_name=project_name,
            package_name=package_name,
        )


def _rename_source_package(project_path: Path, package_name: str) -> None:
    src_root = project_path / "src"
    source_package_dir = src_root / "app"
    target_package_dir = src_root / package_name

    if not source_package_dir.exists():
        raise RuntimeError(
            f"Template source package not found: {source_package_dir}"
        )

    source_package_dir.rename(target_package_dir)


def _remove_database_scaffold(
    *,
    project_path: Path,
    project_name: str,
    package_name: str,
) -> None:
    package_root = project_path / "src" / package_name

    for path in (
        project_path / "alembic.ini",
        project_path / "migrations",
        package_root / "db",
    ):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    _remove_pyproject_database_dependencies(project_path / "pyproject.toml")
    _remove_env_database_values(project_path / ".env.example")
    _write_database_free_compose(project_path / "compose.yaml")
    _write_database_free_api_deps(
        package_root / "api" / "deps.py", package_name
    )
    _remove_settings_database_url(package_root / "settings.py")
    _remove_lifespan_model_imports(package_root / "bootstrap" / "lifespan.py")
    _remove_run_database_summary(package_root / "run.py")
    _write_database_free_test_conftest(
        project_path / "tests" / "conftest.py",
        project_name=project_name,
        package_name=package_name,
    )


def _remove_pyproject_database_dependencies(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not _is_database_dependency_entry(line)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _is_database_dependency_entry(line: str) -> bool:
    entry = parse_dependency_entry(line)
    if entry is None:
        return False

    return any(
        dependency_names_match(entry.value, database_dependency)
        for database_dependency in DATABASE_DEPENDENCIES
    )


def _remove_env_database_values(path: Path) -> None:
    database_prefixes = (
        "DATABASE_URL=",
        "POSTGRES_DB=",
        "POSTGRES_USER=",
        "POSTGRES_PASSWORD=",
        "POSTGRES_PORT=",
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.startswith(database_prefixes)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_database_free_compose(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "services:",
                "  app:",
                "    build:",
                "      context: .",
                "    env_file:",
                "      - .env",
                "    environment:",
                "      APP_HOST: 0.0.0.0",
                '      APP_RELOAD: "false"',
                "    ports:",
                '      - "${APP_PORT:-8000}:${APP_PORT:-8000}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_database_free_api_deps(path: Path, package_name: str) -> None:
    path.write_text(
        f"""from {package_name}.auth.dependencies import (
    get_current_user,
    require_roles,
)


__all__ = [
    "get_current_user",
    "require_roles",
]
""",
        encoding="utf-8",
    )


def _remove_settings_database_url(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    content = _remove_class_attribute(
        content,
        class_name="Settings",
        attribute_name="database_url",
        path_label=str(path),
    )
    content = _remove_import_name_if_unused(
        content,
        module_name="pydantic",
        imported_name="Field",
        path_label=str(path),
    )
    path.write_text(content, encoding="utf-8")


def _remove_lifespan_model_imports(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    content = _remove_import_from_suffix(
        content,
        module_suffix=".db.models",
        imported_name="import_models",
        path_label=str(path),
    )
    content = _remove_named_call_statement(
        content,
        call_name="import_models",
        path_label=str(path),
    )
    path.write_text(content, encoding="utf-8")


def _remove_run_database_summary(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    content = _remove_call_keyword(
        content,
        call_name="print_startup_table",
        keyword_name="database_url",
        path_label=str(path),
    )
    path.write_text(content, encoding="utf-8")


def _remove_class_attribute(
    content: str,
    *,
    class_name: str,
    attribute_name: str,
    path_label: str,
) -> str:
    tree = _parse_python_content(content, path_label=path_label)
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if (
                isinstance(statement.target, ast.Name)
                and statement.target.id == attribute_name
            ):
                ranges.append(
                    _node_line_range(statement, path_label=path_label)
                )

    return _remove_line_ranges(content, ranges)


def _remove_import_name_if_unused(
    content: str,
    *,
    module_name: str,
    imported_name: str,
    path_label: str,
) -> str:
    tree = _parse_python_content(content, path_label=path_label)
    if any(
        isinstance(node, ast.Name) and node.id == imported_name
        for node in ast.walk(tree)
    ):
        return content

    return _remove_import_from_module(
        content,
        module_name=module_name,
        imported_name=imported_name,
        path_label=path_label,
    )


def _remove_import_from_suffix(
    content: str,
    *,
    module_suffix: str,
    imported_name: str,
    path_label: str,
) -> str:
    tree = _parse_python_content(content, path_label=path_label)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module is None or not node.module.endswith(module_suffix):
            continue
        if all(alias.name != imported_name for alias in node.names):
            continue
        return _remove_import_alias(
            content,
            node=node,
            imported_name=imported_name,
            path_label=path_label,
        )

    return content


def _remove_import_from_module(
    content: str,
    *,
    module_name: str,
    imported_name: str,
    path_label: str,
) -> str:
    tree = _parse_python_content(content, path_label=path_label)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module != module_name:
            continue
        if all(alias.name != imported_name for alias in node.names):
            continue
        return _remove_import_alias(
            content,
            node=node,
            imported_name=imported_name,
            path_label=path_label,
        )

    return content


def _remove_import_alias(
    content: str,
    *,
    node: ast.ImportFrom,
    imported_name: str,
    path_label: str,
) -> str:
    if all(alias.name != imported_name for alias in node.names):
        return content

    kept_names = [
        alias.name
        if alias.asname is None
        else f"{alias.name} as {alias.asname}"
        for alias in node.names
        if alias.name != imported_name
    ]
    start, end = _node_line_range(node, path_label=path_label)
    if not kept_names:
        return _remove_line_ranges(content, [(start, end)])

    lines = content.splitlines()
    indent = " " * node.col_offset
    relative_level = "." * node.level
    lines[start:end] = [
        f"{indent}from {relative_level}{node.module or ''} import "
        f"{', '.join(kept_names)}"
    ]
    return "\n".join(lines) + "\n"


def _remove_named_call_statement(
    content: str,
    *,
    call_name: str,
    path_label: str,
) -> str:
    tree = _parse_python_content(content, path_label=path_label)
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        if _call_name(node.value) == call_name:
            ranges.append(_node_line_range(node, path_label=path_label))

    return _remove_line_ranges(content, ranges)


def _remove_call_keyword(
    content: str,
    *,
    call_name: str,
    keyword_name: str,
    path_label: str,
) -> str:
    tree = _parse_python_content(content, path_label=path_label)
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != call_name:
            continue
        for keyword in node.keywords:
            if keyword.arg == keyword_name:
                ranges.append(_node_line_range(keyword, path_label=path_label))

    return _remove_line_ranges(content, ranges)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _parse_python_content(content: str, *, path_label: str) -> ast.Module:
    try:
        return ast.parse(content)
    except SyntaxError as exc:
        raise RuntimeError(
            f"Cannot update generated Python file: {path_label}"
        ) from exc


def _node_line_range(node: ast.AST, *, path_label: str) -> tuple[int, int]:
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        raise RuntimeError(f"Cannot update generated Python file: {path_label}")

    return node.lineno - 1, node.end_lineno


def _remove_line_ranges(content: str, ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return content if content.endswith("\n") else f"{content}\n"

    lines = content.splitlines()
    for start, end in sorted(set(ranges), reverse=True):
        del lines[start:end]

    return "\n".join(lines) + "\n"


def _write_database_free_test_conftest(
    path: Path,
    *,
    project_name: str,
    package_name: str,
) -> None:
    path.write_text(
        f"""import pytest
from fastapi.testclient import TestClient

from {package_name}.app import create_app
from {package_name}.settings import get_settings


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("AUTH_ISSUER", "{project_name}-test")

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
""",
        encoding="utf-8",
    )
