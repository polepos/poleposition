from pathlib import Path

from pole_position.cli.command import Command
from pole_position.cli.services.module_creator import (
    AddedModuleResult,
    add_module,
)
from pole_position.cli.services.module_templates import (
    CRUD_FEATURE_FLAGS,
    CrudFeatureSet,
)
from pole_position.cli.services.project_name import (
    normalize_package_name,
    validate_project_name,
)
from pole_position.cli.usage import print_command_help

HELP_OPTIONS = {"-h", "--help"}


def _print_usage() -> None:
    print_command_help("add", "module")


def run(args: list[str]) -> None:
    if not args:
        _print_usage()
        raise SystemExit(1)

    if len(args) == 1 and args[0] in HELP_OPTIONS:
        _print_usage()
        return

    raw_name: str | None = None
    template = "standard"
    template_was_set = False
    api_only = False
    crud_feature_names: set[str] = set()
    index = 0

    while index < len(args):
        argument = args[index]

        if argument == "--template":
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                print("Missing value for --template.")
                _print_usage()
                raise SystemExit(1)
            template = args[index + 1].strip()
            template_was_set = True
            index += 2
            continue

        if argument.startswith("--template="):
            template = argument.split("=", 1)[1].strip()
            if not template:
                print("Missing value for --template.")
                _print_usage()
                raise SystemExit(1)
            template_was_set = True
            index += 1
            continue

        if argument == "--api-only":
            api_only = True
            index += 1
            continue

        if argument in CRUD_FEATURE_FLAGS:
            crud_feature_names.add(CRUD_FEATURE_FLAGS[argument])
            index += 1
            continue

        if argument.startswith("--"):
            print(f"Unexpected option: {argument}")
            _print_usage()
            raise SystemExit(1)

        if raw_name is None:
            raw_name = argument.strip()
            index += 1
            continue

        print(f"Unexpected argument: {argument}")
        _print_usage()
        raise SystemExit(1)

    if not raw_name:
        _print_usage()
        raise SystemExit(1)

    if api_only:
        if template_was_set and template != "api-only":
            print("--api-only cannot be combined with another module template.")
            _print_usage()
            raise SystemExit(1)
        template = "api-only"

    if crud_feature_names and template != "crud":
        flags = ", ".join(sorted(CRUD_FEATURE_FLAGS))
        print(
            "CRUD feature options require `--template crud`. "
            f"Available options: {flags}."
        )
        _print_usage()
        raise SystemExit(1)

    try:
        validate_project_name(raw_name)
        module_name = normalize_package_name(raw_name)
        result = add_module(
            module_name,
            template=template,
            crud_features=CrudFeatureSet.from_names(crud_feature_names),
        )
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(str(exc))
        _print_usage()
        raise SystemExit(1) from exc

    _print_success(result)


def _print_success(result: AddedModuleResult) -> None:
    print(f"Added module: {result.module_name}")
    print(f"Template: {result.template}")
    if result.features:
        print(f"Features: {', '.join(result.features)}")

    print("Created:")
    for path in (*result.module_files, *result.test_files):
        print(f"  {_relative_path(result, path)}")

    print("Updated:")
    for path in result.updated_files:
        print(f"  {_relative_path(result, path)}")

    print("Next steps:")
    for step in result.next_steps:
        print(f"  {step}")


def _relative_path(result: AddedModuleResult, path: Path) -> str:
    return path.relative_to(result.project_root).as_posix()


command = Command(
    name="module",
    handler=run,
    description="Add a new module to the current project",
)
