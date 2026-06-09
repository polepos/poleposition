from pathlib import Path

from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.services.auth_creator import AddedAuthResult, add_auth
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos add auth"
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    if len(args) == 1 and args[0] in HELP_OPTIONS:
        print_command_help("add", "auth")
        return

    if args:
        console.error(f"Unexpected argument: {args[0]}")
        print(USAGE)
        raise SystemExit(1)

    try:
        result = add_auth()
    except RuntimeError as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc

    _print_success(result)


def _print_success(result: AddedAuthResult) -> None:
    console.success("Added auth workflow")

    console.heading("Created:")
    for path in (*result.auth_files, *result.test_files):
        console.item(_relative_path(result, path))

    console.heading("Updated:")
    for path in result.updated_files:
        console.item(_relative_path(result, path))

    console.heading("Next steps:")
    for step in result.next_steps:
        console.step(step)


def _relative_path(result: AddedAuthResult, path: Path) -> str:
    return path.relative_to(result.project_root).as_posix()


command = Command(
    name="auth",
    handler=run,
    description="Add an optional database-backed auth workflow",
)
