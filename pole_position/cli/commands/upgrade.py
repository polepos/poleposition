from pole_position import __version__
from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.services.project_checker import check_project
from pole_position.cli.services.project_manifest import read_project_manifest
from pole_position.cli.usage import print_command_help

USAGE = "Usage: polepos upgrade"
HELP_OPTIONS = {"-h", "--help"}


def run(args: list[str]) -> None:
    if args and args[0] in HELP_OPTIONS:
        if len(args) > 1:
            console.error(f"Unexpected argument: {args[1]}")
            print(USAGE)
            raise SystemExit(1)
        print_command_help("upgrade")
        return

    if args:
        console.error(f"Unexpected argument: {args[0]}")
        print(USAGE)
        raise SystemExit(1)

    try:
        result = check_project()
    except RuntimeError as exc:
        console.error(str(exc))
        raise SystemExit(1) from exc

    manifest = read_project_manifest(result.project_root)
    modules = manifest.module_templates
    integrations = {
        name: enabled
        for name, enabled in manifest.enabled_integrations.items()
        if enabled
    }

    console.heading("PolePosition upgrade report")
    console.field("CLI version", __version__)
    console.field("Project root", str(result.project_root))
    console.field("Package", result.package_name)
    console.field("Database mode", manifest.database or "managed")
    console.field("Project check", "passed" if result.passed else "failed")

    console.heading("Modules:")
    if modules:
        for module_name in sorted(modules):
            console.item(f"{module_name}: {modules[module_name]}")
    else:
        console.item("none recorded")

    console.heading("Integrations:")
    if integrations:
        for integration_name in sorted(integrations):
            console.item(integration_name)
    else:
        console.item("none recorded")

    if not result.passed:
        console.heading("Issues:")
        for issue in result.issues:
            console.info(f"  - [{issue.code}] {issue.message}")

    console.heading("Next steps:")
    console.step("Run `polepos check --fix` to restore safe managed markers.")
    console.step(
        "Run `polepos check` and project tests after upgrading the CLI."
    )


command = Command(
    name="upgrade",
    handler=run,
    description="Report project upgrade readiness",
)
