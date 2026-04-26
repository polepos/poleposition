from pole_position import __version__
from pole_position.cli.command import Command


def run(args: list[str]) -> None:
    print(__version__)


command = Command(
    name="version",
    aliases=("-v", "--version"),
    handler=run,
    description="Show version",
)