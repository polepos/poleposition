import json

from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.services.project_checker import (
    ProjectCheckResult,
    check_project,
)
from pole_position.cli.services.project_fixer import (
    ProjectFixResult,
    fix_project,
)
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos check [--json] [--fix]"
HELP_OPTIONS = {"-h", "--help"}
JSON_OPTIONS = {"--json"}
FIX_OPTIONS = {"--fix"}


def run(args: list[str]) -> None:
    if len(args) == 1 and args[0] in HELP_OPTIONS:
        print_command_help("check")
        return

    json_output = False
    fix = False
    for arg in args:
        if arg in JSON_OPTIONS:
            json_output = True
            continue
        if arg in FIX_OPTIONS:
            fix = True
            continue
        console.error(f"Unexpected argument: {arg}")
        print(USAGE)
        raise SystemExit(1)

    fix_result: ProjectFixResult | None = None
    try:
        if fix:
            fix_result = fix_project()
        result = check_project()
    except RuntimeError as exc:
        if json_output:
            _print_json_error(str(exc))
            raise SystemExit(1) from exc
        console.error(str(exc))
        raise SystemExit(1) from exc

    if json_output:
        _print_json_result(result, fix_result=fix_result)
        if not result.passed:
            raise SystemExit(1)
        return

    if fix_result is not None:
        _print_fix_result(fix_result)

    if not result.passed:
        console.error("PolePosition project check failed.")
        console.field("Project root", str(result.project_root))
        console.field("Package", result.package_name)
        console.heading("Issues:")
        for issue in result.issues:
            console.info(f"  - [{issue.code}] {issue.message}")
            console.info(f"    Fix: {issue.remediation}")
        raise SystemExit(1)

    console.success("PolePosition project check passed.")
    console.field("Project root", str(result.project_root))
    console.field("Package", result.package_name)


def _print_fix_result(result: ProjectFixResult) -> None:
    if not result.fixed_files:
        console.info("No automatic fixes were applied.")
        return

    console.heading("Applied fixes:")
    for path in result.fixed_files:
        console.item(_relative_path(result, path))


def _print_json_result(
    result: ProjectCheckResult,
    *,
    fix_result: ProjectFixResult | None = None,
) -> None:
    payload = {
        "passed": result.passed,
        "project_root": str(result.project_root),
        "package_name": result.package_name,
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "remediation": issue.remediation,
            }
            for issue in result.issues
        ],
    }
    if fix_result is not None:
        payload["fixed"] = [
            _relative_path(fix_result, path) for path in fix_result.fixed_files
        ]
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_json_error(message: str) -> None:
    payload = {
        "passed": False,
        "project_root": None,
        "package_name": None,
        "issues": [
            {
                "code": "PPCHK000",
                "message": message,
                "remediation": (
                    "Run the command from a PolePosition project root or a "
                    "nested directory inside one."
                ),
            }
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _relative_path(result: ProjectFixResult, path) -> str:
    return path.relative_to(result.project_root).as_posix()


command = Command(
    name="check",
    handler=run,
    description="Validate the current PolePosition project",
)
