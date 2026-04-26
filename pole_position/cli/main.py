import sys

from pole_position.cli.commands import register_commands
from pole_position.cli.registry import registry


def main() -> None:
    register_commands()

    args = sys.argv[1:]

    if not args:
        print("Run `polepos help` for usage.")
        raise SystemExit(1)

    command_name = args[0]
    command_args = args[1:]

    command = registry.get(command_name)

    if command is None:
        print(f"Unknown command: {command_name}")
        print("Run `polepos help` for available commands.")
        raise SystemExit(1)

    command.handler(command_args)


if __name__ == "__main__":
    main()