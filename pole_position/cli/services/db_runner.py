import os
import shutil
import subprocess
import sys
from pathlib import Path

from pole_position.cli.services.project_locator import find_project_root


def run_alembic_command(
    subcommand: str,
    args: list[str] | None = None,
    cwd: Path | None = None,
) -> None:
    project_root = find_project_root(cwd)
    alembic_config = project_root / "alembic.ini"

    if not alembic_config.exists():
        raise RuntimeError(
            f"Alembic is not configured for this project: {alembic_config}"
        )

    command = _build_alembic_command(project_root, subcommand, args or [])

    try:
        subprocess.run(
            command,
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Alembic command failed: {' '.join(command)}"
        ) from exc


def _build_alembic_command(
    project_root: Path,
    subcommand: str,
    args: list[str],
) -> list[str]:
    uv = shutil.which("uv")
    if uv is not None:
        return ["uv", "run", "alembic", subcommand, *args]

    python = _find_python_runner(project_root)
    if python is None:
        raise RuntimeError(
            "Could not find a Python runner for Alembic. "
            "Use `uv sync --extra dev`, or activate a virtualenv with "
            "project dependencies "
            "installed via pip."
        )

    return [python, "-m", "alembic", subcommand, *args]


def _find_python_runner(project_root: Path) -> str | None:
    active_venv = os.environ.get("VIRTUAL_ENV")
    if active_venv:
        python = _venv_python(Path(active_venv))
        if python.exists():
            return str(python)

    project_venv_python = _venv_python(project_root / ".venv")
    if project_venv_python.exists():
        return str(project_venv_python)

    path_python = shutil.which("python") or shutil.which("python3")
    if path_python is not None:
        return path_python

    return sys.executable or None


def _venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"

    return venv_path / "bin" / "python"
