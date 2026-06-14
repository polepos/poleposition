"""Core project checks: identity, manifest, structure, alembic, markers."""

from pathlib import Path

from pole_position.cli.services.module_templates import (
    SUPPORTED_MODULE_TEMPLATES,
)
from pole_position.cli.services.project_checker.constants import (
    ALEMBIC_PATHS,
    CORE_PACKAGE_PATHS,
    CORE_PROJECT_PATHS,
    DATABASE_FREE_FORBIDDEN_PACKAGE_CONTENT,
    DATABASE_FREE_FORBIDDEN_PROJECT_CONTENT,
    DATABASE_MANAGED_MARKERS,
    DATABASE_PACKAGE_PATHS,
    MANAGED_MARKERS,
)
from pole_position.cli.services.project_checker.io import (
    _read_file_lines,
    _read_file_text,
)
from pole_position.cli.services.project_manifest import (
    ProjectManifest,
    parse_manifest_module_template,
)


def _check_project_identity(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    src_root = project_root / "src"

    if not (project_root / "pyproject.toml").is_file():
        problems.append(
            f"Project identity file is missing: "
            f"{project_root / 'pyproject.toml'}"
        )

    if not src_root.is_dir():
        problems.append(f"Project src directory is missing: {src_root}")

    if package_root.parent != src_root:
        problems.append(
            f"Application package is not under project src directory: "
            f"{package_root}"
        )

    if not package_root.name.isidentifier():
        problems.append(
            f"Application package name is not a valid Python identifier: "
            f"{package_root.name}"
        )


def _check_project_manifest(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
) -> None:
    if not manifest.exists:
        return

    if manifest.read_error is not None:
        problems.append(manifest.read_error)
        return

    manifest_path = project_root / ".poleposition.toml"
    if manifest.package_name and manifest.package_name != package_root.name:
        problems.append(
            "Project manifest package does not match discovered package in "
            f"{manifest_path}: {manifest.package_name} != {package_root.name}"
        )

    supported_database_modes = {
        "sqlite",
        "postgres",
        "none",
        "custom",
    }
    if (
        manifest.database
        and manifest.database.strip().lower() not in supported_database_modes
    ):
        problems.append(
            "Project manifest has unsupported database mode in "
            f"{manifest_path}: {manifest.database}"
        )

    supported_module_templates = {*SUPPORTED_MODULE_TEMPLATES, "starter"}
    for module_name, template in manifest.module_templates.items():
        try:
            parsed_template = parse_manifest_module_template(template)
        except ValueError:
            parsed_template = None

        if (
            parsed_template is not None
            and parsed_template.name in supported_module_templates
        ):
            continue
        problems.append(
            "Project manifest has unsupported module template in "
            f"{manifest_path}: {module_name} = {template}"
        )

    for integration_name, value in manifest.invalid_integration_values.items():
        problems.append(
            "Project manifest has unsupported integration value in "
            f"{manifest_path}: {integration_name} = {value}"
        )


def _check_generated_structure(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    *,
    uses_database: bool = True,
) -> None:
    package_paths = list(CORE_PACKAGE_PATHS)
    if uses_database:
        package_paths.extend(DATABASE_PACKAGE_PATHS)

    required_paths = [
        *[project_root / relative_path for relative_path in CORE_PROJECT_PATHS],
        *[package_root / relative_path for relative_path in package_paths],
    ]

    for path in required_paths:
        if not path.exists():
            problems.append(f"Required generated path is missing: {path}")


def _check_alembic_config(problems: list[str], project_root: Path) -> None:
    required_paths = [
        project_root / relative_path for relative_path in ALEMBIC_PATHS
    ]

    for path in required_paths:
        if not path.exists():
            problems.append(f"Required Alembic path is missing: {path}")


def _check_database_free_remnants(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    for (
        relative_path,
        snippets,
    ) in DATABASE_FREE_FORBIDDEN_PROJECT_CONTENT.items():
        _collect_forbidden_database_free_content(
            problems,
            project_root / relative_path,
            snippets,
        )

    for (
        relative_path,
        snippets,
    ) in DATABASE_FREE_FORBIDDEN_PACKAGE_CONTENT.items():
        _collect_forbidden_database_free_content(
            problems,
            package_root / relative_path,
            snippets,
        )


def _collect_forbidden_database_free_content(
    problems: list[str],
    path: Path,
    snippets: list[str],
) -> None:
    content = _read_file_text(path, problems)
    if content is None:
        return

    for snippet in snippets:
        if snippet not in content:
            continue

        display_snippet = snippet.strip() or snippet
        problems.append(
            "Database-free project contains database-specific content in "
            f"{path}: {display_snippet}"
        )


def _check_managed_markers(
    problems: list[str],
    package_root: Path,
    *,
    uses_database: bool = True,
) -> None:
    for relative_path, markers in MANAGED_MARKERS.items():
        if not uses_database and relative_path in DATABASE_MANAGED_MARKERS:
            continue
        path = (package_root / relative_path).resolve()

        if not path.is_file():
            problems.append(f"Managed file is missing: {path}")
            continue

        lines = _read_file_lines(path, problems)
        if lines is None:
            continue

        for marker in markers:
            if marker not in lines:
                problems.append(
                    f"Managed marker '{marker}' is missing in {path}"
                )
