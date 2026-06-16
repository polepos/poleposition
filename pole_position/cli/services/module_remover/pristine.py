from pathlib import Path

from pole_position.cli.services.module_remover.constants import (
    PYTHON_BYTECODE_SUFFIXES,
    PYTHON_CACHE_DIRECTORIES,
)
from pole_position.cli.services.module_templates import (
    DEFAULT_CRUD_FEATURES,
    CrudFeatureSet,
    ModuleTemplateContract,
    build_module_template,
)


def _detect_custom_changes(
    *,
    project_root: Path,
    package_root: Path,
    module_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES,
) -> list[str]:
    template = build_module_template(
        template=template_contract.name,
        package_name=package_root.name,
        module_name=module_name,
        crud_features=crud_features,
    )
    changes: list[str] = []

    if module_root.is_dir():
        expected_module_files = template.files
        for path in sorted(module_root.rglob("*")):
            if not path.is_file():
                continue

            relative_path = path.relative_to(module_root).as_posix()
            if _is_ignored_generated_artifact(path.relative_to(module_root)):
                continue

            expected_content = expected_module_files.get(relative_path)
            if expected_content is None:
                changes.append(f"Unexpected module file: {path}")
                continue

            if not _generated_file_matches(path, expected_content):
                changes.append(f"Modified generated module file: {path}")

    integration_test_path = (
        project_root / "tests" / "integration" / template.integration_test_name
    )
    unit_test_path = project_root / "tests" / "unit" / template.unit_test_name
    expected_tests = {
        integration_test_path: template.integration_test_content,
        unit_test_path: template.unit_test_content,
    }
    for path, expected_content in expected_tests.items():
        if path.is_file() and not _generated_file_matches(
            path, expected_content
        ):
            changes.append(f"Modified generated test file: {path}")

    return changes


def _detect_custom_test_changes(
    *,
    project_root: Path,
    package_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES,
) -> list[str]:
    template = build_module_template(
        template=template_contract.name,
        package_name=package_root.name,
        module_name=module_name,
        crud_features=crud_features,
    )
    changes: list[str] = []
    integration_test_path = (
        project_root / "tests" / "integration" / template.integration_test_name
    )
    unit_test_path = project_root / "tests" / "unit" / template.unit_test_name
    expected_tests = {
        integration_test_path: template.integration_test_content,
        unit_test_path: template.unit_test_content,
    }

    for path, expected_content in expected_tests.items():
        if path.is_file() and not _generated_file_matches(
            path, expected_content
        ):
            changes.append(f"Modified generated test file: {path}")

    return changes


def _generated_file_matches(path: Path, expected_content: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == expected_content
    except UnicodeDecodeError:
        return False


def _is_ignored_generated_artifact(relative_path: Path) -> bool:
    return (
        any(part in PYTHON_CACHE_DIRECTORIES for part in relative_path.parts)
        or relative_path.suffix in PYTHON_BYTECODE_SUFFIXES
    )


def _custom_changes_message(
    module_name: str,
    custom_changes: list[str],
    *,
    wiring_only: bool = False,
) -> str:
    formatted_changes = "\n".join(f"- {change}" for change in custom_changes)
    if wiring_only:
        return (
            "Cannot clean module wiring because generated tests appear to "
            "contain "
            "custom changes:\n"
            f"{formatted_changes}\n"
            f"Use `polepos remove module {module_name} --wiring-only --force` "
            "to remove those tests anyway."
        )

    return (
        "Cannot remove module because it appears to contain custom changes:\n"
        f"{formatted_changes}\n"
        f"Use `polepos remove module {module_name} --force` to remove it "
        f"anyway."
    )
