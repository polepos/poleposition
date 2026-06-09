from pole_position import __version__
from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos version"
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    if args and args[0] in HELP_OPTIONS:
        print_command_help("version")
        return

    if args:
        console.error(f"Unexpected argument: {args[0]}")
        print(USAGE)
        raise SystemExit(1)

    print(__version__)


command = Command(
    name="version",
    aliases=("-v", "--version"),
    handler=run,
    description="Show version",
)
