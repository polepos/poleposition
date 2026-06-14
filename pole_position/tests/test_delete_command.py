import os
import subprocess
import sys
from pathlib import Path

import pytest

from pole_position.cli.services.project_deleter import (
    DeletedProjectResult,
    delete_project,
    resolve_project_to_delete,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(
    cwd: Path, *args: str, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
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
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def _start_project(tmp_path: Path, name: str = "myapp") -> Path:
    create_result = run_cli(tmp_path, "start", name)
    assert create_result.returncode == 0, create_result.stderr
    project_root = tmp_path / name
    assert project_root.is_dir()
    return project_root


def test_delete_help_shows_usage(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "delete", "--help")

    assert result.returncode == 0
    assert "Usage: polepos delete <project_name>" in result.stdout
    assert "--force" in result.stdout
    assert "--trace" in result.stdout


def test_delete_without_name_exits(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "delete")

    assert result.returncode == 1


def test_delete_force_removes_project(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    result = run_cli(tmp_path, "delete", "myapp", "--force")

    assert result.returncode == 0, result.stdout
    assert "Deleted project: myapp" in result.stdout
    assert not project_root.exists()


def test_delete_trace_keeps_project(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    result = run_cli(tmp_path, "delete", "myapp", "--trace")

    assert result.returncode == 0
    assert "Would remove:" in result.stdout
    assert "Trace only: no files changed." in result.stdout
    assert project_root.is_dir()


def test_delete_confirmation_yes_removes_project(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    result = run_cli(tmp_path, "delete", "myapp", stdin="y\n")

    assert result.returncode == 0
    assert not project_root.exists()


def test_delete_confirmation_no_aborts(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    result = run_cli(tmp_path, "delete", "myapp", stdin="n\n")

    assert result.returncode == 0
    assert "Aborted" in result.stdout
    assert project_root.is_dir()


def test_delete_missing_directory_errors(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "delete", "does-not-exist")

    assert result.returncode == 1
    assert "No project directory found to delete" in result.stdout


def test_delete_non_project_directory_refuses(tmp_path: Path) -> None:
    plain_dir = tmp_path / "plaindir"
    plain_dir.mkdir()

    result = run_cli(tmp_path, "delete", "plaindir")

    assert result.returncode == 1
    assert "does not look like a PolePosition project" in result.stdout
    assert plain_dir.is_dir()


def test_delete_refuses_current_directory(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    result = run_cli(project_root, "delete", ".")

    assert result.returncode == 1
    assert "current directory or a parent of it" in result.stdout
    assert project_root.is_dir()


def test_resolve_project_to_delete_validates(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    resolved = resolve_project_to_delete("myapp", cwd=tmp_path)
    assert resolved == project_root.resolve()

    with pytest.raises(RuntimeError, match="No project directory"):
        resolve_project_to_delete("missing", cwd=tmp_path)

    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    with pytest.raises(RuntimeError, match="does not look like"):
        resolve_project_to_delete("plain", cwd=tmp_path)

    with pytest.raises(RuntimeError, match="current directory or a parent"):
        resolve_project_to_delete(".", cwd=project_root)


def test_delete_project_trace_does_not_remove(tmp_path: Path) -> None:
    project_root = _start_project(tmp_path)

    result = delete_project("myapp", cwd=tmp_path, trace=True)

    assert isinstance(result, DeletedProjectResult)
    assert result.trace is True
    assert result.project_root == project_root.resolve()
    assert project_root.is_dir()
