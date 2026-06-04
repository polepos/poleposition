from pole_position.cli.command import Command
from pole_position.cli.commands.db.downgrade import command as downgrade_cmd
from pole_position.cli.commands.db.revision import command as revision_cmd
from pole_position.cli.commands.db.status import command as status_cmd
from pole_position.cli.commands.db.upgrade import command as upgrade_cmd
from pole_position.cli.registry import CommandRegistry
from pole_position.cli.usage import print_command_help

subcommands = CommandRegistry()
subcommands.register(downgrade_cmd)
subcommands.register(revision_cmd)
subcommands.register(status_cmd)
subcommands.register(upgrade_cmd)


def run(args: list[str]) -> None:
    print_command_help("db")


command = Command(
    name="db",
    handler=run,
    description="Run database and migration commands",
    subcommands=subcommands,
)
