from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from pole_position.cli.services.project_checker.auth import (
    _check_auth_workflow,
)
from pole_position.cli.services.project_checker.constants import (
    LEGACY_RACES_UNIT_TEST,
)
from pole_position.cli.services.project_checker.core import (
    _check_alembic_config,
    _check_database_free_remnants,
    _check_generated_structure,
    _check_managed_markers,
    _check_project_identity,
    _check_project_manifest,
)
from pole_position.cli.services.project_checker.discovery import (
    _discover_core_project,
    _project_database_mode,
)
from pole_position.cli.services.project_checker.integration import (
    _check_integration_wiring,
)
from pole_position.cli.services.project_checker.lifecycle import (
    _check_lifecycle_wiring,
)
from pole_position.cli.services.project_checker.report import (
    ProjectCheckIssue,
    ProjectCheckResult,
    describe_project_check_issue,
)
from pole_position.cli.services.project_manifest import (
    read_project_manifest,
)

__all__ = [
    "ProjectCheckIssue",
    "ProjectCheckResult",
    "check_core_project",
    "check_project",
    "describe_project_check_issue",
    "LEGACY_RACES_UNIT_TEST",
    "_check_alembic_config",
    "_check_database_free_remnants",
    "_check_generated_structure",
    "_check_lifecycle_wiring",
    "_check_managed_markers",
    "_check_project_identity",
    "_discover_core_project",
]


def check_project(cwd: Path | None = None) -> ProjectCheckResult:
    return _run_project_checks(
        cwd, include_lifecycle=True, include_integrations=True
    )


def check_core_project(cwd: Path | None = None) -> ProjectCheckResult:
    return _run_project_checks(
        cwd, include_lifecycle=False, include_integrations=False
    )


def _run_project_checks(
    cwd: Path | None = None,
    *,
    include_lifecycle: bool,
    include_integrations: bool,
) -> ProjectCheckResult:
    project_root, package_root = _discover_core_project(cwd)
    problems: list[str] = []
    manifest = read_project_manifest(project_root)
    database_mode = _project_database_mode(project_root, package_root, manifest)
    uses_database = database_mode in {"sqlite", "postgres", "managed"}

    _check_project_identity(problems, project_root, package_root)
    _check_project_manifest(problems, project_root, package_root, manifest)
    _check_generated_structure(
        problems,
        project_root,
        package_root,
        uses_database=uses_database,
    )
    if uses_database:
        _check_alembic_config(problems, project_root)
    elif database_mode == "none":
        _check_database_free_remnants(problems, project_root, package_root)
    _check_managed_markers(problems, package_root, uses_database=uses_database)
    if include_lifecycle:
        _check_lifecycle_wiring(problems, project_root, package_root, manifest)
    if include_integrations:
        _check_integration_wiring(
            problems, project_root, package_root, manifest
        )
        _check_auth_workflow(
            problems=problems,
            project_root=project_root,
            package_root=package_root,
            manifest=manifest,
            uses_database=uses_database,
        )

    return ProjectCheckResult(
        project_root=project_root,
        package_root=package_root,
        problems=problems,
    )
