from pole_position.cli.command import Command
from pole_position.cli.commands.db.downgrade import command as downgrade_cmd
from pole_position.cli.commands.db.revision import command as revision_cmd
from pole_position.cli.commands.db.upgrade import command as upgrade_cmd
from pole_position.cli.registry import CommandRegistry


subcommands = CommandRegistry()
subcommands.register(downgrade_cmd)
subcommands.register(revision_cmd)
subcommands.register(upgrade_cmd)


def run(args: list[str]) -> None:
    print("Usage: polepos db <subcommand>\n")
    print("Subcommands:")

    for command in subcommands.all():
        aliases = f" ({', '.join(command.aliases)})" if command.aliases else ""
        print(f"  {command.name:<12} {command.description}{aliases}")


command = Command(
    name="db",
    handler=run,
    description="Run database and migration commands",
    subcommands=subcommands,
)
