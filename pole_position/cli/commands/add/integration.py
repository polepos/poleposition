from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.commands.output import (
    print_next_steps,
    print_path_section,
)
from pole_position.cli.services.integration_creator import (
    AddedIntegrationResult,
    add_integration,
)
from pole_position.cli.services.project_name import (
    normalize_package_name,
    validate_project_name,
)
from pole_position.cli.usage import print_command_help

HELP_OPTIONS = {"-h", "--help"}


def _print_usage() -> None:
    print_command_help("add", "integration")


def run(args: list[str]) -> None:
    if not args:
        _print_usage()
        raise SystemExit(1)

    if len(args) == 1 and args[0] in HELP_OPTIONS:
        _print_usage()
        return

    if len(args) > 1:
        console.error(f"Unexpected argument: {args[1]}")
        _print_usage()
        raise SystemExit(1)

    if args[0].startswith("--"):
        console.error(f"Unexpected option: {args[0]}")
        _print_usage()
        raise SystemExit(1)

    raw_name = args[0].strip()
    if not raw_name:
        _print_usage()
        raise SystemExit(1)

    try:
        validate_project_name(raw_name)
        integration_name = normalize_package_name(raw_name)
        result = add_integration(integration_name)
    except RuntimeError as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc
    except ValueError as exc:
        console.error(str(exc))
        _print_usage()
        raise SystemExit(1) from exc

    _print_success(result)


def _print_success(result: AddedIntegrationResult) -> None:
    console.success(f"Added integration: {result.integration_name}")

    print_path_section(
        "Created:", result.project_root, result.integration_files
    )
    print_path_section("Updated:", result.project_root, result.updated_files)
    print_next_steps(result.next_steps)


command = Command(
    name="integration",
    handler=run,
    description="Add an external integration to the current project",
)
