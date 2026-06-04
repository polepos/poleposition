from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.integration_specs import (
    KAFKA_INTEGRATION_CONTRACT,
    RABBITMQ_INTEGRATION_CONTRACT,
    REDIS_INTEGRATION_CONTRACT,
    RQ_INTEGRATION_CONTRACT,
    IntegrationContract,
    get_creatable_integration_contract,
)
from pole_position.cli.services.module_templates.renderer import render_template
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
    ensure_project_dependency,
    ensure_project_dependency_text,
)

SETTINGS_INTEGRATION_MARKER = "    # polepos:integration-settings"
SETTINGS_LLM_MARKER = "    # polepos:llm-settings"
ENV_INTEGRATION_MARKER = "# polepos:integration-env"
ENV_LLM_MARKER = "# polepos:llm-env"


@dataclass(frozen=True)
class AddedIntegrationResult:
    integration_name: str
    project_root: Path
    package_root: Path
    integration_files: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]

    @property
    def package_name(self) -> str:
        return self.package_root.name


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


def _ensure_integration_files(
    package_root: Path, files: dict[str, str]
) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in files.items():
        path = package_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            written.append(path)

    return written


def _ensure_project_dependency(path: Path, dependency: str | None) -> bool:
    if dependency is None:
        return False

    original = path.read_text(encoding="utf-8")
    ensure_project_dependency(path, dependency)
    return path.read_text(encoding="utf-8") != original


def _files_for_contract(
    contract: IntegrationContract,
    files: dict[str, str],
) -> dict[str, str]:
    missing = set(contract.file_names) - set(files)
    extra = set(files) - set(contract.file_names)
    if missing or extra:
        raise RuntimeError(
            f"Integration file contract drifted: {contract.name}"
        )

    return {file_name: files[file_name] for file_name in contract.file_names}


def _render_integration_template(relative_path: str, package_name: str) -> str:
    return render_template(
        f"integrations/{relative_path}.tpl",
        {"package_name": package_name},
    )


def _kafka_integration_files(package_name: str) -> dict[str, str]:
    files = {
        "integrations/__init__.py": "",
        "integrations/kafka/__init__.py": _render_integration_template(
            "kafka/__init__.py",
            package_name,
        ),
        "integrations/kafka/consumer.py": _render_integration_template(
            "kafka/consumer.py",
            package_name,
        ),
        "integrations/kafka/factory.py": _render_integration_template(
            "kafka/factory.py",
            package_name,
        ),
        "integrations/kafka/producer.py": _render_integration_template(
            "kafka/producer.py",
            package_name,
        ),
        "integrations/kafka/schemas.py": _render_integration_template(
            "kafka/schemas.py",
            package_name,
        ),
        "integrations/kafka/testing.py": _render_integration_template(
            "kafka/testing.py",
            package_name,
        ),
    }
    return _files_for_contract(KAFKA_INTEGRATION_CONTRACT, files)


def _rabbitmq_integration_files(package_name: str) -> dict[str, str]:
    files = {
        "integrations/__init__.py": "",
        "integrations/rabbitmq/__init__.py": _render_integration_template(
            "rabbitmq/__init__.py",
            package_name,
        ),
        "integrations/rabbitmq/consumer.py": _render_integration_template(
            "rabbitmq/consumer.py",
            package_name,
        ),
        "integrations/rabbitmq/factory.py": _render_integration_template(
            "rabbitmq/factory.py",
            package_name,
        ),
        "integrations/rabbitmq/publisher.py": _render_integration_template(
            "rabbitmq/publisher.py",
            package_name,
        ),
        "integrations/rabbitmq/schemas.py": _render_integration_template(
            "rabbitmq/schemas.py",
            package_name,
        ),
        "integrations/rabbitmq/testing.py": _render_integration_template(
            "rabbitmq/testing.py",
            package_name,
        ),
    }
    return _files_for_contract(RABBITMQ_INTEGRATION_CONTRACT, files)


def _redis_integration_files(package_name: str) -> dict[str, str]:
    files = {
        "integrations/__init__.py": "",
        "integrations/redis/__init__.py": _render_integration_template(
            "redis/__init__.py",
            package_name,
        ),
        "integrations/redis/cache.py": _render_integration_template(
            "redis/cache.py",
            package_name,
        ),
        "integrations/redis/factory.py": _render_integration_template(
            "redis/factory.py",
            package_name,
        ),
        "integrations/redis/schemas.py": _render_integration_template(
            "redis/schemas.py",
            package_name,
        ),
        "integrations/redis/testing.py": _render_integration_template(
            "redis/testing.py",
            package_name,
        ),
    }
    return _files_for_contract(REDIS_INTEGRATION_CONTRACT, files)


def _rq_integration_files(package_name: str) -> dict[str, str]:
    files = {
        "integrations/__init__.py": "",
        "integrations/rq/__init__.py": _render_integration_template(
            "rq/__init__.py",
            package_name,
        ),
        "integrations/rq/factory.py": _render_integration_template(
            "rq/factory.py",
            package_name,
        ),
        "integrations/rq/jobs.py": _render_integration_template(
            "rq/jobs.py",
            package_name,
        ),
        "integrations/rq/schemas.py": _render_integration_template(
            "rq/schemas.py",
            package_name,
        ),
        "integrations/rq/testing.py": _render_integration_template(
            "rq/testing.py",
            package_name,
        ),
        "integrations/rq/worker.py": _render_integration_template(
            "rq/worker.py",
            package_name,
        ),
    }
    return _files_for_contract(RQ_INTEGRATION_CONTRACT, files)


def _ensure_kafka_settings(path: Path, package_name: str) -> bool:
    return _ensure_settings_entries_before_marker_or_anchor(
        path=path,
        block=_kafka_settings_block(package_name),
        markers=[SETTINGS_INTEGRATION_MARKER, SETTINGS_LLM_MARKER],
        anchor="    model_config = SettingsConfigDict(",
    )


def _kafka_settings_block(package_name: str) -> list[str]:
    return [
        "    kafka_enabled: bool = False",
        '    kafka_bootstrap_servers: str = "localhost:9092"',
        f'    kafka_client_id: str = "{package_name}"',
        f'    kafka_default_topic: str = "{package_name}.events"',
        f'    kafka_group_id: str = "{package_name}"',
        '    kafka_auto_offset_reset: str = "earliest"',
        '    kafka_acks: str = "all"',
        "    kafka_compression_type: str | None = None",
        "    kafka_request_timeout_ms: int = 40000",
    ]


def _ensure_kafka_env(path: Path, package_name: str) -> bool:
    return _ensure_env_entries_before_marker_or_anchor(
        path=path,
        block=_kafka_env_block(package_name),
        markers=[ENV_INTEGRATION_MARKER, ENV_LLM_MARKER],
        anchor=None,
    )


def _kafka_env_block(package_name: str) -> list[str]:
    return [
        "KAFKA_ENABLED=false",
        "KAFKA_BOOTSTRAP_SERVERS=localhost:9092",
        f"KAFKA_CLIENT_ID={package_name}",
        f"KAFKA_DEFAULT_TOPIC={package_name}.events",
        f"KAFKA_GROUP_ID={package_name}",
        "KAFKA_AUTO_OFFSET_RESET=earliest",
        "KAFKA_ACKS=all",
        "# KAFKA_COMPRESSION_TYPE=",
        "KAFKA_REQUEST_TIMEOUT_MS=40000",
    ]


def _ensure_rabbitmq_settings(path: Path, package_name: str) -> bool:
    return _ensure_settings_entries_before_marker_or_anchor(
        path=path,
        block=_rabbitmq_settings_block(package_name),
        markers=[SETTINGS_INTEGRATION_MARKER, SETTINGS_LLM_MARKER],
        anchor="    model_config = SettingsConfigDict(",
    )


def _rabbitmq_settings_block(package_name: str) -> list[str]:
    return [
        "    rabbitmq_enabled: bool = False",
        '    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"',
        f'    rabbitmq_client_id: str = "{package_name}"',
        f'    rabbitmq_exchange: str = "{package_name}.events"',
        '    rabbitmq_exchange_type: str = "topic"',
        "    rabbitmq_exchange_durable: bool = True",
        f'    rabbitmq_default_routing_key: str = "{package_name}.event"',
        f'    rabbitmq_default_queue: str = "{package_name}.events"',
        "    rabbitmq_queue_durable: bool = True",
        "    rabbitmq_prefetch_count: int = 10",
    ]


def _ensure_rabbitmq_env(path: Path, package_name: str) -> bool:
    return _ensure_env_entries_before_marker_or_anchor(
        path=path,
        block=_rabbitmq_env_block(package_name),
        markers=[ENV_INTEGRATION_MARKER, ENV_LLM_MARKER],
        anchor=None,
    )


def _rabbitmq_env_block(package_name: str) -> list[str]:
    return [
        "RABBITMQ_ENABLED=false",
        "RABBITMQ_URL=amqp://guest:guest@localhost:5672/",
        f"RABBITMQ_CLIENT_ID={package_name}",
        f"RABBITMQ_EXCHANGE={package_name}.events",
        "RABBITMQ_EXCHANGE_TYPE=topic",
        "RABBITMQ_EXCHANGE_DURABLE=true",
        f"RABBITMQ_DEFAULT_ROUTING_KEY={package_name}.event",
        f"RABBITMQ_DEFAULT_QUEUE={package_name}.events",
        "RABBITMQ_QUEUE_DURABLE=true",
        "RABBITMQ_PREFETCH_COUNT=10",
    ]


def _ensure_redis_settings(path: Path, package_name: str) -> bool:
    return _ensure_settings_entries_before_marker_or_anchor(
        path=path,
        block=_redis_settings_block(package_name),
        markers=[SETTINGS_INTEGRATION_MARKER, SETTINGS_LLM_MARKER],
        anchor="    model_config = SettingsConfigDict(",
    )


def _redis_settings_block(package_name: str) -> list[str]:
    return [
        "    redis_enabled: bool = False",
        '    redis_url: str = "redis://localhost:6379/0"',
        f'    redis_client_name: str = "{package_name}"',
        f'    redis_key_prefix: str = "{package_name}"',
        "    redis_socket_timeout_seconds: float = 5.0",
    ]


def _ensure_redis_env(path: Path, package_name: str) -> bool:
    return _ensure_env_entries_before_marker_or_anchor(
        path=path,
        block=_redis_env_block(package_name),
        markers=[ENV_INTEGRATION_MARKER, ENV_LLM_MARKER],
        anchor=None,
    )


def _redis_env_block(package_name: str) -> list[str]:
    return [
        "REDIS_ENABLED=false",
        "REDIS_URL=redis://localhost:6379/0",
        f"REDIS_CLIENT_NAME={package_name}",
        f"REDIS_KEY_PREFIX={package_name}",
        "REDIS_SOCKET_TIMEOUT_SECONDS=5.0",
    ]


def _ensure_rq_settings(path: Path, package_name: str) -> bool:
    return _ensure_settings_entries_before_marker_or_anchor(
        path=path,
        block=_rq_settings_block(package_name),
        markers=[SETTINGS_INTEGRATION_MARKER, SETTINGS_LLM_MARKER],
        anchor="    model_config = SettingsConfigDict(",
    )


def _rq_settings_block(package_name: str) -> list[str]:
    return [
        "    rq_enabled: bool = False",
        '    rq_redis_url: str = "redis://localhost:6379/0"',
        f'    rq_default_queue: str = "{package_name}.default"',
        f'    rq_worker_name: str = "{package_name}-worker"',
        "    rq_job_timeout_seconds: int = 300",
        "    rq_result_ttl_seconds: int = 500",
    ]


def _ensure_rq_env(path: Path, package_name: str) -> bool:
    return _ensure_env_entries_before_marker_or_anchor(
        path=path,
        block=_rq_env_block(package_name),
        markers=[ENV_INTEGRATION_MARKER, ENV_LLM_MARKER],
        anchor=None,
    )


def _rq_env_block(package_name: str) -> list[str]:
    return [
        "RQ_ENABLED=false",
        "RQ_REDIS_URL=redis://localhost:6379/0",
        f"RQ_DEFAULT_QUEUE={package_name}.default",
        f"RQ_WORKER_NAME={package_name}-worker",
        "RQ_JOB_TIMEOUT_SECONDS=300",
        "RQ_RESULT_TTL_SECONDS=500",
    ]


def _ensure_settings_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
) -> bool:
    return _ensure_block_entries_before_marker_or_anchor(
        path=path,
        block=block,
        markers=markers,
        anchor=anchor,
        key_for_line=_settings_line_key,
    )


def _ensure_env_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
) -> bool:
    return _ensure_block_entries_before_marker_or_anchor(
        path=path,
        block=block,
        markers=markers,
        anchor=anchor,
        key_for_line=_env_line_key,
    )


def _ensure_block_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
    key_for_line,
) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    missing_lines = _missing_block_lines(
        lines=lines,
        block=block,
        key_for_line=key_for_line,
    )

    if not missing_lines:
        return False

    insert_at = _find_insert_index(lines, markers, anchor)
    lines[insert_at:insert_at] = missing_lines + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _settings_line_key(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("#"):
        return None
    if ":" not in stripped:
        return None
    key = stripped.split(":", 1)[0]
    return key if key.isidentifier() else None


def _env_line_key(line: str) -> str | None:
    return _active_env_line_key(line)


def _active_env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0]
    return key if key else None


def _commented_env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    stripped = stripped[1:].strip()
    if "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0]
    return key if key else None


def _missing_block_lines(
    *,
    lines: list[str],
    block: list[str],
    key_for_line,
) -> list[str]:
    if key_for_line is not _env_line_key:
        existing_keys = {
            key for line in lines if (key := key_for_line(line)) is not None
        }
        return [
            line
            for line in block
            if (key := key_for_line(line)) is not None
            and key not in existing_keys
        ]

    active_keys = {
        key for line in lines if (key := _active_env_line_key(line)) is not None
    }
    commented_keys = {
        key
        for line in lines
        if (key := _commented_env_line_key(line)) is not None
    }
    missing_lines: list[str] = []
    for line in block:
        active_key = _active_env_line_key(line)
        if active_key is not None:
            if active_key not in active_keys:
                missing_lines.append(line)
            continue

        commented_key = _commented_env_line_key(line)
        if commented_key is None:
            continue
        if (
            commented_key not in active_keys
            and commented_key not in commented_keys
        ):
            missing_lines.append(line)

    return missing_lines


def _find_insert_index(
    lines: list[str],
    markers: list[str],
    anchor: str | None,
) -> int:
    insert_at = None

    for marker in markers:
        if marker in lines:
            insert_at = lines.index(marker)
            break

    if insert_at is None and anchor and anchor in lines:
        insert_at = lines.index(anchor)

    if insert_at is None:
        insert_at = len(lines)

    return insert_at


def _integration_next_steps(
    *,
    package_name: str,
    integration_name: str,
) -> tuple[str, ...]:
    return (
        "Run `uv sync --extra dev`",
        (
            "Copy new integration env values from `.env.example` into `.env` "
            "if `.env` already exists"
        ),
        f"Review src/{package_name}/integrations/{integration_name}/",
        "Run `polepos check`",
    )
