from pole_position.cli.command import Command
from pole_position.cli.commands.remove.module import command as module_cmd
from pole_position.cli.registry import CommandRegistry
from pole_position.cli.usage import print_command_help

subcommands = CommandRegistry()
subcommands.register(module_cmd)


def run(args: list[str]) -> None:
    print_command_help("remove")


command = Command(
    name="remove",
    handler=run,
    description="Remove generated resources from the current project",
    subcommands=subcommands,
)
