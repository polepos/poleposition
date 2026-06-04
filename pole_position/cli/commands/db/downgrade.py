from pole_position.cli.command import Command
from pole_position.cli.services.db_runner import run_alembic_command
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos db downgrade <target>"


def run(args: list[str]) -> None:
    if args and args[0] in {"-h", "--help"}:
        if len(args) > 1:
            print(f"Unexpected argument: {args[1]}")
            print(USAGE)
            raise SystemExit(1)
        print_command_help("db", "downgrade")
        return

    if not args:
        print(USAGE)
        raise SystemExit(1)

    if len(args) > 1:
        print(f"Unexpected argument: {args[1]}")
        print(USAGE)
        raise SystemExit(1)

    try:
        run_alembic_command("downgrade", [args[0]])
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1) from exc


command = Command(
    name="downgrade",
    handler=run,
    description="Revert database migrations",
)
