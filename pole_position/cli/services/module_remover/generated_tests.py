from pathlib import Path

from pole_position.cli.services.module_templates import (
    ModuleTemplateContract,
)
from pole_position.cli.services.project_checker import LEGACY_RACES_UNIT_TEST


def _remove_generated_tests(
    project_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> list[Path]:
    removed_paths: list[Path] = []

    for path in _generated_test_paths(
        project_root, module_name, template_contract
    ):
        if path.exists():
            path.unlink()
            removed_paths.append(path)

    return removed_paths


def _generated_test_paths(
    project_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> list[Path]:
    test_paths = [
        (
            project_root
            / "tests"
            / "integration"
            / template_contract.integration_test_name(module_name)
        ),
        project_root
        / "tests"
        / "unit"
        / template_contract.unit_test_name(module_name),
    ]
    # Legacy: older scaffolds shipped a "races" starter whose unit test used the
    # singular name (test_race_service.py). Clean it up only when that legacy
    # file is actually present, matching
    # project_checker._is_legacy_starter_module.
    if module_name == "races":
        legacy_unit_test = project_root / LEGACY_RACES_UNIT_TEST
        if legacy_unit_test.is_file():
            test_paths.append(legacy_unit_test)

    return test_paths
