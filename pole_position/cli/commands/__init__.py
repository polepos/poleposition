from pole_position.cli.commands.add import command as add_cmd
from pole_position.cli.commands.check import command as check_cmd
from pole_position.cli.commands.completion import command as completion_cmd
from pole_position.cli.commands.completion import (
    complete_command as complete_cmd,
)
from pole_position.cli.commands.db import command as db_cmd
from pole_position.cli.commands.delete import command as delete_cmd
from pole_position.cli.commands.remove import command as remove_cmd
from pole_position.cli.commands.startproject import command as start_cmd
from pole_position.cli.commands.upgrade import command as upgrade_cmd
from pole_position.cli.commands.version import command as version_cmd
from pole_position.cli.help import command as help_cmd
from pole_position.cli.registry import registry


def register_commands() -> None:
    registry.register(add_cmd)
    registry.register(check_cmd)
    registry.register(completion_cmd)
    registry.register(complete_cmd)
    registry.register(db_cmd)
    registry.register(delete_cmd)
    registry.register(remove_cmd)
    registry.register(start_cmd)
    registry.register(upgrade_cmd)
    registry.register(version_cmd)
    registry.register(help_cmd)
