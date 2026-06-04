import ast
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pole_position.cli.services.project_creator import (
    _remove_lifespan_model_imports,
    _remove_pyproject_database_dependencies,
    _remove_run_database_summary,
    _remove_settings_database_url,
)
from pole_position.cli.services.project_creator import (
    create_project as create_project_from_template,
)

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[2]
START_USAGE = (
    "Usage: polepos start <project_name> "
    "[--install] [--no-bytecode] [--db sqlite|postgres|none]"
)


def run_cli(cwd, *args):
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(REPO_ROOT)
    )

    return subprocess.run(
        [sys.executable, "-m", "pole_position.cli.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def _assert_python_files_compile(project_root: Path) -> None:
    python_files = sorted(project_root.rglob("*.py"))

    assert python_files
    for path in python_files:
        py_compile.compile(str(path), doraise=True)


def _assigns_name(node: ast.Assign, name: str) -> bool:
    return any(
        isinstance(target, ast.Name) and target.id == name
        for target in node.targets
    )


def _assigns_call(node: ast.Assign, target_name: str, call_name: str) -> bool:
    return (
        _assigns_name(node, target_name) and _call_name(node.value) == call_name
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def test_create_project(tmp_path: Path):
    project_name = "myapp"

    result = run_cli(tmp_path, "start", project_name)

    assert result.returncode == 0
    assert "uv sync --extra dev" in result.stdout
    assert (tmp_path / project_name).exists()
    assert (tmp_path / project_name / "src").exists()


def test_startproject_alias(tmp_path: Path):
    result = run_cli(tmp_path, "startproject", "aliasapp")

    assert result.returncode == 0
    assert (tmp_path / "aliasapp").exists()


def test_invalid_project_name(tmp_path: Path):
    result = run_cli(tmp_path, "start", "invalid name")

    assert result.returncode != 0
    assert "Usage" in result.stdout


def test_start_rejects_project_name_with_path_separator(tmp_path: Path):
    result = run_cli(tmp_path, "start", "foo/bar")

    assert result.returncode != 0
    assert "Project name cannot contain path separators." in result.stdout
    assert not (tmp_path / "foo").exists()


def test_start_rejects_project_name_invalid_for_pyproject_metadata(
    tmp_path: Path,
):
    result = run_cli(tmp_path, "start", "foo@bar")

    assert result.returncode != 0
    assert "Project name may only contain letters, digits" in result.stdout
    assert not (tmp_path / "foo@bar").exists()


def test_start_help_shows_usage_without_creating_project(tmp_path: Path):
    result = run_cli(tmp_path, "start", "--help")

    assert result.returncode == 0
    assert START_USAGE in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_start_rejects_unknown_option(tmp_path: Path):
    result = run_cli(tmp_path, "start", "--template")

    assert result.returncode != 0
    assert "Unexpected option: --template" in result.stdout
    assert START_USAGE in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_existing_directory(tmp_path: Path):
    project_path = tmp_path / "myapp"
    project_path.mkdir()

    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode != 0
    assert "already exists" in result.stdout


def test_package_name_normalization(tmp_path: Path):
    result = run_cli(tmp_path, "start", "my-app")

    assert result.returncode == 0
    assert (tmp_path / "my-app").exists()
    assert (tmp_path / "my-app" / "src" / "my_app").exists()


def test_start_rejects_unknown_database_option(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp", "--db", "clickhouse")

    assert result.returncode != 0
    assert "Unsupported database option 'clickhouse'" in result.stdout
    assert START_USAGE in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_start_rejects_missing_database_option_value(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp", "--db")

    assert result.returncode != 0
    assert "Missing value for --db" in result.stdout
    assert START_USAGE in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_start_with_postgres_database_option(tmp_path: Path):
    result = run_cli(tmp_path, "start", "pg-app", "--db=postgres")

    assert result.returncode == 0
    assert "Database: postgres" in result.stdout
    assert "polepos db upgrade" in result.stdout

    project_root = tmp_path / "pg-app"
    package_root = project_root / "src" / "pg_app"
    env_example = (project_root / ".env.example").read_text(encoding="utf-8")
    settings = (package_root / "settings.py").read_text(encoding="utf-8")
    compose_file = (project_root / "compose.yaml").read_text(encoding="utf-8")

    expected_url = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/pg_app"
    )
    assert f"DATABASE_URL={expected_url}" in env_example
    assert "POSTGRES_DB=pg_app" in env_example
    assert f'default="{expected_url}"' in settings
    assert "${POSTGRES_DB:-pg_app}" in compose_file
    assert (project_root / "alembic.ini").exists()
    assert (package_root / "db" / "models.py").exists()


def test_start_with_no_database_option(tmp_path: Path):
    result = run_cli(tmp_path, "start", "api-app", "--db", "none")

    assert result.returncode == 0
    assert "Database: none" in result.stdout
    assert "polepos db upgrade" not in result.stdout
    assert "uv sync --extra dev" in result.stdout
    assert "uv run python -m api_app.run" in result.stdout

    project_root = tmp_path / "api-app"
    package_root = project_root / "src" / "api_app"
    env_example = (project_root / ".env.example").read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    dockerfile = (project_root / "Dockerfile").read_text(encoding="utf-8")
    settings = (package_root / "settings.py").read_text(encoding="utf-8")
    api_deps = (package_root / "api" / "deps.py").read_text(encoding="utf-8")
    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(
        encoding="utf-8"
    )
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(
        encoding="utf-8"
    )

    assert not (project_root / "alembic.ini").exists()
    assert not (project_root / "migrations").exists()
    assert not (package_root / "db").exists()
    assert 'db = "none"' in manifest
    assert "DATABASE_URL=" not in env_example
    assert "POSTGRES_DB=" not in env_example
    assert '"alembic>=' not in pyproject
    assert '"sqlalchemy>=' not in pyproject
    assert '"psycopg[binary]>=' not in pyproject
    assert "database_url" not in settings
    assert "sqlalchemy" not in api_deps
    assert ".db." not in api_deps
    assert "db_session" not in api_deps
    assert "get_current_user" in api_deps
    assert "require_roles" in api_deps
    assert "import_models" not in lifespan
    assert ".db." not in tests_conftest
    assert "alembic.ini" not in dockerfile
    assert "COPY migrations" not in dockerfile
    assert "COPY pyproject.toml README.md ./" in dockerfile
    assert "This project was generated with `--db none`" in readme
    assert "uv sync --extra dev" in readme
    assert "polepos db upgrade" not in readme
    assert "polepos add module garage --api-only" in readme
    assert "polepos add module garage\n" not in readme
    assert "If the module directory was already deleted manually" in readme
    assert "router/export wiring" in readme
    assert readme.count("Use `polepos remove module <name> --wiring-only`") == 1
    assert "alembic.ini" not in readme
    assert "migrations/" not in readme
    assert "\n  db/\n" not in readme
    assert "src/api_app/" in readme

    _assert_python_files_compile(project_root)

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0
    assert "PolePosition project check passed." in check_result.stdout


def test_create_project_normalizes_database_option_for_database_free_scaffold(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "api-app"

    create_project_from_template(
        project_name="api-app",
        package_name="api_app",
        project_path=project_root,
        database="NONE",
    )

    api_deps = (project_root / "src" / "api_app" / "api" / "deps.py").read_text(
        encoding="utf-8"
    )

    assert not (project_root / "alembic.ini").exists()
    assert not (project_root / "migrations").exists()
    assert "db_session" not in api_deps
    assert "sqlalchemy" not in api_deps


def test_database_free_cleanup_removes_database_dependencies_by_name(
    tmp_path: Path,
) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "\n".join(
            [
                "[project]",
                "dependencies = [",
                '  "fastapi[standard]>=0.115.0",',
                '  "SQLAlchemy ~= 2.0",',
                '  "psycopg[binary] == 3.2.1",  # postgres driver',
                '  "alembic>=1.14.0",',
                "]",
                "",
            ]
        ),
        encoding="utf-8",
    )

    _remove_pyproject_database_dependencies(pyproject_path)

    pyproject = pyproject_path.read_text(encoding="utf-8")
    assert "fastapi[standard]" in pyproject
    assert "SQLAlchemy" not in pyproject
    assert "psycopg[binary]" not in pyproject
    assert "alembic" not in pyproject


def test_database_free_python_cleanup_uses_python_structure(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / "settings.py"
    settings_path.write_text(
        """from pydantic import field_validator, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "api"
    database_url: str = Field(
        default="sqlite:///./poleposition.db",
        description="Database URL",
    )
    log_format: str = "text"

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        return value
""",
        encoding="utf-8",
    )
    lifespan_path = tmp_path / "lifespan.py"
    lifespan_path.write_text(
        """from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.bootstrap.logging import get_logger
from api.db.models import import_models


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import_models()
    yield
""",
        encoding="utf-8",
    )
    run_path = tmp_path / "run.py"
    run_path.write_text(
        """from api.bootstrap.logging import print_startup_table
from api.settings import get_settings


def main() -> None:
    settings = get_settings()
    print_startup_table(
        app_name=settings.app_name,
        database_url=settings.database_url,
        app_env=settings.app_env,
    )
""",
        encoding="utf-8",
    )

    _remove_settings_database_url(settings_path)
    _remove_lifespan_model_imports(lifespan_path)
    _remove_run_database_summary(run_path)

    settings = settings_path.read_text(encoding="utf-8")
    lifespan = lifespan_path.read_text(encoding="utf-8")
    run = run_path.read_text(encoding="utf-8")

    assert "from pydantic import field_validator" in settings
    assert "Field" not in settings
    assert "database_url" not in settings
    assert "import_models" not in lifespan
    assert "database_url" not in run
    ast.parse(settings)
    ast.parse(lifespan)
    ast.parse(run)


def test_generated_project_uses_enterprise_template_layout(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"

    expected_paths = [
        project_root / "AGENTS.md",
        project_root / "Dockerfile",
        project_root / ".dockerignore",
        project_root / ".poleposition.toml",
        project_root / "compose.yaml",
        project_root / "alembic.ini",
        project_root / ".gitignore",
        project_root / "migrations" / "env.py",
        project_root / "migrations" / "script.py.mako",
        project_root / "migrations" / "versions" / "__init__.py",
        package_root / "run.py",
        package_root / "settings.py",
        package_root / "auth" / "__init__.py",
        package_root / "auth" / "dependencies.py",
        package_root / "auth" / "schemas.py",
        package_root / "auth" / "service.py",
        package_root / "auth" / "token.py",
        package_root / "bootstrap" / "logging.py",
        package_root / "bootstrap" / "errors.py",
        package_root / "bootstrap" / "middleware.py",
        package_root / "bootstrap" / "lifespan.py",
        package_root / "api" / "deps.py",
        package_root / "db" / "session.py",
        package_root / "db" / "base.py",
        package_root / "domain" / "exceptions.py",
        package_root / "modules" / "status" / "router.py",
        package_root / "modules" / "status" / "services" / "__init__.py",
        package_root / "modules" / "status" / "services" / "status_service.py",
        project_root / "tests" / "conftest.py",
        project_root / "tests" / "integration" / "test_status.py",
    ]

    for path in expected_paths:
        assert path.exists(), f"Expected generated file is missing: {path}"

    assert not (package_root / "modules" / "status" / "service.py").exists()

    removed_sample_paths = [
        project_root / "migrations" / "versions" / "0001_create_races_table.py",
        package_root / "modules" / "profile",
        package_root / "modules" / "races",
        project_root / "tests" / "integration" / "test_profile.py",
        project_root / "tests" / "integration" / "test_races.py",
        project_root / "tests" / "unit" / "test_race_service.py",
    ]
    for path in removed_sample_paths:
        assert not path.exists(), f"Sample path should not be generated: {path}"


def test_generated_project_python_files_compile(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode == 0

    _assert_python_files_compile(tmp_path / "myapp")


def test_generated_project_does_not_copy_pycache(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode == 0
    generated_pycache = list((tmp_path / "myapp").rglob("__pycache__"))

    assert generated_pycache == []


def test_generated_project_renders_database_and_module_placeholders(
    tmp_path: Path,
):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    package_root = project_root / "src" / "demo_app"

    env_example = (project_root / ".env.example").read_text(encoding="utf-8")
    agents_guide = (project_root / "AGENTS.md").read_text(encoding="utf-8")
    app_module = (package_root / "app.py").read_text(encoding="utf-8")
    main_module = (package_root / "main.py").read_text(encoding="utf-8")
    run_module = (package_root / "run.py").read_text(encoding="utf-8")
    settings_module = (package_root / "settings.py").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")
    dockerfile = (project_root / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (project_root / ".dockerignore").read_text(encoding="utf-8")
    compose_file = (project_root / "compose.yaml").read_text(encoding="utf-8")
    logging_module = (package_root / "bootstrap" / "logging.py").read_text(
        encoding="utf-8"
    )
    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(
        encoding="utf-8"
    )
    middleware_module = (
        package_root / "bootstrap" / "middleware.py"
    ).read_text(encoding="utf-8")
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(
        encoding="utf-8"
    )
    status_service = (
        package_root / "modules" / "status" / "services" / "status_service.py"
    ).read_text(encoding="utf-8")
    auth_dependencies = (package_root / "auth" / "dependencies.py").read_text(
        encoding="utf-8"
    )
    auth_token = (package_root / "auth" / "token.py").read_text(
        encoding="utf-8"
    )
    db_models_path = package_root / "db" / "models.py"
    db_models = db_models_path.read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///./poleposition.db" in env_example
    assert (
        "This file is for coding agents working in this PolePosition-generated"
        in agents_guide
    )
    assert "`polepos add module <name>`" in agents_guide
    assert "`polepos remove module <name>`" in agents_guide
    assert "`polepos remove module <name> --wiring-only`" in agents_guide
    assert "`polepos check`" in agents_guide
    assert "`polepos check --json`" in agents_guide
    assert "{{project" not in agents_guide
    assert "src/demo_app/api/router.py" in readme
    assert "uv sync --extra dev" in readme
    assert "uv run pytest" in readme
    assert 'prefix="/garage"' in readme
    assert "GET /api/v1/garage/" in readme
    assert "polepos check --json" in readme
    assert "If the module directory was already deleted manually" in readme
    assert "router, model, and export wiring" in readme
    assert "polepos remove module <name> --wiring-only" in readme
    assert readme.count("Use `polepos remove module <name> --wiring-only`") == 1
    assert "{{project" not in readme
    assert "CORS_ENABLED=true" in env_example
    assert 'CORS_ALLOW_ORIGINS=["http://localhost:3000"' in env_example
    assert "# CORS_ALLOW_ORIGIN_REGEX=" in env_example
    assert (
        'CORS_ALLOW_METHODS=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]'
        in env_example
    )
    assert (
        'CORS_ALLOW_HEADERS=["Authorization","Content-Type","X-Request-ID"]'
        in env_example
    )
    assert 'CORS_EXPOSE_HEADERS=["X-Request-ID"]' in env_example
    assert "CORS_MAX_AGE=600" in env_example
    assert "POSTGRES_DB=app" in env_example
    assert "POSTGRES_USER=postgres" in env_example
    assert "POSTGRES_PASSWORD=postgres" in env_example
    assert "POSTGRES_PORT=5432" in env_example
    assert "AUTH_SECRET_KEY=change-me-in-production" in env_example
    assert "AUTH_ALGORITHM=HS256" in env_example
    assert "AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60" in env_example
    assert "AUTH_ISSUER=demo-app" in env_example
    assert "APP_HOST=127.0.0.1" in env_example
    assert "LOG_FORMAT=text" in env_example
    assert "UVICORN_WORKERS=1" in env_example
    assert "# UVICORN_USE_COLORS=" in env_example
    assert "# UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=" in env_example
    assert "# UVICORN_LIMIT_CONCURRENCY=" in env_example
    assert "# UVICORN_LIMIT_MAX_REQUESTS=" in env_example
    assert "UVICORN_LIMIT_MAX_REQUESTS_JITTER=0" in env_example
    assert 'name = "demo-app"' in pyproject
    assert 'package = "demo_app"' in manifest
    assert 'db = "sqlite"' in manifest
    assert 'status = "starter"' in manifest
    assert '"PyJWT>=' in pyproject
    assert '"psycopg[binary]>=' in pyproject
    assert "[project.optional-dependencies]" in pyproject
    assert "dev = [" in pyproject
    assert 'build-backend = "hatchling.build"' in pyproject
    assert 'packages = ["src/demo_app"]' in pyproject
    assert 'CMD ["uv", "run", "python", "-m", "demo_app.run"]' in dockerfile
    assert "COPY pyproject.toml README.md alembic.ini ./" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile
    assert "RUN uv sync --no-dev" in dockerfile
    assert ".venv" in dockerignore
    assert "poleposition.db" in dockerignore
    assert "services:" in compose_file
    assert "image: postgres:16" in compose_file
    assert "DATABASE_URL: postgresql+psycopg://" in compose_file
    assert "APP_HOST: 0.0.0.0" in compose_file
    assert '- "${POSTGRES_PORT:-5432}:5432"' in compose_file
    assert "# polepos:router-imports" in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert "# polepos:router-includes" in (
        package_root / "api" / "router.py"
    ).read_text(encoding="utf-8")
    assert "# polepos:model-imports" in db_models
    assert "    pass" in db_models
    compile(db_models, str(db_models_path), "exec")
    assert "# polepos:module-exports" in (
        package_root / "modules" / "__init__.py"
    ).read_text(encoding="utf-8")
    assert "# polepos:auth-settings" in settings_module
    assert "# polepos:integration-settings" in settings_module
    assert "# polepos:llm-settings" in settings_module
    assert "# polepos:auth-env" in env_example
    assert "# polepos:integration-env" in env_example
    assert "# polepos:llm-env" in env_example
    assert "from demo_app.api.router import api_router" in app_module
    assert "uvicorn.run(" in run_module
    assert '"demo_app.main:app"' in run_module
    assert "from demo_app.app import create_app" in main_module
    assert "app = create_app()" in main_module
    assert "app = create_app()" not in app_module
    assert (
        "from demo_app.bootstrap.logging import print_startup_table"
        in run_module
    )
    assert "print_startup_table(" in run_module
    assert (
        'docs_url = f"http://{display_host}:{app_port}/docs"' in logging_module
    )
    assert (
        'openapi_url = f"http://{display_host}:{app_port}/openapi.json"'
        in logging_module
    )
    assert "def render_startup_table(" in logging_module
    assert (
        "def print_startup_table(**kwargs: object) -> None:" in logging_module
    )
    assert "PolePosition Startup" in logging_module
    assert "host=settings.app_host" in run_module
    assert "workers=settings.uvicorn_workers" in run_module
    assert (
        "limit_max_requests=settings.uvicorn_limit_max_requests" in run_module
    )
    assert (
        "limit_max_requests_jitter=settings.uvicorn_limit_max_requests_jitter"
        in run_module
    )
    assert (
        "timeout_worker_healthcheck=settings.uvicorn_timeout_worker_healthcheck"
        in run_module
    )
    assert "sys.dont_write_bytecode = True" not in run_module
    assert 'app_host: str = "127.0.0.1"' in settings_module
    assert "uvicorn_workers: int = 1" in settings_module
    assert 'log_format: str = "text"' in settings_module
    assert "cors_enabled: bool = True" in settings_module
    assert "cors_allow_origins: list[str] = [" in settings_module
    assert "cors_allow_origin_regex: str | None = None" in settings_module
    assert "cors_allow_credentials: bool = True" in settings_module
    assert "cors_max_age: int = 600" in settings_module
    assert "uvicorn_limit_max_requests: int | None = None" in settings_module
    assert "uvicorn_limit_max_requests_jitter: int = 0" in settings_module
    assert 'auth_secret_key: str = "change-me-in-production"' in settings_module
    assert 'auth_algorithm: str = "HS256"' in settings_module
    assert "auth_access_token_expire_minutes: int = 60" in settings_module
    assert 'auth_issuer: str = "demo-app"' in settings_module
    assert "@field_validator(" in settings_module
    assert (
        "def empty_string_to_none(cls, value: object) -> object:"
        in settings_module
    )
    assert (
        "def parse_list_env(cls, value: object) -> object:" in settings_module
    )
    assert "def get_logger(name: str) -> logging.Logger:" in logging_module
    assert (
        '_request_id_context = ContextVar("request_id", default="-")'
        in logging_module
    )
    assert "def bind_request_id(request_id: str) -> Token:" in logging_module
    assert "def reset_request_id(token: Token) -> None:" in logging_module
    assert "record.request_id = get_request_id()" in logging_module
    assert "class JsonFormatter(logging.Formatter):" in logging_module
    assert 'if log_format.lower() == "json":' in logging_module
    assert '"timestamp": datetime.fromtimestamp(' in logging_module
    assert '"request_id": getattr(record, "request_id", "-")' in logging_module
    assert (
        "from demo_app.bootstrap.logging import bind_request_id, "
        "reset_request_id" in middleware_module
    )
    assert (
        "from starlette.types import ASGIApp, Message, Receive, Scope, Send"
        in middleware_module
    )
    assert "class RequestContextMiddleware:" in middleware_module
    assert 'if message["type"] == "http.response.start":' in middleware_module
    assert 'if key.lower() != b"x-request-id"' in middleware_module
    assert (
        'response_headers.append((b"x-request-id", '
        'request_id.encode("latin-1")))' in middleware_module
    )
    assert "app.add_middleware(RequestContextMiddleware)" in middleware_module
    assert '@app.middleware("http")' not in middleware_module
    assert (
        "from fastapi.middleware.cors import CORSMiddleware"
        in middleware_module
    )
    assert "allow_origins=settings.cors_allow_origins" in middleware_module
    assert (
        "allow_origin_regex=settings.cors_allow_origin_regex"
        in middleware_module
    )
    assert (
        "allow_credentials=settings.cors_allow_credentials" in middleware_module
    )
    assert "allow_methods=settings.cors_allow_methods" in middleware_module
    assert "allow_headers=settings.cors_allow_headers" in middleware_module
    assert "expose_headers=settings.cors_expose_headers" in middleware_module
    assert "max_age=settings.cors_max_age" in middleware_module
    assert "token = bind_request_id(request_id)" in middleware_module
    assert "reset_request_id(token)" in middleware_module
    assert "from demo_app.bootstrap.logging import get_logger" in lifespan
    assert "logger = get_logger(__name__)" in lifespan
    assert "from demo_app.settings import get_settings" in app_module
    assert "log_format=settings.log_format" in app_module
    assert "app_name=settings.app_name" in app_module
    assert "environment=settings.app_env" in app_module
    assert "from demo_app.bootstrap.logging import get_logger" in status_service
    assert "logger = get_logger(__name__)" in status_service
    assert "from demo_app import __version__" in status_service
    assert "bearer_scheme = HTTPBearer(auto_error=False)" in auth_dependencies
    assert "def get_current_user(" in auth_dependencies
    assert "def require_roles(*roles: str)" in auth_dependencies
    assert "def create_access_token(" in auth_token
    assert "def decode_access_token(token: str" in auth_token
    assert "sys.dont_write_bytecode = True" not in tests_conftest
    assert "{{project" not in app_module
    assert "{{project" not in status_service


def test_generated_app_factory_initializes_settings_inside_create_app(
    tmp_path: Path,
) -> None:
    result = run_cli(tmp_path, "start", "runtime-app")

    assert result.returncode == 0

    project_root = tmp_path / "runtime-app"
    package_root = project_root / "src" / "runtime_app"
    app_source = (package_root / "app.py").read_text(encoding="utf-8")
    app_tree = ast.parse(app_source)
    create_app = next(
        node
        for node in app_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )

    module_assignments = [
        node for node in app_tree.body if isinstance(node, ast.Assign)
    ]
    create_app_assignments = [
        node for node in create_app.body if isinstance(node, ast.Assign)
    ]

    assert not any(
        _assigns_name(node, "settings") for node in module_assignments
    )
    assert not any(
        _assigns_call(node, "app", "create_app") for node in module_assignments
    )
    assert any(
        _assigns_call(node, "settings", "get_settings")
        for node in create_app_assignments
    )
    assert any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and _call_name(node.value) == "setup_logging"
        for node in create_app.body
    )


def test_generated_logging_context_includes_request_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import importlib
    import json
    import logging

    result = run_cli(tmp_path, "start", "request-id-app")

    assert result.returncode == 0

    project_root = tmp_path / "request-id-app"
    package_name = "request_id_app"
    request_id = "req-test-123"

    monkeypatch.syspath_prepend(str(project_root / "src"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv(
        "DATABASE_URL", f"sqlite:///{tmp_path / 'request-id.db'}"
    )

    root_logger = logging.getLogger()
    previous_handlers = list(root_logger.handlers)
    previous_level = root_logger.level

    try:
        logging_module = importlib.import_module(
            f"{package_name}.bootstrap.logging"
        )
        logging_module.setup_logging(
            log_format="json",
            app_name="request-id-app",
            environment="test",
        )

        token = logging_module.bind_request_id(request_id)
        try:
            logging_module.get_logger("request-id-test").info("bound request")
        finally:
            logging_module.reset_request_id(token)

        logging_module.get_logger("request-id-test").info("outside request")

        output = capsys.readouterr().out
        logs = [
            json.loads(line)
            for line in output.splitlines()
            if line.startswith("{")
        ]

        assert any(
            log.get("message") == "bound request"
            and log.get("request_id") == request_id
            for log in logs
        )
        assert any(
            log.get("message") == "outside request"
            and log.get("request_id") == "-"
            for log in logs
        )
    finally:
        for module_name in list(sys.modules):
            if module_name == package_name or module_name.startswith(
                f"{package_name}."
            ):
                sys.modules.pop(module_name, None)
        root_logger.handlers.clear()
        root_logger.handlers.extend(previous_handlers)
        root_logger.setLevel(previous_level)


def test_generated_project_includes_alembic_support(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    migrations_env = (project_root / "migrations" / "env.py").read_text(
        encoding="utf-8"
    )
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert '"alembic>=' in pyproject
    assert "from demo_app.db.base import Base" in migrations_env
    assert "from demo_app.db.models import import_models" in migrations_env
    assert "from demo_app.settings import get_settings" in migrations_env
    assert "target_metadata = Base.metadata" in migrations_env
    assert "polepos db upgrade" in readme
    assert 'polepos db revision -m "add garage table"' in readme
    assert (
        'uv run alembic revision --autogenerate -m "add garage table"' in readme
    )
    assert "alembic.ini\nmigrations/\n  versions/\nsrc/demo_app/" in readme
    assert "\n  db/\n" in readme
    assert "{{project" not in migrations_env


def test_generated_project_includes_auth_foundation(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    auth_schemas = (
        project_root / "src" / "demo_app" / "auth" / "schemas.py"
    ).read_text(encoding="utf-8")
    auth_dependencies = (
        project_root / "src" / "demo_app" / "auth" / "dependencies.py"
    ).read_text(encoding="utf-8")
    auth_token = (
        project_root / "src" / "demo_app" / "auth" / "token.py"
    ).read_text(encoding="utf-8")

    assert "GET /api/v1/profile/me" not in readme
    assert "GET /api/v1/profile/admin-preview" not in readme
    assert "class AuthenticatedUser(BaseModel):" in auth_schemas
    assert "def get_current_user(" in auth_dependencies
    assert "def require_roles(*roles: str)" in auth_dependencies
    assert "def create_access_token(" in auth_token
    assert "def decode_access_token(token: str" in auth_token


def test_generated_project_includes_docker_workflow_docs(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "docker compose up --build" in readme
    assert "docker compose run --rm app uv run alembic upgrade head" in readme
    assert "runs Alembic directly inside the generated app container" in readme
    assert (
        "For host-based development, keep using `polepos db upgrade`." in readme
    )


def test_generated_project_is_migration_first(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    package_root = project_root / "src" / "demo_app"

    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(
        encoding="utf-8"
    )
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "Base.metadata.create_all" not in lifespan
    assert "import_models()" in lifespan
    assert "polepos db upgrade" in result.stdout
    assert "polepos db upgrade" in readme


def test_no_bytecode_flag_updates_generated_run_instructions(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app", "--no-bytecode")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    run_module = (project_root / "src" / "demo_app" / "run.py").read_text(
        encoding="utf-8"
    )
    migrations_env = (project_root / "migrations" / "env.py").read_text(
        encoding="utf-8"
    )
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(
        encoding="utf-8"
    )

    expected_migration_command = "PYTHONDONTWRITEBYTECODE=1 polepos db upgrade"
    expected_run_command = (
        "PYTHONDONTWRITEBYTECODE=1 uv run python -m demo_app.run"
    )
    assert expected_migration_command in result.stdout
    assert expected_migration_command in readme
    assert expected_run_command in result.stdout
    assert expected_run_command in readme
    assert (
        "Configured generated local Python commands to start without "
        "bytecode writes." in result.stdout
    )
    assert "generated with `--no-bytecode`" in readme
    assert "PYTHONDONTWRITEBYTECODE=1" in readme
    assert "{{no_bytecode_command_prefix}}" not in readme
    assert "sys.dont_write_bytecode = True" not in run_module
    assert "sys.dont_write_bytecode = True" not in migrations_env
    assert "sys.dont_write_bytecode = True" not in tests_conftest


def test_generated_gitignore_ignores_bytecode_artifacts(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    gitignore = (tmp_path / "demo-app" / ".gitignore").read_text(
        encoding="utf-8"
    )
    assert "__pycache__/" in gitignore
    assert "*.pyc" in gitignore
    assert "*.egg-info/" in gitignore
    assert ".env" in gitignore


def test_generated_env_example_is_safe_to_copy(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    env_example = (tmp_path / "demo-app" / ".env.example").read_text(
        encoding="utf-8"
    )
    env_lines = env_example.splitlines()

    assert "UVICORN_LIMIT_MAX_REQUESTS=" not in env_lines
    assert "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=" not in env_lines
    assert "UVICORN_LIMIT_CONCURRENCY=" not in env_lines


def test_packaging_includes_hidden_template_files() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    packages = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
    package_data = pyproject["tool"]["setuptools"]["package-data"][
        "pole_position"
    ]
    exclude_package_data = pyproject["tool"]["setuptools"][
        "exclude-package-data"
    ]["pole_position"]
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "pole_position*" in packages
    assert "polepos*" in packages
    assert "template/AGENTS.md" in package_data
    assert "template/.env.example" in package_data
    assert "template/.gitignore" in package_data
    assert "template/.dockerignore" in package_data
    assert "cli/services/module_templates/files/**/*.tpl" in package_data
    assert "template/**/__pycache__/*" in exclude_package_data
    assert "template/**/*.pyc" in exclude_package_data
    assert (
        "recursive-include "
        "pole_position/cli/services/module_templates/files *.tpl" in manifest
    )
    assert "recursive-include pole_position/template *" in manifest
    assert "include pole_position/template/AGENTS.md" in manifest
    assert "include pole_position/template/.dockerignore" in manifest
    assert "include pole_position/template/.env.example" in manifest
    assert "include pole_position/template/.gitignore" in manifest
    assert "global-exclude __pycache__ *.py[cod]" in manifest


def test_lockfile_version_matches_project_metadata() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    lockfile = tomllib.loads(
        (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    )
    poleposition_package = next(
        package
        for package in lockfile["package"]
        if package["name"] == "poleposition"
    )

    assert poleposition_package["version"] == pyproject["project"]["version"]


def test_install_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    from pole_position.cli.commands.startproject import run

    with patch(
        "pole_position.cli.commands.startproject.install_project_dependencies",
        return_value="uv",
    ) as mock_install:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["myapp", "--install"])

    captured = capsys.readouterr()
    mock_install.assert_called_once_with(project_path=Path("myapp"))
    assert "Dependencies installed successfully with uv." in captured.out
    assert "polepos db upgrade" in captured.out
    assert "uv run python -m myapp.run" in captured.out
    assert "alembic upgrade head" not in captured.out


def test_install_flag_prints_pip_next_steps_when_uv_is_unavailable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pole_position.cli.commands.startproject import run

    with patch(
        "pole_position.cli.commands.startproject.install_project_dependencies",
        return_value="pip",
    ):
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["myapp", "--install"])

    captured = capsys.readouterr()
    assert "Dependencies installed successfully with pip." in captured.out
    assert "source .venv/bin/activate" in captured.out
    assert "polepos db upgrade" in captured.out
    assert "python -m myapp.run" in captured.out
    assert "uv run alembic upgrade head" not in captured.out
    assert "python -m alembic upgrade head" not in captured.out
