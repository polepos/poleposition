from pathlib import Path

from pole_position.cli.command import Command
from pole_position.cli.services.installer import install_project_dependencies
from pole_position.cli.services.project_creator import create_project
from pole_position.cli.services.project_name import (
    normalize_package_name,
    validate_project_name,
)


USAGE = "Usage: polepos start <project_name> [--install] [--no-bytecode]"
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    install = False
    no_bytecode = False
    installer: str | None = None
    filtered_args: list[str] = []

    for arg in args:
        if arg in HELP_OPTIONS:
            print(USAGE)
            return
        if arg == "--install":
            install = True
        elif arg == "--no-bytecode":
            no_bytecode = True
        elif arg.startswith("-"):
            print(f"Unexpected option: {arg}")
            print(USAGE)
            raise SystemExit(1)
        else:
            filtered_args.append(arg)

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
        raise SystemExit(1)

    package_name = normalize_package_name(project_name)
    project_path = Path(project_name)

    if project_path.exists():
        print(f"Directory already exists: {project_name}")
        raise SystemExit(1)

    create_project(
        project_name=project_name,
        package_name=package_name,
        project_path=project_path,
        no_bytecode=no_bytecode,
    )
    print(f"Created project: {project_name}")

    command_prefix = "PYTHONDONTWRITEBYTECODE=1 " if no_bytecode else ""

    if no_bytecode:
        print("Configured generated local Python commands to start without bytecode writes.")

    if install:
        try:
            print("Installing project dependencies...")
            installer = install_project_dependencies(project_path=project_path)
            print(f"Dependencies installed successfully with {installer}.")
        except RuntimeError as exc:
            print(str(exc))
            raise SystemExit(1)

    print("")
    print("Next steps:")
    print(f"  cd {project_name}")
    print("  cp .env.example .env")

    if installer == "pip":
        print("  source .venv/bin/activate")
        print(f"  {command_prefix}python -m alembic upgrade head")
        print(f"  {command_prefix}python -m {package_name}.run")
        return

    if not install:
        print("  uv sync")

    print(f"  {command_prefix}uv run alembic upgrade head")
    print(f"  {command_prefix}uv run python -m {package_name}.run")


command = Command(
    name="start",
    aliases=("startproject",),
    handler=run,
    description="Start a new FastAPI project lifecycle",
)
