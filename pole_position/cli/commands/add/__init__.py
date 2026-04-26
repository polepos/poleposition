from pole_position.cli.command import Command
from pole_position.cli.commands.add.module import command as module_cmd
from pole_position.cli.registry import CommandRegistry


subcommands = CommandRegistry()
subcommands.register(module_cmd)


def run(args: list[str]) -> None:
    print("Usage: polepos add <subcommand>\n")
    print("Subcommands:")

    for command in subcommands.all():
        aliases = f" ({', '.join(command.aliases)})" if command.aliases else ""
        print(f"  {command.name:<12} {command.description}{aliases}")


command = Command(
    name="add",
    handler=run,
    description="Add new code generation resources",
    subcommands=subcommands,
)
