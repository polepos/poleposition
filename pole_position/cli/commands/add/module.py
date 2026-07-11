from pole_position.cli import console
from pole_position.cli.command import Command
from pole_position.cli.commands.output import (
    print_next_steps,
    print_path_section,
)
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

# Convenience flags that select a module template; each maps to its template
# name. Adding a new shortcut is a single entry here.
SHORTCUT_TEMPLATE_FLAGS = {
    "--api-only": "api-only",
    "--service-only": "service-only",
}


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
    template = "api"
    template_was_set = False
    shortcut_templates: list[str] = []
    crud_feature_names: set[str] = set()
    index = 0

    while index < len(args):
        argument = args[index]

        if argument == "--template":
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                console.error("Missing value for --template.")
                _print_usage()
                raise SystemExit(1)
            template = args[index + 1].strip()
            template_was_set = True
            index += 2
            continue

        if argument.startswith("--template="):
            template = argument.removeprefix("--template=").strip()
            if not template:
                console.error("Missing value for --template.")
                _print_usage()
                raise SystemExit(1)
            template_was_set = True
            index += 1
            continue

        if argument in SHORTCUT_TEMPLATE_FLAGS:
            shortcut_templates.append(SHORTCUT_TEMPLATE_FLAGS[argument])
            index += 1
            continue

        if argument in CRUD_FEATURE_FLAGS:
            crud_feature_names.add(CRUD_FEATURE_FLAGS[argument])
            index += 1
            continue

        if argument.startswith("--"):
            console.error(f"Unexpected option: {argument}")
            _print_usage()
            raise SystemExit(1)

        if raw_name is None:
            raw_name = argument.strip()
            index += 1
            continue

        console.error(f"Unexpected argument: {argument}")
        _print_usage()
        raise SystemExit(1)

    if not raw_name:
        _print_usage()
        raise SystemExit(1)

    chosen_shortcuts = list(dict.fromkeys(shortcut_templates))
    if len(chosen_shortcuts) > 1:
        flags = ", ".join(f"--{name}" for name in chosen_shortcuts)
        console.error(f"Choose only one module template shortcut: {flags}.")
        _print_usage()
        raise SystemExit(1)

    if chosen_shortcuts:
        shortcut = chosen_shortcuts[0]
        if template_was_set and template != shortcut:
            console.error(
                f"--{shortcut} cannot be combined with another module template."
            )
            _print_usage()
            raise SystemExit(1)
        template = shortcut

    if crud_feature_names and template != "crud":
        flags = ", ".join(sorted(CRUD_FEATURE_FLAGS))
        console.error(
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
        console.error(str(exc))
        raise SystemExit(1) from exc
    except ValueError as exc:
        console.error(str(exc))
        _print_usage()
        raise SystemExit(1) from exc

    _print_success(result)


def _print_success(result: AddedModuleResult) -> None:
    console.success(f"Added module: {result.module_name}")
    console.field("Template", result.template)
    if result.features:
        console.field("Features", ", ".join(result.features))

    print_path_section(
        "Created:",
        result.project_root,
        (*result.module_files, *result.test_files),
    )
    print_path_section("Updated:", result.project_root, result.updated_files)
    print_next_steps(result.next_steps)


command = Command(
    name="module",
    handler=run,
    description="Add a new module to the current project",
)
