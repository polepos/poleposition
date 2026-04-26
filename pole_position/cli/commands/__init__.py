from pole_position.cli.registry import registry

from pole_position.cli.commands.startproject import command as start_cmd
from pole_position.cli.commands.version import command as version_cmd
from pole_position.cli.help import command as help_cmd


def register_commands() -> None:
    registry.register(start_cmd)
    registry.register(version_cmd)
    registry.register(help_cmd)
