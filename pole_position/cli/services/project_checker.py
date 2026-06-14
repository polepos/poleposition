from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from pole_position.cli.services.integration_specs import (
    CHECKED_INTEGRATION_CONTRACTS,
    IntegrationContract,
)
from pole_position.cli.services.project_check_auth import (
    _check_auth_workflow,
)
from pole_position.cli.services.project_check_constants import (
    LEGACY_RACES_UNIT_TEST,
)
from pole_position.cli.services.project_check_core import (
    _check_alembic_config,
    _check_database_free_remnants,
    _check_generated_structure,
    _check_managed_markers,
    _check_project_identity,
    _check_project_manifest,
)
from pole_position.cli.services.project_check_deps import (
    _pyproject_has_dependency,
)
from pole_position.cli.services.project_check_discovery import (
    _discover_core_project,
    _project_database_mode,
)
from pole_position.cli.services.project_check_io import (
    _env_keys,
    _read_file_text,
    _settings_keys,
)
from pole_position.cli.services.project_check_lifecycle import (
    _check_lifecycle_wiring,
    _detect_module_kind,
    _should_skip_lifecycle_module,
)
from pole_position.cli.services.project_check_report import (
    ProjectCheckIssue,
    ProjectCheckResult,
    describe_project_check_issue,
)
from pole_position.cli.services.project_manifest import (
    ProjectManifest,
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


def _check_integration_wiring(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest | None = None,
) -> None:
    manifest = manifest or read_project_manifest(project_root)
    settings_content = _read_file_text(package_root / "settings.py", problems)
    env_content = _read_file_text(project_root / ".env.example", problems)
    pyproject_content = _read_file_text(
        project_root / "pyproject.toml", problems
    )

    for contract in CHECKED_INTEGRATION_CONTRACTS:
        if not _should_check_integration(
            contract=contract,
            project_root=project_root,
            package_root=package_root,
            manifest=manifest,
            settings_content=settings_content,
            env_content=env_content,
            pyproject_content=pyproject_content,
        ):
            continue

        _check_integration_files(
            problems=problems,
            package_root=package_root,
            contract=contract,
        )
        _check_integration_dependency(
            problems=problems,
            project_root=project_root,
            contract=contract,
            pyproject_content=pyproject_content,
        )
        _check_integration_settings(
            problems=problems,
            package_root=package_root,
            contract=contract,
            settings_content=settings_content,
        )
        _check_integration_env(
            problems=problems,
            project_root=project_root,
            contract=contract,
            env_content=env_content,
        )


def _should_check_integration(
    *,
    contract: IntegrationContract,
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    settings_content: str | None,
    env_content: str | None,
    pyproject_content: str | None,
) -> bool:
    if manifest.exists:
        integrations = manifest.enabled_integrations
        if integrations.get(contract.name):
            return True
        if contract.name == "llm" and _has_ai_prompt_module(
            project_root,
            package_root,
        ):
            return True
        return _has_integration_signal(
            contract=contract,
            project_root=project_root,
            package_root=package_root,
            settings_content=settings_content,
            env_content=env_content,
            pyproject_content=pyproject_content,
        )

    return _has_integration_signal(
        contract=contract,
        project_root=project_root,
        package_root=package_root,
        settings_content=settings_content,
        env_content=env_content,
        pyproject_content=pyproject_content,
    )


def _has_integration_signal(
    *,
    contract: IntegrationContract,
    project_root: Path,
    package_root: Path,
    settings_content: str | None,
    env_content: str | None,
    pyproject_content: str | None,
) -> bool:
    if (package_root / "integrations" / contract.name).exists():
        return True

    dependency = contract.dependency
    if (
        isinstance(dependency, str)
        and pyproject_content is not None
        and _pyproject_has_dependency(pyproject_content, dependency)
    ):
        return True

    if settings_content is not None:
        settings_keys = _settings_keys(settings_content)
        if any(setting in settings_keys for setting in contract.settings):
            return True

    if env_content is not None:
        env_keys = _env_keys(env_content)
        integration_env = contract.env + contract.optional_env
        if any(env_name in env_keys for env_name in integration_env):
            return True

    if contract.name == "llm":
        return _has_ai_prompt_module(project_root, package_root)

    return False


def _has_ai_prompt_module(project_root: Path, package_root: Path) -> bool:
    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return False

    for module_root in modules_root.iterdir():
        if not module_root.is_dir():
            continue
        if _should_skip_lifecycle_module(project_root, module_root):
            continue
        if _detect_module_kind(project_root, module_root) == "ai-prompt":
            return True

    return False


def _check_integration_files(
    *,
    problems: list[str],
    package_root: Path,
    contract: IntegrationContract,
) -> None:
    for relative_path in contract.file_names:
        path = package_root / relative_path
        if not path.exists():
            problems.append(
                f"Integration '{contract.name}' is missing generated "
                f"file: {path}"
            )


def _check_integration_dependency(
    *,
    problems: list[str],
    project_root: Path,
    contract: IntegrationContract,
    pyproject_content: str | None,
) -> None:
    dependency = contract.dependency
    if not isinstance(dependency, str):
        return

    if pyproject_content is None:
        return

    if not _pyproject_has_dependency(pyproject_content, dependency):
        problems.append(
            f"Integration '{contract.name}' is missing dependency in "
            f"{project_root / 'pyproject.toml'}: {dependency}"
        )


def _check_integration_settings(
    *,
    problems: list[str],
    package_root: Path,
    contract: IntegrationContract,
    settings_content: str | None,
) -> None:
    if settings_content is None:
        return

    settings_path = package_root / "settings.py"
    settings_keys = _settings_keys(settings_content)
    for setting in contract.settings:
        if setting not in settings_keys:
            problems.append(
                f"Integration '{contract.name}' is missing setting in "
                f"{settings_path}: {setting}"
            )


def _check_integration_env(
    *,
    problems: list[str],
    project_root: Path,
    contract: IntegrationContract,
    env_content: str | None,
) -> None:
    if env_content is None:
        return

    env_path = project_root / ".env.example"
    env_keys = _env_keys(env_content)
    for env_name in contract.env:
        if env_name not in env_keys:
            problems.append(
                f"Integration '{contract.name}' is missing env value in "
                f"{env_path}: {env_name}"
            )
