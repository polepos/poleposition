from pole_position.cli.command import Command
from pole_position.cli.commands.add.auth import command as auth_cmd
from pole_position.cli.commands.add.integration import (
    command as integration_cmd,
)
from pole_position.cli.commands.add.module import command as module_cmd
from pole_position.cli.registry import CommandRegistry
from pole_position.cli.usage import print_command_help

subcommands = CommandRegistry()
subcommands.register(auth_cmd)
subcommands.register(integration_cmd)
subcommands.register(module_cmd)


def run(args: list[str]) -> None:
    print_command_help("add")


command = Command(
    name="add",
    handler=run,
    description="Grow the current project with new resources",
    subcommands=subcommands,
)
