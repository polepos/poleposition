import shutil
import subprocess
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

    if shutil.which("alembic") is None:
        raise RuntimeError(
            "`alembic` is not installed or not available in PATH. "
            "Install project dependencies first."
        )

    command = ["alembic", subcommand, *(args or [])]

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
