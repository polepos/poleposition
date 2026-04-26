from pole_position.cli.command import Command
from pole_position.cli.services.module_creator import add_module
from pole_position.cli.services.project_name import normalize_package_name, validate_project_name


USAGE = "Usage: polepos add module <module_name>"


def run(args: list[str]) -> None:
    if not args:
        print(USAGE)
        raise SystemExit(1)

    if len(args) > 1:
        print(f"Unexpected argument: {args[1]}")
        print(USAGE)
        raise SystemExit(1)

    raw_name = args[0].strip()

    try:
        validate_project_name(raw_name)
        module_name = normalize_package_name(raw_name)
        add_module(module_name)
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1)
    except ValueError as exc:
        print(str(exc))
        print(USAGE)
        raise SystemExit(1)

    print(f"Added module: {module_name}")


command = Command(
    name="module",
    handler=run,
    description="Add a new module to the current project",
)
