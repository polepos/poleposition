from pathlib import Path

from pole_position.cli.services.module_templates import ModuleTemplate


def _write_module_files(module_root: Path, files: dict[str, str]) -> list[Path]:
    module_root.mkdir(parents=True)
    written: list[Path] = []

    for file_name, content in files.items():
        path = module_root / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return written


def _write_module_tests(
    tests_root: Path, template_spec: ModuleTemplate
) -> list[Path]:
    integration_root = tests_root / "integration"
    unit_root = tests_root / "unit"
    integration_root.mkdir(parents=True, exist_ok=True)
    unit_root.mkdir(parents=True, exist_ok=True)

    integration_test = integration_root / template_spec.integration_test_name
    unit_test = unit_root / template_spec.unit_test_name

    integration_test.write_text(
        template_spec.integration_test_content,
        encoding="utf-8",
    )
    unit_test.write_text(
        template_spec.unit_test_content,
        encoding="utf-8",
    )
    return [integration_test, unit_test]
