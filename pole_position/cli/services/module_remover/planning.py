from pathlib import Path

from pole_position.cli.services.module_remover.generated_tests import (
    _generated_test_paths,
)
from pole_position.cli.services.module_remover.io import (
    _line_exists,
    _model_import_line,
    _module_export_line,
)
from pole_position.cli.services.module_remover.llm import (
    _planned_llm_integration_paths,
    _planned_llm_settings_updates,
)
from pole_position.cli.services.module_remover.router import (
    _router_wiring_ranges,
)
from pole_position.cli.services.module_templates import (
    ModuleTemplateContract,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    read_project_manifest,
)


def _planned_removed_paths(
    *,
    project_root: Path,
    package_root: Path,
    module_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
    remove_llm_shared: bool,
    include_module_directory: bool = True,
) -> list[Path]:
    removed_paths = [
        path
        for path in _generated_test_paths(
            project_root, module_name, template_contract
        )
        if path.exists()
    ]

    if module_root.exists() and include_module_directory:
        removed_paths.append(module_root)

    if remove_llm_shared:
        removed_paths.extend(
            _planned_llm_integration_paths(package_root, package_root.name)
        )

    return removed_paths


def _planned_updated_files(
    *,
    project_root: Path,
    package_root: Path,
    package_name: str,
    module_name: str,
    template_contract: ModuleTemplateContract,
    remove_llm_shared: bool,
) -> list[Path]:
    updated_files: list[Path] = []
    modules_init_path = package_root / "modules" / "__init__.py"
    router_path = package_root / "api" / "router.py"

    if _line_exists(modules_init_path, _module_export_line(module_name)):
        updated_files.append(modules_init_path)

    if _router_wiring_ranges(router_path, package_name, module_name):
        updated_files.append(router_path)

    if template_contract.update_db_models:
        models_path = package_root / "db" / "models.py"
        if _line_exists(
            models_path, _model_import_line(package_name, module_name)
        ):
            updated_files.append(models_path)

    if remove_llm_shared:
        updated_files.extend(
            _planned_llm_settings_updates(project_root, package_root)
        )

    if _manifest_would_change(
        project_root=project_root,
        module_name=module_name,
        remove_llm_shared=remove_llm_shared,
    ):
        updated_files.append(manifest_path(project_root))

    return updated_files


def _remove_next_steps(
    *,
    include_migration_note: bool,
    wiring_only: bool = False,
    module_directory_preserved: bool = False,
) -> tuple[str, ...]:
    steps: list[str] = []
    if wiring_only and module_directory_preserved:
        steps.append(
            "Move, delete, or rewire the preserved module directory before "
            "expecting `polepos check` to pass"
        )
    steps.append("Run `polepos check`")
    if include_migration_note:
        steps.append(
            "Create a migration if removing the module also removes "
            "database tables"
        )
    return tuple(steps)


def _manifest_would_change(
    *,
    project_root: Path,
    module_name: str,
    remove_llm_shared: bool,
) -> bool:
    manifest = read_project_manifest(project_root)
    if not manifest.exists:
        return False

    if module_name in manifest.module_templates:
        return True

    return remove_llm_shared and (
        "llm" in manifest.enabled_integrations
        or "llm" in manifest.invalid_integration_values
    )
