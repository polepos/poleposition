"""Integration wiring checks: files, dependency, settings, env."""

from pathlib import Path

from pole_position.cli.services.integration_specs import (
    CHECKED_INTEGRATION_CONTRACTS,
    IntegrationContract,
)
from pole_position.cli.services.project_checker.deps import (
    _pyproject_has_dependency,
)
from pole_position.cli.services.project_checker.io import (
    _env_keys,
    _read_file_text,
    _settings_keys,
)
from pole_position.cli.services.project_checker.lifecycle import (
    _detect_module_kind,
    _should_skip_lifecycle_module,
)
from pole_position.cli.services.project_manifest import (
    ProjectManifest,
    read_project_manifest,
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
