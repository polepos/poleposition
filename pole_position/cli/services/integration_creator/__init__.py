from pathlib import Path

from pole_position.cli.services.integration_creator.blocks import (
    _active_env_line_key,
    _settings_line_key,
)
from pole_position.cli.services.integration_creator.constants import (
    ENV_INTEGRATION_MARKER,
    SETTINGS_INTEGRATION_MARKER,
)
from pole_position.cli.services.integration_creator.dependencies import (
    _ensure_project_dependency,
)
from pole_position.cli.services.integration_creator.files import (
    _ensure_integration_files,
    _kafka_integration_files,
    _rabbitmq_integration_files,
    _redis_integration_files,
    _rq_integration_files,
)
from pole_position.cli.services.integration_creator.result import (
    AddedIntegrationResult,
)
from pole_position.cli.services.integration_creator.settings_env import (
    _ensure_kafka_env,
    _ensure_kafka_settings,
    _ensure_rabbitmq_env,
    _ensure_rabbitmq_settings,
    _ensure_redis_env,
    _ensure_redis_settings,
    _ensure_rq_env,
    _ensure_rq_settings,
)
from pole_position.cli.services.integration_creator.steps import (
    _integration_next_steps,
)
from pole_position.cli.services.integration_specs import (
    IntegrationContract,
    get_creatable_integration_contract,
)
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    read_project_manifest,
    record_manifest_integration,
)
from pole_position.cli.services.pyproject_editor import (
    ensure_project_dependency_text,
)

__all__ = [
    "add_integration",
    "AddedIntegrationResult",
    "_kafka_integration_files",
    "_rabbitmq_integration_files",
    "_redis_integration_files",
    "_rq_integration_files",
]


def add_integration(
    integration_name: str,
    cwd: Path | None = None,
) -> AddedIntegrationResult:
    contract = get_creatable_integration_contract(integration_name)

    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    integration_root = package_root / "integrations" / contract.name

    _validate_add_integration_preflight(
        project_root=project_root,
        package_root=package_root,
        integration_root=integration_root,
        contract=contract,
    )

    integration_files: dict[str, str]
    update_settings = None
    update_env = None
    if contract.name == "kafka":
        integration_files = _kafka_integration_files(package_name)
        update_settings = _ensure_kafka_settings
        update_env = _ensure_kafka_env
    elif contract.name == "rabbitmq":
        integration_files = _rabbitmq_integration_files(package_name)
        update_settings = _ensure_rabbitmq_settings
        update_env = _ensure_rabbitmq_env
    elif contract.name == "redis":
        integration_files = _redis_integration_files(package_name)
        update_settings = _ensure_redis_settings
        update_env = _ensure_redis_env
    elif contract.name == "rq":
        integration_files = _rq_integration_files(package_name)
        update_settings = _ensure_rq_settings
        update_env = _ensure_rq_env
    else:  # pragma: no cover - guarded by get_creatable_integration_contract
        raise AssertionError(f"Unhandled integration: {contract.name}")

    written_files = _ensure_integration_files(package_root, integration_files)
    updated_files: list[Path] = []

    settings_path = package_root / "settings.py"
    if update_settings(settings_path, package_name):
        updated_files.append(settings_path)

    env_path = project_root / ".env.example"
    if update_env(env_path, package_name):
        updated_files.append(env_path)

    pyproject_path = project_root / "pyproject.toml"
    if _ensure_project_dependency(pyproject_path, contract.dependency):
        updated_files.append(pyproject_path)

    record_manifest_integration(
        project_root=project_root,
        integration_name=contract.name,
    )
    project_manifest_path = manifest_path(project_root)
    if project_manifest_path.is_file():
        updated_files.append(project_manifest_path)

    return AddedIntegrationResult(
        integration_name=contract.name,
        project_root=project_root,
        package_root=package_root,
        integration_files=tuple(written_files),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=_integration_next_steps(
            package_name=package_name,
            integration_name=contract.name,
        ),
    )


def _validate_add_integration_preflight(
    *,
    project_root: Path,
    package_root: Path,
    integration_root: Path,
    contract: IntegrationContract,
) -> None:
    problems: list[str] = []
    pyproject_path = project_root / "pyproject.toml"

    _collect_manifest_read_error(problems, project_root)

    if integration_root.exists():
        problems.append(f"Integration already exists: {contract.name}")

    _collect_required_file(problems, pyproject_path)
    _collect_patchable_project_dependency(
        problems, pyproject_path, contract.dependency
    )
    _collect_missing_marker_unless_entries_exist(
        problems,
        package_root / "settings.py",
        SETTINGS_INTEGRATION_MARKER,
        entries=contract.settings,
        entry_type="setting",
    )
    _collect_missing_marker_unless_entries_exist(
        problems,
        project_root / ".env.example",
        ENV_INTEGRATION_MARKER,
        entries=contract.env,
        entry_type="env",
    )

    if problems:
        formatted_problems = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(
            "Cannot add integration because the project layout is not ready:\n"
            f"{formatted_problems}"
        )


def _collect_required_file(problems: list[str], path: Path) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")


def _collect_manifest_read_error(
    problems: list[str], project_root: Path
) -> None:
    manifest = read_project_manifest(project_root)
    if manifest.read_error is not None:
        problems.append(manifest.read_error)


def _collect_patchable_project_dependency(
    problems: list[str],
    path: Path,
    dependency: str | None,
) -> None:
    if dependency is None or not path.is_file():
        return

    try:
        content = path.read_text(encoding="utf-8")
        ensure_project_dependency_text(
            content,
            dependency,
            path_label=str(path),
        )
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for integration add: "
            f"{path}: {exc.reason}"
        )
    except RuntimeError as exc:
        problems.append(str(exc))


def _collect_missing_marker(
    problems: list[str], path: Path, marker: str
) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for integration add: "
            f"{path}: {exc.reason}"
        )
        return

    if marker not in lines:
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _collect_missing_marker_unless_entries_exist(
    problems: list[str],
    path: Path,
    marker: str,
    *,
    entries: tuple[str, ...],
    entry_type: str,
) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for integration add: "
            f"{path}: {exc.reason}"
        )
        return

    if all(
        _entry_exists(content, entry, entry_type=entry_type)
        for entry in entries
    ):
        return

    if marker not in content.splitlines():
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _entry_exists(content: str, entry: str, *, entry_type: str) -> bool:
    if entry_type == "setting":
        return any(
            _settings_line_key(line) == entry for line in content.splitlines()
        )

    return any(
        _active_env_line_key(line) == entry for line in content.splitlines()
    )
