import sys

from pole_position.cli.commands.startproject import run as run_startproject
from pole_position.cli.commands.version import run as run_version


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print("Usage: polepos <command> [options]")
        print("")
        print("Commands:")
        print("  start <project_name> [--install]")
        print("  version")
        raise SystemExit(1)

    command = args[0]
    command_args = args[1:]

    if command in {"start", "startproject"}:
        run_startproject(command_args)
        return

    if command == "version":
        run_version(command_args)
        return

    print(f"Unknown command: {command}")
    print("Usage: poleposition <command> [options]")
    raise SystemExit(1)

if __name__ == "__main__":
    main()