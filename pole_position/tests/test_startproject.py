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

def test_install_flag(tmp_path: Path):
    from pole_position.cli.commands.startproject import run

    with patch("pole_position.cli.commands.startproject.install_project_dependencies") as mock_install:
        with pytest.MonkeyPatch.context() as mp:
            mp.chdir(tmp_path)
            run(["myapp", "--install"])

    mock_install.assert_called_once_with(project_path=Path("myapp"))
   
