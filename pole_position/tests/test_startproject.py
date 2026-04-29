from pathlib import Path
import os
import subprocess
import sys
import tomllib
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


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

def test_create_project(tmp_path: Path):
    project_name = "myapp"

    result = run_cli(tmp_path, "start", project_name)

    assert result.returncode == 0
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

def test_existing_directory(tmp_path: Path):
    project_path = tmp_path / "myapp"
    project_path.mkdir()

    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode != 0
    assert "already exists" in result.stdout

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


def test_generated_project_uses_enterprise_template_layout(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"

    expected_paths = [
        project_root / "Dockerfile",
        project_root / ".dockerignore",
        project_root / "compose.yaml",
        project_root / "alembic.ini",
        project_root / ".gitignore",
        project_root / "migrations" / "env.py",
        project_root / "migrations" / "script.py.mako",
        project_root / "migrations" / "versions" / "__init__.py",
        project_root / "migrations" / "versions" / "0001_create_races_table.py",
        package_root / "run.py",
        package_root / "settings.py",
        package_root / "bootstrap" / "logging.py",
        package_root / "bootstrap" / "errors.py",
        package_root / "bootstrap" / "middleware.py",
        package_root / "bootstrap" / "lifespan.py",
        package_root / "api" / "deps.py",
        package_root / "db" / "session.py",
        package_root / "db" / "base.py",
        package_root / "domain" / "exceptions.py",
        package_root / "modules" / "status" / "router.py",
        package_root / "modules" / "status" / "service.py",
        package_root / "modules" / "races" / "model.py",
        package_root / "modules" / "races" / "repository.py",
        package_root / "modules" / "races" / "router.py",
        project_root / "tests" / "conftest.py",
        project_root / "tests" / "integration" / "test_status.py",
        project_root / "tests" / "integration" / "test_races.py",
        project_root / "tests" / "unit" / "test_race_service.py",
    ]

    for path in expected_paths:
        assert path.exists(), f"Expected generated file is missing: {path}"


def test_generated_project_does_not_copy_pycache(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode == 0
    generated_pycache = list((tmp_path / "myapp").rglob("__pycache__"))

    assert generated_pycache == []


def test_generated_project_renders_database_and_module_placeholders(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    package_root = project_root / "src" / "demo_app"

    env_example = (project_root / ".env.example").read_text(encoding="utf-8")
    app_module = (package_root / "app.py").read_text(encoding="utf-8")
    run_module = (package_root / "run.py").read_text(encoding="utf-8")
    settings_module = (package_root / "settings.py").read_text(encoding="utf-8")
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    dockerfile = (project_root / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (project_root / ".dockerignore").read_text(encoding="utf-8")
    compose_file = (project_root / "compose.yaml").read_text(encoding="utf-8")
    logging_module = (package_root / "bootstrap" / "logging.py").read_text(encoding="utf-8")
    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(encoding="utf-8")
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(encoding="utf-8")
    status_service = (
        package_root / "modules" / "status" / "service.py"
    ).read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///./poleposition.db" in env_example
    assert "POSTGRES_DB=app" in env_example
    assert "POSTGRES_USER=postgres" in env_example
    assert "POSTGRES_PASSWORD=postgres" in env_example
    assert "APP_HOST=127.0.0.1" in env_example
    assert "UVICORN_WORKERS=1" in env_example
    assert "# UVICORN_USE_COLORS=" in env_example
    assert "# UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=" in env_example
    assert "# UVICORN_LIMIT_CONCURRENCY=" in env_example
    assert "# UVICORN_LIMIT_MAX_REQUESTS=" in env_example
    assert "UVICORN_LIMIT_MAX_REQUESTS_JITTER=0" in env_example
    assert '"psycopg[binary]>=' in pyproject
    assert 'CMD ["uv", "run", "python", "-m", "demo_app.run"]' in dockerfile
    assert "RUN uv sync --no-dev" in dockerfile
    assert ".venv" in dockerignore
    assert "poleposition.db" in dockerignore
    assert "services:" in compose_file
    assert "image: postgres:16" in compose_file
    assert "DATABASE_URL: postgresql+psycopg://" in compose_file
    assert 'APP_HOST: 0.0.0.0' in compose_file
    assert "from demo_app.api.router import api_router" in app_module
    assert 'uvicorn.run(' in run_module
    assert '"demo_app.main:app"' in run_module
    assert "from demo_app.bootstrap.logging import print_startup_table" in run_module
    assert "print_startup_table(" in run_module
    assert 'docs_url = f"http://{display_host}:{app_port}/docs"' in logging_module
    assert 'openapi_url = f"http://{display_host}:{app_port}/openapi.json"' in logging_module
    assert "def render_startup_table(" in logging_module
    assert "def print_startup_table(**kwargs: object) -> None:" in logging_module
    assert "PolePosition Startup" in logging_module
    assert "host=settings.app_host" in run_module
    assert "workers=settings.uvicorn_workers" in run_module
    assert "limit_max_requests=settings.uvicorn_limit_max_requests" in run_module
    assert "limit_max_requests_jitter=settings.uvicorn_limit_max_requests_jitter" in run_module
    assert "timeout_worker_healthcheck=settings.uvicorn_timeout_worker_healthcheck" in run_module
    assert "sys.dont_write_bytecode = True" not in run_module
    assert "app_host: str = \"127.0.0.1\"" in settings_module
    assert "uvicorn_workers: int = 1" in settings_module
    assert "uvicorn_limit_max_requests: int | None = None" in settings_module
    assert "uvicorn_limit_max_requests_jitter: int = 0" in settings_module
    assert "@field_validator(" in settings_module
    assert 'def empty_string_to_none(cls, value: object) -> object:' in settings_module
    assert "def get_logger(name: str) -> logging.Logger:" in logging_module
    assert "from demo_app.bootstrap.logging import get_logger" in lifespan
    assert "logger = get_logger(__name__)" in lifespan
    assert "from demo_app.settings import get_settings" in app_module
    assert "from demo_app.bootstrap.logging import get_logger" in status_service
    assert "logger = get_logger(__name__)" in status_service
    assert "from demo_app import __version__" in status_service
    assert "sys.dont_write_bytecode = True" not in tests_conftest
    assert "{{project" not in app_module
    assert "{{project" not in status_service


def test_generated_project_includes_alembic_support(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    migrations_env = (project_root / "migrations" / "env.py").read_text(encoding="utf-8")
    initial_migration = (
        project_root / "migrations" / "versions" / "0001_create_races_table.py"
    ).read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert '"alembic>=' in pyproject
    assert "from demo_app.db.base import Base" in migrations_env
    assert "from demo_app.db.models import import_models" in migrations_env
    assert "from demo_app.settings import get_settings" in migrations_env
    assert "target_metadata = Base.metadata" in migrations_env
    assert "alembic upgrade head" in readme
    assert 'op.create_table(' in initial_migration
    assert '"races"' in initial_migration
    assert 'alembic revision --autogenerate -m "add garage table"' in readme
    assert "{{project" not in migrations_env


def test_generated_project_includes_docker_workflow_docs(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "docker compose up --build" in readme
    assert "docker compose run --rm app uv run alembic upgrade head" in readme


def test_generated_project_is_migration_first(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    package_root = project_root / "src" / "demo_app"

    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "Base.metadata.create_all" not in lifespan
    assert "import_models()" in lifespan
    assert "alembic upgrade head" in result.stdout
    assert "alembic upgrade head" in readme


def test_no_bytecode_flag_updates_generated_run_instructions(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app", "--no-bytecode")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    run_module = (project_root / "src" / "demo_app" / "run.py").read_text(encoding="utf-8")
    migrations_env = (project_root / "migrations" / "env.py").read_text(encoding="utf-8")
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(encoding="utf-8")

    expected_command = "uv run python -m demo_app.run"
    assert expected_command in result.stdout
    assert expected_command in readme
    assert "Configured generated runtime and migration entrypoints without Python bytecode writes." in result.stdout
    assert "generated with `--no-bytecode`" in readme
    assert "sys.dont_write_bytecode = True" in run_module
    assert "sys.dont_write_bytecode = True" in migrations_env
    assert "sys.dont_write_bytecode = True" in tests_conftest


def test_generated_gitignore_ignores_bytecode_artifacts(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    gitignore = (tmp_path / "demo-app" / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__/" in gitignore
    assert "*.pyc" in gitignore


def test_generated_env_example_is_safe_to_copy(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    env_example = (tmp_path / "demo-app" / ".env.example").read_text(encoding="utf-8")
    env_lines = env_example.splitlines()

    assert "UVICORN_LIMIT_MAX_REQUESTS=" not in env_lines
    assert "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=" not in env_lines
    assert "UVICORN_LIMIT_CONCURRENCY=" not in env_lines


def test_packaging_includes_hidden_template_files() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["pole_position"]
    exclude_package_data = pyproject["tool"]["setuptools"]["exclude-package-data"][
        "pole_position"
    ]
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "template/.env.example" in package_data
    assert "template/.gitignore" in package_data
    assert "template/.dockerignore" in package_data
    assert "template/**/__pycache__/*" in exclude_package_data
    assert "template/**/*.pyc" in exclude_package_data
    assert "recursive-include pole_position/template *" in manifest
    assert "include pole_position/template/.dockerignore" in manifest
    assert "include pole_position/template/.env.example" in manifest
    assert "include pole_position/template/.gitignore" in manifest
    assert "global-exclude __pycache__ *.py[cod]" in manifest

def test_install_flag(tmp_path: Path):
    from pole_position.cli.commands.startproject import run

    with patch("pole_position.cli.commands.startproject.install_project_dependencies") as mock_install:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["myapp", "--install"])

    mock_install.assert_called_once_with(project_path=Path("myapp"))
   
