from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.services.completion import (
    SUPPORTED_SHELLS,
    complete,
    completion_script,
)
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos completion <shell>"
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    if not args or args[0] in HELP_OPTIONS:
        if not print_command_help("completion"):
            print(USAGE)
        return

    shell = args[0]
    if len(args) > 1:
        console.error(f"Unexpected argument: {args[1]}")
        print(USAGE)
        raise SystemExit(1)

    try:
        script = completion_script(shell)
    except ValueError as exc:
        console.error(str(exc))
        print(USAGE)
        raise SystemExit(1) from exc

    print(script, end="")


def run_complete(args: list[str]) -> None:
    """Hidden completion backend.

    Prints one candidate per line for the word following ``args`` (the words
    already typed). It must stay quiet and exit zero so a broken completion can
    never disrupt the user's shell.
    """
    for candidate in complete(args):
        print(candidate)


command = Command(
    name="completion",
    handler=run,
    description="Print a shell completion script (bash, zsh, fish)",
)

complete_command = Command(
    name="__complete",
    handler=run_complete,
    description="Internal completion backend",
)


__all__ = ["command", "complete_command", "SUPPORTED_SHELLS"]
