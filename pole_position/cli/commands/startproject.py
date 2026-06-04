from pathlib import Path

from pole_position.cli.command import Command
from pole_position.cli.services.database_options import (
    DEFAULT_DATABASE,
    SUPPORTED_DATABASES,
    get_database_option,
)
from pole_position.cli.services.installer import install_project_dependencies
from pole_position.cli.services.project_creator import create_project
from pole_position.cli.services.project_name import (
    normalize_package_name,
    validate_project_name,
)
from pole_position.cli.usage import print_command_help

DATABASE_CHOICES = "|".join(SUPPORTED_DATABASES)
USAGE = (
    "Usage: polepos start <project_name> "
    f"[--install] [--no-bytecode] [--db {DATABASE_CHOICES}]"
)
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    install = False
    no_bytecode = False
    database = DEFAULT_DATABASE
    installer: str | None = None
    filtered_args: list[str] = []
    index = 0

    while index < len(args):
        arg = args[index]
        if arg in HELP_OPTIONS:
            print_command_help("start")
            return
        if arg == "--install":
            install = True
        elif arg == "--no-bytecode":
            no_bytecode = True
        elif arg == "--db":
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                print("Missing value for --db")
                print(USAGE)
                raise SystemExit(1)
            database = args[index + 1]
            index += 1
        elif arg.startswith("--db="):
            database = arg.split("=", 1)[1]
        elif arg.startswith("-"):
            print(f"Unexpected option: {arg}")
            print(USAGE)
            raise SystemExit(1)
        else:
            filtered_args.append(arg)
        index += 1

    if not filtered_args:
        print(USAGE)
        raise SystemExit(1)

    if len(filtered_args) > 1:
        print(f"Unexpected argument: {filtered_args[1]}")
        print(USAGE)
        raise SystemExit(1)

    project_name = filtered_args[0].strip()

    try:
        validate_project_name(project_name)
    except ValueError as exc:
        print(str(exc))
        print(USAGE)
        raise SystemExit(1) from exc

    package_name = normalize_package_name(project_name)
    try:
        database_option = get_database_option(
            database, package_name=package_name
        )
    except ValueError as exc:
        print(str(exc))
        print(USAGE)
        raise SystemExit(1) from exc
    project_path = Path(project_name)

    if project_path.exists():
        print(f"Directory already exists: {project_name}")
        raise SystemExit(1)

    create_project(
        project_name=project_name,
        package_name=package_name,
        project_path=project_path,
        database=database_option.name,
        no_bytecode=no_bytecode,
    )
    print(f"Created project: {project_name}")
    print(f"Database: {database_option.name}")

    command_prefix = "PYTHONDONTWRITEBYTECODE=1 " if no_bytecode else ""

    if no_bytecode:
        print(
            "Configured generated local Python commands to start without "
            "bytecode writes."
        )

    if install:
        try:
            print("Installing project dependencies...")
            installer = install_project_dependencies(project_path=project_path)
            print(f"Dependencies installed successfully with {installer}.")
        except RuntimeError as exc:
            print(str(exc))
            raise SystemExit(1) from exc

    print("")
    print("Next steps:")
    print(f"  cd {project_name}")
    print("  cp .env.example .env")

    if installer == "pip":
        print("  source .venv/bin/activate")
        if database_option.uses_database:
            print(f"  {command_prefix}polepos db upgrade")
        print(f"  {command_prefix}python -m {package_name}.run")
        return

    if not install:
        print("  uv sync --extra dev")

    if database_option.uses_database:
        print(f"  {command_prefix}polepos db upgrade")
    print(f"  {command_prefix}uv run python -m {package_name}.run")


command = Command(
    name="start",
    aliases=("startproject",),
    handler=run,
    description="Start a new FastAPI project lifecycle",
)
