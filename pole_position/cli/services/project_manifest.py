from dataclasses import dataclass
from pathlib import Path
import re


MANIFEST_FILE_NAME = ".poleposition.toml"
SECTION_PATTERN = re.compile(r"^\s*\[([^\]]+)\]\s*$")
ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.+?)\s*$")


@dataclass(frozen=True)
class ProjectManifest:
    package_name: str | None = None
    database: str | None = None
    modules: dict[str, str] | None = None
    integrations: dict[str, bool] | None = None
    exists: bool = False

    @property
    def module_templates(self) -> dict[str, str]:
        return dict(self.modules or {})

    @property
    def enabled_integrations(self) -> dict[str, bool]:
        return dict(self.integrations or {})


def manifest_path(project_root: Path) -> Path:
    return project_root / MANIFEST_FILE_NAME


def read_project_manifest(project_root: Path) -> ProjectManifest:
    path = manifest_path(project_root)
    if not path.is_file():
        return ProjectManifest()

    section = ""
    package_name: str | None = None
    database: str | None = None
    modules: dict[str, str] = {}
    integrations: dict[str, bool] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
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
        value = _parse_value(assignment_match.group(2))

        if section == "poleposition" and key == "package":
            package_name = str(value)
        elif section == "poleposition" and key == "db":
            database = str(value)
        elif section == "modules":
            modules[key] = str(value)
        elif section == "integrations":
            integrations[key] = bool(value)

    return ProjectManifest(
        package_name=package_name,
        database=database,
        modules=modules,
        integrations=integrations,
        exists=True,
    )


def write_project_manifest(project_root: Path, manifest: ProjectManifest) -> None:
    package_name = manifest.package_name or ""
    database = manifest.database or "custom"
    modules = manifest.module_templates
    integrations = manifest.enabled_integrations

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
    for integration_name in sorted(integrations):
        enabled = "true" if integrations[integration_name] else "false"
        lines.append(f"{integration_name} = {enabled}")

    manifest_path(project_root).write_text("\n".join(lines) + "\n", encoding="utf-8")


def record_manifest_module(
    *,
    project_root: Path,
    module_name: str,
    template: str,
) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists:
        return

    modules = manifest.module_templates
    modules[module_name] = template
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=modules,
            integrations=manifest.enabled_integrations,
            exists=True,
        ),
    )


def remove_manifest_module(*, project_root: Path, module_name: str) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists:
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
    if not manifest.exists:
        return

    integrations = manifest.enabled_integrations
    integrations[integration_name] = enabled
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=manifest.module_templates,
            integrations=integrations,
            exists=True,
        ),
    )


def remove_manifest_integration(*, project_root: Path, integration_name: str) -> None:
    manifest = read_project_manifest(project_root)
    if not manifest.exists:
        return

    integrations = manifest.enabled_integrations
    integrations.pop(integration_name, None)
    write_project_manifest(
        project_root,
        ProjectManifest(
            package_name=manifest.package_name,
            database=manifest.database,
            modules=manifest.module_templates,
            integrations=integrations,
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
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value
