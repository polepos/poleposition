import shutil
from pathlib import Path

from pole_position.cli.services.module_remover.generated_tests import (
    _remove_generated_tests,
)
from pole_position.cli.services.module_remover.io import (
    _model_import_line,
    _module_export_line,
    _remove_line,
)
from pole_position.cli.services.module_remover.llm import (
    _has_remaining_ai_prompt_module,
    _is_generated_llm_scaffold_pristine,
    _remove_llm_integration_files,
    _remove_llm_settings,
)
from pole_position.cli.services.module_remover.planning import (
    _manifest_would_change,
    _planned_removed_paths,
    _planned_updated_files,
    _remove_next_steps,
)
from pole_position.cli.services.module_remover.preflight import (
    _validate_remove_module_preflight,
)
from pole_position.cli.services.module_remover.pristine import (
    _custom_changes_message,
    _detect_custom_changes,
    _detect_custom_test_changes,
)
from pole_position.cli.services.module_remover.references import (
    _remove_module_reference_lines,
    _remove_module_test_files,
)
from pole_position.cli.services.module_remover.result import (
    RemovedModuleResult,
)
from pole_position.cli.services.module_remover.router import (
    _remove_router_wiring,
)
from pole_position.cli.services.module_remover.templates import (
    _detect_module_template,
)
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    remove_manifest_integration,
    remove_manifest_module,
)

__all__ = [
    "remove_module",
    "RemovedModuleResult",
]


def remove_module(
    module_name: str,
    cwd: Path | None = None,
    *,
    force: bool = False,
    trace: bool = False,
    wiring_only: bool = False,
) -> RemovedModuleResult:
    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    modules_root = package_root / "modules"
    module_root = modules_root / module_name

    detected_template = _detect_module_template(
        project_root, module_root, module_name
    )
    template_contract = detected_template.contract
    _validate_remove_module_preflight(
        project_root=project_root,
        package_root=package_root,
        module_root=module_root,
        module_name=module_name,
        template_contract=template_contract,
    )

    custom_changes = (
        _detect_custom_test_changes(
            project_root=project_root,
            package_root=package_root,
            module_name=module_name,
            template_contract=template_contract,
            crud_features=detected_template.crud_features,
        )
        if wiring_only
        else _detect_custom_changes(
            project_root=project_root,
            package_root=package_root,
            module_root=module_root,
            module_name=module_name,
            template_contract=template_contract,
            crud_features=detected_template.crud_features,
        )
    )
    remove_llm_shared = (
        not wiring_only
        and template_contract.ensure_llm_settings
        and not _has_remaining_ai_prompt_module(
            project_root=project_root,
            modules_root=modules_root,
            removed_module_name=module_name,
        )
        and _is_generated_llm_scaffold_pristine(
            project_root, package_root, package_name
        )
    )
    include_migration_next_step = (
        template_contract.update_db_models and (package_root / "db").exists()
    )

    if custom_changes and not force and not trace:
        raise RuntimeError(
            _custom_changes_message(
                module_name,
                custom_changes,
                wiring_only=wiring_only,
            )
        )

    if trace:
        return RemovedModuleResult(
            module_name=module_name,
            template=template_contract.name,
            project_root=project_root,
            package_root=package_root,
            removed_paths=tuple(
                dict.fromkeys(
                    _planned_removed_paths(
                        project_root=project_root,
                        package_root=package_root,
                        module_root=module_root,
                        module_name=module_name,
                        template_contract=template_contract,
                        remove_llm_shared=remove_llm_shared,
                        include_module_directory=not wiring_only,
                    )
                )
            ),
            updated_files=tuple(
                dict.fromkeys(
                    _planned_updated_files(
                        project_root=project_root,
                        package_root=package_root,
                        package_name=package_name,
                        module_name=module_name,
                        template_contract=template_contract,
                        remove_llm_shared=remove_llm_shared,
                    )
                )
            ),
            next_steps=_remove_next_steps(
                include_migration_note=include_migration_next_step,
                wiring_only=wiring_only,
                module_directory_preserved=wiring_only and module_root.exists(),
            ),
            trace=True,
            force=force,
            wiring_only=wiring_only,
            custom_changes=tuple(custom_changes),
            blocked_by_custom_changes=bool(custom_changes and not force),
        )

    updated_files: list[Path] = []
    removed_paths: list[Path] = []
    manifest_would_change = _manifest_would_change(
        project_root=project_root,
        module_name=module_name,
        remove_llm_shared=remove_llm_shared,
    )

    modules_init_path = modules_root / "__init__.py"
    if _remove_line(modules_init_path, _module_export_line(module_name)):
        updated_files.append(modules_init_path)

    router_path = package_root / "api" / "router.py"
    models_path = package_root / "db" / "models.py"
    module_missing = not module_root.exists()

    if module_missing:
        # Orphan cleanup: scrub every reference `polepos check` would flag,
        # regardless of the (possibly mis-detected) template or hand-edited
        # shape, so the recommended `remove module` command never dead-ends.
        if _remove_module_reference_lines(
            router_path, package_name, module_name
        ):
            updated_files.append(router_path)
        if _remove_module_reference_lines(
            models_path, package_name, module_name
        ):
            updated_files.append(models_path)
        removed_paths.extend(
            _remove_module_test_files(project_root, module_name)
        )
    else:
        if _remove_router_wiring(router_path, package_name, module_name):
            updated_files.append(router_path)
        if template_contract.update_db_models and _remove_line(
            models_path, _model_import_line(package_name, module_name)
        ):
            updated_files.append(models_path)
        removed_paths.extend(
            _remove_generated_tests(
                project_root, module_name, template_contract
            )
        )

    if module_root.exists() and not wiring_only:
        shutil.rmtree(module_root)
        removed_paths.append(module_root)

    if remove_llm_shared:
        updated_files.extend(_remove_llm_settings(project_root, package_root))
        removed_paths.extend(
            _remove_llm_integration_files(package_root, package_name)
        )
        remove_manifest_integration(
            project_root=project_root, integration_name="llm"
        )

    remove_manifest_module(project_root=project_root, module_name=module_name)
    if manifest_would_change:
        updated_files.append(manifest_path(project_root))

    return RemovedModuleResult(
        module_name=module_name,
        template=template_contract.name,
        project_root=project_root,
        package_root=package_root,
        removed_paths=tuple(dict.fromkeys(removed_paths)),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=_remove_next_steps(
            include_migration_note=include_migration_next_step,
            wiring_only=wiring_only,
            module_directory_preserved=wiring_only and module_root.exists(),
        ),
        force=force,
        wiring_only=wiring_only,
        custom_changes=tuple(custom_changes),
    )
