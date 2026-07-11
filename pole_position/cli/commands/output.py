"""Shared success-output helpers for command handlers.

`add module`, `add integration`, `add auth`, and `remove module` all print the
same shape: sections of project-relative paths followed by next steps.
"""

from collections.abc import Iterable
from pathlib import Path

from pole_position.cli import console


def relative_to_project(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def print_path_section(
    heading: str, project_root: Path, paths: Iterable[Path]
) -> None:
    console.heading(heading)
    for path in paths:
        console.item(relative_to_project(project_root, path))


def print_next_steps(steps: Iterable[str]) -> None:
    console.heading("Next steps:")
    for step in steps:
        console.step(step)
