from pathlib import Path

from pole_position.cli.command import Command
from pole_position.cli.services.installer import install_project_dependencies
from pole_position.cli.services.project_creator import create_project
from pole_position.cli.services.project_name import (
    normalize_package_name,
    validate_project_name,
)


USAGE = "Usage: polepos start <project_name> [--install]"


def run(args: list[str]) -> None:
    install = False
    filtered_args: list[str] = []

    for arg in args:
        if arg == "--install":
            install = True
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
    )
    print(f"Created project: {project_name}")

    if install:
        try:
            print("Installing project dependencies with uv...")
            install_project_dependencies(project_path=project_path)
            print("Dependencies installed successfully.")
        except RuntimeError as exc:
            print(str(exc))
            raise SystemExit(1)

    print("")
    print("Next steps:")
    print(f"  cd {project_name}")
    print("  cp .env.example .env")

    if not install:
        print("  uv sync")

    print(f"  uv run fastapi dev src/{package_name}/main.py")


command = Command(
    name="start",
    aliases=("startproject",),
    handler=run,
    description="Create a new FastAPI project",
)