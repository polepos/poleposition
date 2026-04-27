from pathlib import Path
import os
import subprocess
import sys
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
        project_root / "alembic.ini",
        project_root / "migrations" / "env.py",
        project_root / "migrations" / "script.py.mako",
        project_root / "migrations" / "versions" / "__init__.py",
        project_root / "migrations" / "versions" / "0001_create_races_table.py",
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
    status_service = (
        package_root / "modules" / "status" / "service.py"
    ).read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///./poleposition.db" in env_example
    assert "from demo_app.api.router import api_router" in app_module
    assert "from demo_app.settings import get_settings" in app_module
    assert "from demo_app import __version__" in status_service
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

def test_install_flag(tmp_path: Path):
    from pole_position.cli.commands.startproject import run

    with patch("pole_position.cli.commands.startproject.install_project_dependencies") as mock_install:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["myapp", "--install"])

    mock_install.assert_called_once_with(project_path=Path("myapp"))
   
