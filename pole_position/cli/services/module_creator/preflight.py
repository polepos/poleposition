import ast
from pathlib import Path

from pole_position.cli.services.module_creator.constants import (
    ENV_LLM_MARKER,
    MODEL_IMPORTS_MARKER,
    MODULE_EXPORTS_MARKER,
    ROUTER_IMPORTS_MARKER,
    ROUTER_INCLUDES_MARKER,
    SETTINGS_LLM_MARKER,
)
from pole_position.cli.services.module_creator.entries import (
    _existing_entry_keys,
    _expected_block_keys,
)
from pole_position.cli.services.module_creator.references import (
    _has_router_reference,
    _line_exists,
)
from pole_position.cli.services.module_templates import (
    ModuleTemplate,
    llm_env_block,
    llm_settings_block,
)
from pole_position.cli.services.project_manifest import (
    read_project_manifest,
)


def _validate_add_module_preflight(
    *,
    project_root: Path,
    package_root: Path,
    modules_root: Path,
    module_root: Path,
    module_name: str,
    template_spec: ModuleTemplate,
) -> None:
    problems: list[str] = []
    tests_root = project_root / "tests"

    _collect_manifest_read_error(problems, project_root)

    if module_root.exists():
        problems.append(f"Module already exists: {module_name}")

    _collect_existing_generated_file(
        problems,
        tests_root / "integration" / template_spec.integration_test_name,
    )
    _collect_existing_generated_file(
        problems,
        tests_root / "unit" / template_spec.unit_test_name,
    )

    modules_init_path = modules_root / "__init__.py"
    router_path = package_root / "api" / "router.py"
    _collect_missing_marker(
        problems,
        modules_init_path,
        MODULE_EXPORTS_MARKER,
    )
    _collect_python_parse_error(problems, modules_init_path)
    if template_spec.update_api_router:
        _collect_missing_marker(
            problems,
            router_path,
            ROUTER_IMPORTS_MARKER,
        )
        _collect_missing_marker(
            problems,
            router_path,
            ROUTER_INCLUDES_MARKER,
        )
        _collect_python_parse_error(problems, router_path)
    _collect_existing_managed_module_references(
        problems=problems,
        package_root=package_root,
        module_name=module_name,
        template_spec=template_spec,
    )

    if template_spec.update_db_models:
        db_models_path = package_root / "db" / "models.py"
        if not db_models_path.is_file() and not (package_root / "db").exists():
            problems.append(
                "Database-backed module templates require generated db/ "
                "wiring. "
                "Use `polepos add module <name> --api-only` in a "
                "database-free project."
            )
        else:
            _collect_missing_marker(
                problems,
                db_models_path,
                MODEL_IMPORTS_MARKER,
            )
            _collect_python_parse_error(problems, db_models_path)

    if template_spec.ensure_llm_settings:
        settings_path = package_root / "settings.py"
        _collect_missing_marker_unless_entries_exist(
            problems,
            settings_path,
            marker=SETTINGS_LLM_MARKER,
            block=llm_settings_block(),
            entry_type="setting",
        )
        _collect_python_parse_error(problems, settings_path)
        _collect_missing_marker_unless_entries_exist(
            problems,
            project_root / ".env.example",
            marker=ENV_LLM_MARKER,
            block=llm_env_block(),
            entry_type="env",
        )

    if problems:
        formatted_problems = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(
            "Cannot add module because the project layout is not ready:\n"
            f"{formatted_problems}"
        )


def _collect_existing_generated_file(problems: list[str], path: Path) -> None:
    if path.exists():
        problems.append(f"Generated file already exists: {path}")


def _collect_manifest_read_error(
    problems: list[str], project_root: Path
) -> None:
    manifest = read_project_manifest(project_root)
    if manifest.read_error is not None:
        problems.append(manifest.read_error)


def _collect_missing_marker(
    problems: list[str], path: Path, marker: str
) -> None:
    lines = _read_managed_file_lines(problems, path)
    if lines is None:
        return

    if marker not in lines:
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _collect_python_parse_error(problems: list[str], path: Path) -> None:
    if not path.is_file():
        return

    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed Python file for module add: {path}: "
            f"{exc.reason}"
        )
    except SyntaxError as exc:
        problems.append(
            f"Could not parse managed Python file for module add: {path}: {exc}"
        )


def _collect_existing_managed_module_references(
    *,
    problems: list[str],
    package_root: Path,
    module_name: str,
    template_spec: ModuleTemplate,
) -> None:
    package_name = package_root.name
    modules_init_path = package_root / "modules" / "__init__.py"
    router_path = package_root / "api" / "router.py"
    models_path = package_root / "db" / "models.py"

    stale_references: list[str] = []
    if _line_exists(modules_init_path, f'    "{module_name}",'):
        stale_references.append(f"module export in {modules_init_path}")

    if _has_router_reference(router_path, package_name, module_name):
        stale_references.append(f"router wiring in {router_path}")

    if template_spec.update_db_models and _line_exists(
        models_path,
        f"    from {package_name}.modules.{module_name} import model  # "
        f"noqa: F401",
    ):
        stale_references.append(f"model import in {models_path}")

    if stale_references:
        formatted = ", ".join(stale_references)
        problems.append(
            f"Managed references already exist for module '{module_name}': "
            f"{formatted}. Run `polepos remove module {module_name}` before "
            "adding it again."
        )


def _collect_missing_marker_unless_entries_exist(
    problems: list[str],
    path: Path,
    *,
    marker: str,
    block: list[str],
    entry_type: str,
) -> None:
    content = _read_managed_file_text(problems, path)
    if content is None:
        return

    expected_keys = _expected_block_keys(block, entry_type=entry_type)
    existing_keys = _existing_entry_keys(
        content.splitlines(),
        entry_type=entry_type,
    )
    if all(key in existing_keys for key in expected_keys):
        return

    if marker not in content.splitlines():
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _read_managed_file_text(problems: list[str], path: Path) -> str | None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        )
        return None


def _read_managed_file_lines(
    problems: list[str], path: Path
) -> list[str] | None:
    content = _read_managed_file_text(problems, path)
    if content is None:
        return None

    return content.splitlines()
