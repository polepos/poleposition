import sys

from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.commands import register_commands
from pole_position.cli.registry import CommandRegistry, registry
from pole_position.cli.usage import print_command_help

HELP_OPTIONS = {"-h", "--help"}


def main() -> None:
    register_commands()

    args = sys.argv[1:]

    if not args:
        print("Run `polepos help` for usage.")
        raise SystemExit(1)

    dispatch_command(registry, args)


def dispatch_command(
    command_registry: CommandRegistry, args: list[str]
) -> None:
    command_name = args[0]
    command = command_registry.get(command_name)

    if command is None:
        console.error(f"Unknown command: {command_name}")
        print("Run `polepos help` for available commands.")
        raise SystemExit(1)

    command_args = args[1:]

    if (
        command.subcommands is not None
        and command_args
        and command_args[0] in HELP_OPTIONS
    ):
        print_command_usage(command)
        return

    if command.subcommands is not None and command_args:
        dispatch_command(command.subcommands, command_args)
        return

    if command.subcommands is not None and command.handler is None:
        print_command_usage(command)
        raise SystemExit(1)

    if command.handler is None:
        console.error(f"Command '{command.name}' is not executable.")
        raise SystemExit(1)

    command.handler(command_args)


def print_command_usage(command: Command) -> None:
    if print_command_help(command.name):
        return

    print(f"Usage: polepos {command.name} <subcommand>\n")
    console.heading("Subcommands:")

    if command.subcommands is None:
        return

    for subcommand in command.subcommands.all():
        aliases = (
            f" ({', '.join(subcommand.aliases)})" if subcommand.aliases else ""
        )
        print(f"  {subcommand.name:<12} {subcommand.description}{aliases}")


if __name__ == "__main__":
    main()
