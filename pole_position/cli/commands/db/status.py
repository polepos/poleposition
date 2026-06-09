from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.services.db_runner import run_alembic_command
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos db status"


def run(args: list[str]) -> None:
    if args and args[0] in {"-h", "--help"}:
        if len(args) > 1:
            console.error(f"Unexpected argument: {args[1]}")
            print(USAGE)
            raise SystemExit(1)
        print_command_help("db", "status")
        return

    if args:
        console.error(f"Unexpected argument: {args[0]}")
        print(USAGE)
        raise SystemExit(1)

    try:
        console.heading("Alembic current revision:")
        run_alembic_command("current", [])
        console.heading("Alembic heads:")
        run_alembic_command("heads", [])
    except RuntimeError as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc


command = Command(
    name="status",
    handler=run,
    description="Show current and target migration revisions",
)
