from pole_position import __version__
from pole_position.cli.command import Command
from pole_position.cli.services.project_checker import check_project
from pole_position.cli.services.project_manifest import read_project_manifest
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos upgrade"
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    if args and args[0] in HELP_OPTIONS:
        if len(args) > 1:
            print(f"Unexpected argument: {args[1]}")
            print(USAGE)
            raise SystemExit(1)
        print_command_help("upgrade")
        return

    if args:
        print(f"Unexpected argument: {args[0]}")
        print(USAGE)
        raise SystemExit(1)

    try:
        result = check_project()
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    manifest = read_project_manifest(result.project_root)
    modules = manifest.module_templates
    integrations = {
        name: enabled
        for name, enabled in manifest.enabled_integrations.items()
        if enabled
    }

    print("PolePosition upgrade report")
    print(f"CLI version: {__version__}")
    print(f"Project root: {result.project_root}")
    print(f"Package: {result.package_name}")
    print(f"Database mode: {manifest.database or 'managed'}")
    print(f"Project check: {'passed' if result.passed else 'failed'}")

    print("Modules:")
    if modules:
        for module_name in sorted(modules):
            print(f"  {module_name}: {modules[module_name]}")
    else:
        print("  none recorded")

    print("Integrations:")
    if integrations:
        for integration_name in sorted(integrations):
            print(f"  {integration_name}")
    else:
        print("  none recorded")

    if not result.passed:
        print("Issues:")
        for issue in result.issues:
            print(f"  - [{issue.code}] {issue.message}")

    print("Next steps:")
    print("  Run `polepos check --fix` to restore safe managed markers.")
    print("  Run `polepos check` and project tests after upgrading the CLI.")


command = Command(
    name="upgrade",
    handler=run,
    description="Report project upgrade readiness",
)
