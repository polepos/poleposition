import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from pole_position.cli.services.auth_creator import AUTH_DEPENDENCY
from pole_position.cli.services.dependency_contract import (
    dependency_contract_satisfied,
    quoted_dependency_values,
)
from pole_position.cli.services.integration_specs import (
    CHECKED_INTEGRATION_CONTRACTS,
    IntegrationContract,
)
from pole_position.cli.services.project_check_constants import (
    AUTH_WORKFLOW_PACKAGE_PATHS,
    AUTH_WORKFLOW_TEST_PATHS,
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
from pole_position.cli.services.project_check_discovery import (
    _discover_core_project,
    _project_database_mode,
)
from pole_position.cli.services.project_check_io import (
    _env_keys,
    _parse_python_source,
    _read_file_text,
    _settings_keys,
)
from pole_position.cli.services.project_check_lifecycle import (
    _check_lifecycle_wiring,
    _detect_module_kind,
    _has_reported_parse_error,
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
from pole_position.cli.services.project_wiring import (
    has_router_import,
    has_router_include,
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


def _check_auth_workflow(
    *,
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    uses_database: bool,
) -> None:
    pyproject_content = _read_file_text(
        project_root / "pyproject.toml", problems
    )
    if not _should_check_auth_workflow(
        project_root=project_root,
        package_root=package_root,
        manifest=manifest,
        pyproject_content=pyproject_content,
    ):
        return

    if not uses_database:
        problems.append(
            "Auth workflow requires generated database wiring but the "
            "project is "
            "configured without a database."
        )
        return

    _check_auth_files(problems, package_root)
    _check_auth_tests(problems, project_root)
    _check_auth_dependency(
        problems=problems,
        project_root=project_root,
        pyproject_content=pyproject_content,
    )
    _check_auth_router_wiring(problems, package_root)
    _check_auth_model_wiring(problems, package_root)


def _should_check_auth_workflow(
    *,
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    pyproject_content: str | None,
) -> bool:
    if manifest.exists and manifest.enabled_integrations.get("auth"):
        return True

    if any(
        (package_root / relative_path).exists()
        for relative_path in AUTH_WORKFLOW_PACKAGE_PATHS
    ):
        return True

    if any(
        (project_root / relative_path).exists()
        for relative_path in AUTH_WORKFLOW_TEST_PATHS
    ):
        return True

    router_content = _read_file_text(package_root / "api" / "router.py") or ""
    if (
        f"{package_root.name}.auth.router" in router_content
        or "/auth" in router_content
    ):
        return True

    models_content = _read_file_text(package_root / "db" / "models.py") or ""
    if f"{package_root.name}.auth import model" in models_content:
        return True

    return pyproject_content is not None and _pyproject_has_dependency(
        pyproject_content, AUTH_DEPENDENCY
    )


def _check_auth_files(problems: list[str], package_root: Path) -> None:
    for relative_path in AUTH_WORKFLOW_PACKAGE_PATHS:
        path = package_root / relative_path
        if not path.exists():
            problems.append(f"Auth workflow is missing generated file: {path}")


def _check_auth_tests(problems: list[str], project_root: Path) -> None:
    integration_test = project_root / "tests" / "integration" / "test_auth.py"
    unit_test = project_root / "tests" / "unit" / "test_auth_service.py"

    if not integration_test.exists():
        problems.append(
            f"Auth workflow is missing integration test: {integration_test}"
        )

    if not unit_test.exists():
        problems.append(f"Auth workflow is missing unit test: {unit_test}")


def _check_auth_dependency(
    *,
    problems: list[str],
    project_root: Path,
    pyproject_content: str | None,
) -> None:
    if pyproject_content is None:
        return

    if not _pyproject_has_dependency(pyproject_content, AUTH_DEPENDENCY):
        problems.append(
            f"Auth workflow is missing dependency in "
            f"{project_root / 'pyproject.toml'}: {AUTH_DEPENDENCY}"
        )


def _check_auth_router_wiring(problems: list[str], package_root: Path) -> None:
    router_path = package_root / "api" / "router.py"
    content = _read_file_text(router_path, problems)
    if content is None:
        return

    tree = _parse_python_source(content, router_path, problems)
    if tree is None:
        return

    package_name = package_root.name
    router_module = f"{package_name}.auth.router"
    import_line = (
        f"from {package_name}.auth.router import router as auth_router"
    )
    include_line = (
        'api_router.include_router(auth_router, prefix="/auth", tags=["auth"])'
    )

    if not has_router_import(tree, router_module, "auth_router"):
        problems.append(
            f"Auth workflow is missing router import in {router_path}: "
            f"{import_line}"
        )

    if not has_router_include(tree, "auth_router", "auth"):
        problems.append(
            f"Auth workflow is missing API router include in "
            f"{router_path}: {include_line}"
        )


def _check_auth_model_wiring(problems: list[str], package_root: Path) -> None:
    models_path = package_root / "db" / "models.py"
    content = _read_file_text(models_path, problems)
    if content is None:
        return

    if _has_reported_parse_error(problems, models_path):
        return

    tree = _parse_python_source(content, models_path, problems)
    if tree is None:
        return

    import_line = (
        f"    from {package_root.name}.auth import model as auth_model  # "
        f"noqa: F401"
    )
    if import_line not in content.splitlines():
        problems.append(
            f"Auth workflow is missing model import in {models_path}: "
            f"{import_line}"
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


def _pyproject_has_dependency(
    pyproject_content: str, required_dependency: str
) -> bool:
    return dependency_contract_satisfied(
        _project_dependency_specs(pyproject_content),
        required_dependency,
    )


def _project_dependency_specs(pyproject_content: str) -> tuple[str, ...]:
    if tomllib is not None:
        try:
            pyproject = tomllib.loads(pyproject_content)
        except tomllib.TOMLDecodeError:
            return ()

        project = pyproject.get("project")
        if not isinstance(project, dict):
            return ()

        dependencies = project.get("dependencies")
        if not isinstance(dependencies, list):
            return ()

        return tuple(
            dependency
            for dependency in dependencies
            if isinstance(dependency, str)
        )

    return _fallback_project_dependency_specs(pyproject_content)


def _fallback_project_dependency_specs(
    pyproject_content: str,
) -> tuple[str, ...]:
    project_match = re.search(
        r"(?ms)^\s*\[project\]\s*$"
        r"(?P<section>.*?)"
        r"^\s*\[[^\]]+\]\s*$",
        f"{pyproject_content}\n[__poleposition_end__]\n",
    )
    if project_match is None:
        return ()

    dependencies_match = re.search(
        r"(?ms)^\s*dependencies\s*=\s*\[(?P<dependencies>.*?)\]\s*(?:#.*)?$",
        project_match.group("section"),
    )
    if dependencies_match is None:
        return ()

    return quoted_dependency_values(dependencies_match.group("dependencies"))


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
