from pathlib import Path

from pole_position.cli.services.module_creator.constants import (
    MODEL_IMPORTS_MARKER,
    MODULE_EXPORTS_MARKER,
    ROUTER_IMPORTS_MARKER,
    ROUTER_INCLUDES_MARKER,
)
from pole_position.cli.services.module_creator.files import (
    _write_module_files,
    _write_module_tests,
)
from pole_position.cli.services.module_creator.llm import (
    _ensure_llm_env,
    _ensure_llm_integrations,
    _ensure_llm_settings,
)
from pole_position.cli.services.module_creator.markers import (
    _insert_block_before_marker_or_anchor,
    _insert_line_before_marker,
    _insert_sorted_line_before_marker,
)
from pole_position.cli.services.module_creator.preflight import (
    _validate_add_module_preflight,
)
from pole_position.cli.services.module_creator.result import (
    AddedModuleResult,
)
from pole_position.cli.services.module_creator.steps import (
    _module_next_steps,
)
from pole_position.cli.services.module_creator.wiring import (
    _update_api_router,
    _update_db_models,
    _update_modules_init,
)
from pole_position.cli.services.module_templates import (
    DEFAULT_CRUD_FEATURES,
    SUPPORTED_MODULE_TEMPLATES,
    CrudFeatureSet,
    build_module_template,
)
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    record_manifest_integration,
    record_manifest_module,
)

__all__ = [
    "add_module",
    "AddedModuleResult",
    "MODEL_IMPORTS_MARKER",
    "MODULE_EXPORTS_MARKER",
    "ROUTER_IMPORTS_MARKER",
    "ROUTER_INCLUDES_MARKER",
    "_validate_add_module_preflight",
    "_insert_block_before_marker_or_anchor",
    "_insert_line_before_marker",
    "_insert_sorted_line_before_marker",
]


def add_module(
    module_name: str,
    template: str = "standard",
    cwd: Path | None = None,
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES,
) -> AddedModuleResult:
    if template not in SUPPORTED_MODULE_TEMPLATES:
        supported = ", ".join(SUPPORTED_MODULE_TEMPLATES)
        raise ValueError(
            f"Unsupported module template '{template}'. Expected one of: "
            f"{supported}."
        )

    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    modules_root = package_root / "modules"
    module_root = modules_root / module_name
    template_spec = build_module_template(
        template=template,
        package_name=package_name,
        module_name=module_name,
        crud_features=crud_features,
    )

    _validate_add_module_preflight(
        project_root=project_root,
        package_root=package_root,
        modules_root=modules_root,
        module_root=module_root,
        module_name=module_name,
        template_spec=template_spec,
    )

    module_files = _write_module_files(module_root, template_spec.files)
    test_files = _write_module_tests(project_root / "tests", template_spec)
    updated_files: list[Path] = []

    _update_modules_init(modules_root / "__init__.py", module_name)
    updated_files.append(modules_root / "__init__.py")
    _update_api_router(
        package_root / "api" / "router.py", package_name, module_name
    )
    updated_files.append(package_root / "api" / "router.py")
    if template_spec.update_db_models:
        _update_db_models(
            package_root / "db" / "models.py", package_name, module_name
        )
        updated_files.append(package_root / "db" / "models.py")
    if template_spec.ensure_llm_integrations:
        updated_files.extend(
            _ensure_llm_integrations(package_root, package_name)
        )
    if template_spec.ensure_llm_settings:
        if _ensure_llm_settings(package_root / "settings.py"):
            updated_files.append(package_root / "settings.py")
        if _ensure_llm_env(project_root / ".env.example"):
            updated_files.append(project_root / ".env.example")
        record_manifest_integration(
            project_root=project_root,
            integration_name="llm",
        )

    record_manifest_module(
        project_root=project_root,
        module_name=module_name,
        template=template,
        features=template_spec.features,
    )
    project_manifest_path = manifest_path(project_root)
    if project_manifest_path.is_file():
        updated_files.append(project_manifest_path)

    return AddedModuleResult(
        module_name=module_name,
        template=template,
        project_root=project_root,
        package_root=package_root,
        module_files=tuple(module_files),
        test_files=tuple(test_files),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=_module_next_steps(
            package_name=package_name,
            module_name=module_name,
            template_spec=template_spec,
        ),
        features=template_spec.features,
    )
