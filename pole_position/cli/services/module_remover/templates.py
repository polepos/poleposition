from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.module_templates import (
    DEFAULT_CRUD_FEATURES,
    SUPPORTED_MODULE_TEMPLATES,
    CrudFeatureSet,
    ModuleTemplateContract,
    get_module_template_contract,
)
from pole_position.cli.services.module_templates.detection import (
    detect_module_template_name,
)
from pole_position.cli.services.project_manifest import (
    ManifestModuleTemplate,
    parse_manifest_module_template,
    read_project_manifest,
)


@dataclass(frozen=True)
class DetectedModuleTemplate:
    contract: ModuleTemplateContract
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES


def _detect_module_template(
    project_root: Path,
    module_root: Path,
    module_name: str,
) -> DetectedModuleTemplate:
    manifest = read_project_manifest(project_root)
    manifest_parsed = None
    if manifest.exists:
        manifest_parsed = _supported_manifest_module_template(
            manifest.module_templates.get(module_name)
        )
        if manifest_parsed is not None and manifest_parsed.name == "starter":
            manifest_parsed = None

    template_name = detect_module_template_name(
        tests_root=project_root / "tests",
        module_root=module_root,
        module_name=module_name,
        manifest_template_name=(
            manifest_parsed.name if manifest_parsed is not None else None
        ),
    )

    crud_features = (
        manifest_parsed.crud_features
        if manifest_parsed is not None and manifest_parsed.name == template_name
        else DEFAULT_CRUD_FEATURES
    )
    return DetectedModuleTemplate(
        contract=get_module_template_contract(template_name),
        crud_features=crud_features,
    )


def _detect_module_contract(
    project_root: Path,
    module_root: Path,
    module_name: str,
) -> ModuleTemplateContract:
    return _detect_module_template(
        project_root, module_root, module_name
    ).contract


def _supported_manifest_module_template(
    template: str | None,
) -> ManifestModuleTemplate | None:
    if not template:
        return None

    try:
        parsed_template = parse_manifest_module_template(template)
    except ValueError:
        return None

    if parsed_template.name not in SUPPORTED_MODULE_TEMPLATES:
        return None

    return parsed_template
