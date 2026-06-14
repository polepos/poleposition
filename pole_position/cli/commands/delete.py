from pathlib import Path

from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.services.project_deleter import (
    delete_project,
    resolve_project_to_delete,
)
from pole_position.cli.usage import print_command_help

HELP_OPTIONS = {"-h", "--help"}
FORCE_OPTIONS = {"--force", "-y"}
TRACE_OPTIONS = {"--trace", "--dry-run"}


def _print_usage() -> None:
    print_command_help("delete")


def run(args: list[str]) -> None:
    if not args:
        _print_usage()
        raise SystemExit(1)

    raw_name: str | None = None
    force = False
    trace = False

    for argument in args:
        if argument in HELP_OPTIONS:
            _print_usage()
            return
        if argument in FORCE_OPTIONS:
            force = True
            continue
        if argument in TRACE_OPTIONS:
            trace = True
            continue
        if argument.startswith("-"):
            console.error(f"Unexpected option: {argument}")
            _print_usage()
            raise SystemExit(1)
        if raw_name is None:
            raw_name = argument.strip()
            continue
        console.error(f"Unexpected argument: {argument}")
        _print_usage()
        raise SystemExit(1)

    if not raw_name:
        _print_usage()
        raise SystemExit(1)

    try:
        target = resolve_project_to_delete(raw_name)
    except RuntimeError as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc

    if trace:
        console.heading(f"Deletion trace: {raw_name}")
        console.heading("Would remove:")
        console.item(str(target))
        console.info("Trace only: no files changed.")
        return

    if not force and not _confirm(target):
        console.info("Aborted. No files were deleted.")
        return

    try:
        result = delete_project(raw_name)
    except RuntimeError as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc

    console.success(f"Deleted project: {result.name}")
    console.heading("Removed:")
    console.item(str(result.project_root))


def _confirm(target: Path) -> bool:
    console.warn(f"This permanently deletes {target} and everything inside it.")
    try:
        answer = input("Delete this project? [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


command = Command(
    name="delete",
    handler=run,
    description="Delete a generated project directory",
)
