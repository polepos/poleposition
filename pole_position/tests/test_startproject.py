from pathlib import Path
import os
import py_compile
import subprocess
import sys
from unittest.mock import patch

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


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


def _assert_python_files_compile(project_root: Path) -> None:
    python_files = sorted(project_root.rglob("*.py"))

    assert python_files
    for path in python_files:
        py_compile.compile(str(path), doraise=True)


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


def test_start_help_shows_usage_without_creating_project(tmp_path: Path):
    result = run_cli(tmp_path, "start", "--help")

    assert result.returncode == 0
    assert (
        "Usage: polepos start <project_name> [--install] [--no-bytecode]"
        in result.stdout
    )
    assert list(tmp_path.iterdir()) == []


def test_start_rejects_unknown_option(tmp_path: Path):
    result = run_cli(tmp_path, "start", "--template")

    assert result.returncode != 0
    assert "Unexpected option: --template" in result.stdout
    assert (
        "Usage: polepos start <project_name> [--install] [--no-bytecode]"
        in result.stdout
    )
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


def test_generated_project_uses_enterprise_template_layout(tmp_path: Path):
    result = run_cli(tmp_path, "start", "myapp")

    assert result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"

    expected_paths = [
        project_root / "AGENTS.md",
        project_root / "Dockerfile",
        project_root / ".dockerignore",
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


def test_generated_project_renders_database_and_module_placeholders(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    package_root = project_root / "src" / "demo_app"

    env_example = (project_root / ".env.example").read_text(encoding="utf-8")
    agents_guide = (project_root / "AGENTS.md").read_text(encoding="utf-8")
    app_module = (package_root / "app.py").read_text(encoding="utf-8")
    run_module = (package_root / "run.py").read_text(encoding="utf-8")
    settings_module = (package_root / "settings.py").read_text(encoding="utf-8")
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    dockerfile = (project_root / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (project_root / ".dockerignore").read_text(encoding="utf-8")
    compose_file = (project_root / "compose.yaml").read_text(encoding="utf-8")
    logging_module = (package_root / "bootstrap" / "logging.py").read_text(encoding="utf-8")
    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(encoding="utf-8")
    middleware_module = (package_root / "bootstrap" / "middleware.py").read_text(encoding="utf-8")
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(encoding="utf-8")
    status_service = (
        package_root / "modules" / "status" / "services" / "status_service.py"
    ).read_text(encoding="utf-8")
    auth_dependencies = (
        package_root / "auth" / "dependencies.py"
    ).read_text(encoding="utf-8")
    auth_token = (package_root / "auth" / "token.py").read_text(encoding="utf-8")
    db_models_path = package_root / "db" / "models.py"
    db_models = db_models_path.read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///./poleposition.db" in env_example
    assert "This file is for coding agents working in this PolePosition-generated" in agents_guide
    assert "`polepos add module <name>`" in agents_guide
    assert "`polepos remove module <name>`" in agents_guide
    assert "`polepos check`" in agents_guide
    assert "{{project" not in agents_guide
    assert "CORS_ENABLED=true" in env_example
    assert 'CORS_ALLOW_ORIGINS=["http://localhost:3000"' in env_example
    assert "# CORS_ALLOW_ORIGIN_REGEX=" in env_example
    assert 'CORS_ALLOW_METHODS=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]' in env_example
    assert 'CORS_ALLOW_HEADERS=["Authorization","Content-Type","X-Request-ID"]' in env_example
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
    assert '"PyJWT>=' in pyproject
    assert '"psycopg[binary]>=' in pyproject
    assert "[project.optional-dependencies]" in pyproject
    assert "dev = [" in pyproject
    assert 'build-backend = "hatchling.build"' in pyproject
    assert 'packages = ["src/demo_app"]' in pyproject
    assert 'CMD ["uv", "run", "python", "-m", "demo_app.run"]' in dockerfile
    assert "RUN uv sync --no-dev" in dockerfile
    assert ".venv" in dockerignore
    assert "poleposition.db" in dockerignore
    assert "services:" in compose_file
    assert "image: postgres:16" in compose_file
    assert "DATABASE_URL: postgresql+psycopg://" in compose_file
    assert 'APP_HOST: 0.0.0.0' in compose_file
    assert '- "${POSTGRES_PORT:-5432}:5432"' in compose_file
    assert "# polepos:router-imports" in (package_root / "api" / "router.py").read_text(encoding="utf-8")
    assert "# polepos:router-includes" in (package_root / "api" / "router.py").read_text(encoding="utf-8")
    assert "# polepos:model-imports" in db_models
    assert "    pass" in db_models
    compile(db_models, str(db_models_path), "exec")
    assert "# polepos:module-exports" in (package_root / "modules" / "__init__.py").read_text(encoding="utf-8")
    assert "# polepos:auth-settings" in settings_module
    assert "# polepos:integration-settings" in settings_module
    assert "# polepos:llm-settings" in settings_module
    assert "# polepos:auth-env" in env_example
    assert "# polepos:integration-env" in env_example
    assert "# polepos:llm-env" in env_example
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
    assert 'def empty_string_to_none(cls, value: object) -> object:' in settings_module
    assert "def parse_list_env(cls, value: object) -> object:" in settings_module
    assert "def get_logger(name: str) -> logging.Logger:" in logging_module
    assert "class JsonFormatter(logging.Formatter):" in logging_module
    assert 'if log_format.lower() == "json":' in logging_module
    assert '"timestamp": datetime.fromtimestamp(' in logging_module
    assert '"request_id": getattr(record, "request_id", "-")' in logging_module
    assert "from fastapi.middleware.cors import CORSMiddleware" in middleware_module
    assert "allow_origins=settings.cors_allow_origins" in middleware_module
    assert "allow_origin_regex=settings.cors_allow_origin_regex" in middleware_module
    assert "allow_credentials=settings.cors_allow_credentials" in middleware_module
    assert "allow_methods=settings.cors_allow_methods" in middleware_module
    assert "allow_headers=settings.cors_allow_headers" in middleware_module
    assert "expose_headers=settings.cors_expose_headers" in middleware_module
    assert "max_age=settings.cors_max_age" in middleware_module
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


def test_generated_project_includes_alembic_support(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    migrations_env = (project_root / "migrations" / "env.py").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert '"alembic>=' in pyproject
    assert "from demo_app.db.base import Base" in migrations_env
    assert "from demo_app.db.models import import_models" in migrations_env
    assert "from demo_app.settings import get_settings" in migrations_env
    assert "target_metadata = Base.metadata" in migrations_env
    assert "polepos db upgrade" in readme
    assert 'polepos db revision -m "add garage table"' in readme
    assert 'uv run alembic revision --autogenerate -m "add garage table"' in readme
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


def test_generated_project_is_migration_first(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    project_root = tmp_path / "demo-app"
    package_root = project_root / "src" / "demo_app"

    lifespan = (package_root / "bootstrap" / "lifespan.py").read_text(encoding="utf-8")
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
    run_module = (project_root / "src" / "demo_app" / "run.py").read_text(encoding="utf-8")
    migrations_env = (project_root / "migrations" / "env.py").read_text(encoding="utf-8")
    tests_conftest = (project_root / "tests" / "conftest.py").read_text(encoding="utf-8")

    expected_migration_command = "PYTHONDONTWRITEBYTECODE=1 polepos db upgrade"
    expected_run_command = "PYTHONDONTWRITEBYTECODE=1 uv run python -m demo_app.run"
    assert expected_migration_command in result.stdout
    assert expected_migration_command in readme
    assert expected_run_command in result.stdout
    assert expected_run_command in readme
    assert "Configured generated local Python commands to start without bytecode writes." in result.stdout
    assert "generated with `--no-bytecode`" in readme
    assert "PYTHONDONTWRITEBYTECODE=1" in readme
    assert "{{no_bytecode_command_prefix}}" not in readme
    assert "sys.dont_write_bytecode = True" not in run_module
    assert "sys.dont_write_bytecode = True" not in migrations_env
    assert "sys.dont_write_bytecode = True" not in tests_conftest


def test_generated_gitignore_ignores_bytecode_artifacts(tmp_path: Path):
    result = run_cli(tmp_path, "start", "demo-app")

    assert result.returncode == 0

    gitignore = (tmp_path / "demo-app" / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__/" in gitignore
    assert "*.pyc" in gitignore
    assert "*.egg-info/" in gitignore


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

    assert "template/AGENTS.md" in package_data
    assert "template/.env.example" in package_data
    assert "template/.gitignore" in package_data
    assert "template/.dockerignore" in package_data
    assert "cli/services/module_templates/files/**/*.tpl" in package_data
    assert "template/**/__pycache__/*" in exclude_package_data
    assert "template/**/*.pyc" in exclude_package_data
    assert "recursive-include pole_position/cli/services/module_templates/files *.tpl" in manifest
    assert "recursive-include pole_position/template *" in manifest
    assert "include pole_position/template/AGENTS.md" in manifest
    assert "include pole_position/template/.dockerignore" in manifest
    assert "include pole_position/template/.env.example" in manifest
    assert "include pole_position/template/.gitignore" in manifest
    assert "global-exclude __pycache__ *.py[cod]" in manifest


def test_lockfile_version_matches_project_metadata() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lockfile = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    poleposition_package = next(
        package
        for package in lockfile["package"]
        if package["name"] == "poleposition"
    )

    assert poleposition_package["version"] == pyproject["project"]["version"]


def test_install_flag(tmp_path: Path):
    from pole_position.cli.commands.startproject import run

    with patch(
        "pole_position.cli.commands.startproject.install_project_dependencies",
        return_value="uv",
    ) as mock_install:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["myapp", "--install"])

    mock_install.assert_called_once_with(project_path=Path("myapp"))
   

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
