from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.module_templates import (
    DEFAULT_CRUD_FEATURES,
    DEFAULT_MODULE_TEMPLATE,
    SUPPORTED_MODULE_TEMPLATES,
    CrudFeatureSet,
    ModuleTemplateContract,
    get_module_template_contract,
    module_template_detection_contracts,
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
    if manifest.exists:
        template = manifest.module_templates.get(module_name)
        parsed_template = _supported_manifest_module_template(template)
        if parsed_template is not None and parsed_template.name != "starter":
            return DetectedModuleTemplate(
                contract=get_module_template_contract(parsed_template.name),
                crud_features=parsed_template.crud_features,
            )

    for contract in module_template_detection_contracts():
        unit_test = (
            project_root
            / "tests"
            / "unit"
            / contract.unit_test_name(module_name)
        )
        if unit_test.exists():
            return DetectedModuleTemplate(contract=contract)

        if any(
            (module_root / file_name).exists()
            for file_name in contract.detection_file_names_for(module_name)
        ):
            return DetectedModuleTemplate(contract=contract)

    return DetectedModuleTemplate(
        contract=get_module_template_contract(DEFAULT_MODULE_TEMPLATE),
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
