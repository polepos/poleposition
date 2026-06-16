from pathlib import Path

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
from pole_position.cli.services.integration_creator.preflight import (
    _validate_add_integration_preflight,
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
    get_creatable_integration_contract,
)
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    record_manifest_integration,
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
