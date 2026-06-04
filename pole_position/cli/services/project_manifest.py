import re
from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.module_templates.crud_features import (
    DEFAULT_CRUD_FEATURES,
    CrudFeatureSet,
)

MANIFEST_FILE_NAME = ".poleposition.toml"
SECTION_PATTERN = re.compile(r"^\s*\[([^\]]+)\]\s*$")
ASSIGNMENT_PATTERN = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.+?)\s*$"
)
MODULE_TEMPLATE_VALUE_PATTERN = re.compile(
    r"^(?P<template>[A-Za-z0-9_-]+)(?:\[(?P<features>[A-Za-z0-9_, -]*)\])?$"
)


@dataclass(frozen=True)
class ProjectManifest:
    package_name: str | None = None
    database: str | None = None
    modules: dict[str, str] | None = None
    integrations: dict[str, bool] | None = None
    invalid_integrations: dict[str, str] | None = None
    read_error: str | None = None
    exists: bool = False

    @property
    def module_templates(self) -> dict[str, str]:
        return dict(self.modules or {})

    @property
    def enabled_integrations(self) -> dict[str, bool]:
        return dict(self.integrations or {})

    @property
    def invalid_integration_values(self) -> dict[str, str]:
        return dict(self.invalid_integrations or {})


@dataclass(frozen=True)
class ManifestModuleTemplate:
    name: str
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES


def manifest_path(project_root: Path) -> Path:
    return project_root / MANIFEST_FILE_NAME


def format_manifest_module_template(
    template: str,
    *,
    features: tuple[str, ...] = (),
) -> str:
    if template != "crud" or not features:
        return template

    crud_features = CrudFeatureSet.from_labels(set(features))
    return f"{template}[{','.join(crud_features.enabled_labels)}]"


def parse_manifest_module_template(value: str) -> ManifestModuleTemplate:
    raw_value = value.strip()
    match = MODULE_TEMPLATE_VALUE_PATTERN.match(raw_value)
    if match is None:
        raise ValueError(f"Unsupported module template value: {value}")

    template = match.group("template")
    raw_features = match.group("features")
    if raw_features is None:
        return ManifestModuleTemplate(name=template)

    feature_labels = {
        label.strip() for label in raw_features.split(",") if label.strip()
    }
    if template != "crud":
        raise ValueError(
            f"Only the crud module template supports feature options: {value}"
        )

    return ManifestModuleTemplate(
        name=template,
        crud_features=CrudFeatureSet.from_labels(feature_labels),
    )


def read_project_manifest(project_root: Path) -> ProjectManifest:
    path = manifest_path(project_root)
    if not path.is_file():
        return ProjectManifest()

    section = ""
    package_name: str | None = None
    database: str | None = None
    modules: dict[str, str] = {}
    integrations: dict[str, bool] = {}
    invalid_integrations: dict[str, str] = {}

    try:
        manifest_lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        return ProjectManifest(
            read_error=f"Could not read project manifest as UTF-8: {path}: "
            f"{exc.reason}",
            exists=True,
        )

    for raw_line in manifest_lines:
        line = _strip_comment(raw_line).strip()
        if not line:
            continue

        section_match = SECTION_PATTERN.match(line)
        if section_match is not None:
            section = section_match.group(1).strip()
            continue

        assignment_match = ASSIGNMENT_PATTERN.match(line)
        if assignment_match is None:
            continue

        key = assignment_match.group(1)
        raw_value = assignment_match.group(2)
        value = _parse_value(raw_value)

        if section == "poleposition" and key == "package":
            package_name = str(value)
        elif section == "poleposition" and key == "db":
            database = str(value)
        elif section == "modules":
            modules[key] = str(value)
        elif section == "integrations":
            if isinstance(value, bool):
                integrations[key] = value
                invalid_integrations.pop(key, None)
            else:
                integrations.pop(key, None)
                invalid_integrations[key] = raw_value.strip()

    return ProjectManifest(
        package_name=package_name,
        database=database,
        modules=modules,
        integrations=integrations,
        invalid_integrations=invalid_integrations,
        exists=True,
    )


def write_project_manifest(
    project_root: Path, manifest: ProjectManifest
) -> None:
    package_name = manifest.package_name or ""
    database = manifest.database or "custom"
    modules = manifest.module_templates
    integrations = manifest.enabled_integrations
    invalid_integrations = manifest.invalid_integration_values

    lines = [
        "[poleposition]",
        f'package = "{package_name}"',
        f'db = "{database}"',
        "",
        "[modules]",
    ]

    for module_name in sorted(modules):
        lines.append(f'{module_name} = "{modules[module_name]}"')

    lines.extend(["", "[integrations]"])
    for integration_name in sorted({*integrations, *invalid_integrations}):
        if integration_name in integrations:
            enabled = "true" if integrations[integration_name] else "false"
            lines.append(f"{integration_name} = {enabled}")
            continue

        lines.append(
            f"{integration_name} = {invalid_integrations[integration_name]}"
        )

    manifest_path(project_root).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def record_manifest_module(
    *,
    project_root: Path,
    module_name: str,
    template: str,
    features: tuple[str, ...] = (),
) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists or manifest.read_error is not None:
        return

    modules = manifest.module_templates
    modules[module_name] = format_manifest_module_template(
        template,
        features=features,
    )
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=modules,
            integrations=manifest.enabled_integrations,
            invalid_integrations=manifest.invalid_integration_values,
            exists=True,
        ),
    )


def remove_manifest_module(*, project_root: Path, module_name: str) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists or manifest.read_error is not None:
        return

    modules = manifest.module_templates
    modules.pop(module_name, None)
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=modules,
            integrations=manifest.enabled_integrations,
            invalid_integrations=manifest.invalid_integration_values,
            exists=True,
        ),
    )


def record_manifest_integration(
    *,
    project_root: Path,
    integration_name: str,
    enabled: bool = True,
) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists or manifest.read_error is not None:
        return

    integrations = manifest.enabled_integrations
    integrations[integration_name] = enabled
    invalid_integrations = manifest.invalid_integration_values
    invalid_integrations.pop(integration_name, None)
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=manifest.module_templates,
            integrations=integrations,
            invalid_integrations=invalid_integrations,
            exists=True,
        ),
    )


def remove_manifest_integration(
    *, project_root: Path, integration_name: str
) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists or manifest.read_error is not None:
        return

    integrations = manifest.enabled_integrations
    invalid_integrations = manifest.invalid_integration_values
    integrations.pop(integration_name, None)
    invalid_integrations.pop(integration_name, None)
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=manifest.module_templates,
            integrations=integrations,
            invalid_integrations=invalid_integrations,
            exists=True,
        ),
    )


def _strip_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if quote is not None:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = None
            escaped = False
            continue

        if char in {"'", '"'}:
            quote = char
            continue
        if char == "#":
            return line[:index]

    return line


def _parse_value(raw_value: str) -> str | bool:
    value = raw_value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
