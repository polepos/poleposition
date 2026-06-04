from pathlib import Path

from pole_position.cli.command import Command
from pole_position.cli.services.module_remover import (
    RemovedModuleResult,
    remove_module,
)
from pole_position.cli.services.project_name import (
    normalize_package_name,
    validate_project_name,
)
from pole_position.cli.usage import print_command_help


def _print_usage() -> None:
    print_command_help("remove", "module")


def run(args: list[str]) -> None:
    if not args:
        _print_usage()
        raise SystemExit(1)

    raw_name: str | None = None
    force = False
    trace = False
    wiring_only = False

    for argument in args:
        if argument in {"-h", "--help"}:
            _print_usage()
            return

        if argument == "--force":
            force = True
            continue

        if argument == "--trace":
            trace = True
            continue

        if argument == "--wiring-only":
            wiring_only = True
            continue

        if argument.startswith("--"):
            print(f"Unexpected option: {argument}")
            _print_usage()
            raise SystemExit(1)

        if raw_name is None:
            raw_name = argument.strip()
            continue

        print(f"Unexpected argument: {argument}")
        _print_usage()
        raise SystemExit(1)

    if not raw_name:
        _print_usage()
        raise SystemExit(1)

    try:
        validate_project_name(raw_name)
        module_name = normalize_package_name(raw_name)
        result = remove_module(
            module_name,
            force=force,
            trace=trace,
            wiring_only=wiring_only,
        )
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(str(exc))
        _print_usage()
        raise SystemExit(1) from exc

    _print_success(result)


def _print_success(result: RemovedModuleResult) -> None:
    if result.trace:
        _print_trace(result)
        return

    if result.wiring_only:
        print(f"Cleaned module wiring: {result.module_name}")
    else:
        print(f"Removed module: {result.module_name}")
    print(f"Template: {result.template}")

    if result.removed_paths:
        print("Removed:")
        for path in result.removed_paths:
            print(f"  {_relative_path(result, path)}")

    if result.updated_files:
        print("Updated:")
        for path in result.updated_files:
            print(f"  {_relative_path(result, path)}")

    print("Next steps:")
    for step in result.next_steps:
        print(f"  {step}")


def _relative_path(result: RemovedModuleResult, path: Path) -> str:
    return path.relative_to(result.project_root).as_posix()


def _print_trace(result: RemovedModuleResult) -> None:
    if result.wiring_only:
        print(f"Wiring-only removal trace: {result.module_name}")
    else:
        print(f"Removal trace: {result.module_name}")
    print(f"Template: {result.template}")

    if result.blocked_by_custom_changes:
        print(
            "Blocked unless --force is used because custom changes were "
            "detected:"
        )
    elif result.custom_changes:
        print("Custom changes that would be removed because --force is set:")

    for change in result.custom_changes:
        print(f"  {change}")

    if result.removed_paths:
        print("Would remove:")
        for path in result.removed_paths:
            print(f"  {_relative_path(result, path)}")

    if result.updated_files:
        print("Would update:")
        for path in result.updated_files:
            print(f"  {_relative_path(result, path)}")

    print("Trace only: no files changed.")


command = Command(
    name="module",
    handler=run,
    description="Remove a generated module from the current project",
)
