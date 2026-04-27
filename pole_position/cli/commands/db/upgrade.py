from pole_position.cli.command import Command
from pole_position.cli.services.db_runner import run_alembic_command


USAGE = "Usage: polepos db upgrade [target]"


def run(args: list[str]) -> None:
    if len(args) > 1:
        print(f"Unexpected argument: {args[1]}")
        print(USAGE)
        raise SystemExit(1)

    target = args[0] if args else "head"

    try:
        run_alembic_command("upgrade", [target])
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1)


command = Command(
    name="upgrade",
    handler=run,
    description="Apply database migrations",
)
