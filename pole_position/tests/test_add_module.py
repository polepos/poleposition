from pathlib import Path
import os
import subprocess
import sys


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


def test_add_command_shows_usage(tmp_path: Path):
    result = run_cli(tmp_path, "add")

    assert result.returncode == 0
    assert "Usage: polepos add <subcommand>" in result.stdout
    assert "module" in result.stdout


def test_add_module_creates_module_files_and_updates_router(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode == 0
    assert "Added module: garage" in result.stdout

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "garage"

    expected_files = [
        module_root / "__init__.py",
        module_root / "model.py",
        module_root / "repository.py",
        module_root / "router.py",
        module_root / "schemas.py",
        module_root / "service.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated module file is missing: {path}"

    router_content = (package_root / "api" / "router.py").read_text(encoding="utf-8")
    db_models_content = (package_root / "db" / "models.py").read_text(encoding="utf-8")

    assert "from myapp.modules.garage.router import router as garage_router" in router_content
    assert 'api_router.include_router(garage_router, prefix="/garage", tags=["garage"])' in router_content
    assert "from myapp.modules.garage import model" in db_models_content


def test_add_module_rejects_duplicate_module(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "module", "garage")
    second_result = run_cli(project_root, "add", "module", "garage")

    assert first_result.returncode == 0
    assert second_result.returncode != 0
    assert "Module already exists: garage" in second_result.stdout


def test_add_module_requires_poleposition_project(tmp_path: Path):
    result = run_cli(tmp_path, "add", "module", "garage")

    assert result.returncode != 0
    assert "does not look like a PolePosition project" in result.stdout
