from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.commands.output import (
    print_next_steps,
    print_path_section,
)
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

    print_path_section(
        "Created:",
        result.project_root,
        (*result.auth_files, *result.test_files),
    )
    print_path_section("Updated:", result.project_root, result.updated_files)
    print_next_steps(result.next_steps)


command = Command(
    name="auth",
    handler=run,
    description="Add an optional database-backed auth workflow",
)
