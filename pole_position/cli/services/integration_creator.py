from pathlib import Path

from pole_position.cli.services.integration_specs import (
    IntegrationContract,
    KAFKA_INTEGRATION_CONTRACT,
    RABBITMQ_INTEGRATION_CONTRACT,
    SUPPORTED_INTEGRATIONS,
    get_creatable_integration_contract,
)
from pole_position.cli.services.module_templates.renderer import render_template
from pole_position.cli.services.project_locator import find_package_root, find_project_root
from pole_position.cli.services.project_manifest import record_manifest_integration
from pole_position.cli.services.pyproject_editor import (
    ensure_project_dependency,
    ensure_project_dependency_text,
)


SETTINGS_INTEGRATION_MARKER = "    # polepos:integration-settings"
SETTINGS_LLM_MARKER = "    # polepos:llm-settings"
ENV_INTEGRATION_MARKER = "# polepos:integration-env"
ENV_LLM_MARKER = "# polepos:llm-env"


def add_integration(integration_name: str, cwd: Path | None = None) -> None:
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

    if contract.name == "kafka":
        _ensure_integration_files(
            package_root,
            _kafka_integration_files(package_name),
        )
        _ensure_kafka_settings(package_root / "settings.py", package_name)
        _ensure_kafka_env(project_root / ".env.example", package_name)
        ensure_project_dependency(project_root / "pyproject.toml", contract.dependency)
        record_manifest_integration(
            project_root=project_root,
            integration_name=contract.name,
        )
        return

    if contract.name == "rabbitmq":
        _ensure_integration_files(
            package_root,
            _rabbitmq_integration_files(package_name),
        )
        _ensure_rabbitmq_settings(package_root / "settings.py", package_name)
        _ensure_rabbitmq_env(project_root / ".env.example", package_name)
        ensure_project_dependency(project_root / "pyproject.toml", contract.dependency)
        record_manifest_integration(
            project_root=project_root,
            integration_name=contract.name,
        )
        return


def _validate_add_integration_preflight(
    *,
    project_root: Path,
    package_root: Path,
    integration_root: Path,
    contract: IntegrationContract,
) -> None:
    problems: list[str] = []
    pyproject_path = project_root / "pyproject.toml"

    if integration_root.exists():
        problems.append(f"Integration already exists: {contract.name}")

    _collect_required_file(problems, pyproject_path)
    _collect_patchable_project_dependency(problems, pyproject_path, contract.dependency)
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


def _collect_patchable_project_dependency(
    problems: list[str],
    path: Path,
    dependency: str | None,
) -> None:
    if dependency is None or not path.is_file():
        return

    content = path.read_text(encoding="utf-8")
    try:
        ensure_project_dependency_text(
            content,
            dependency,
            path_label=str(path),
        )
    except RuntimeError as exc:
        problems.append(str(exc))


def _collect_missing_marker(problems: list[str], path: Path, marker: str) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    if marker not in path.read_text(encoding="utf-8").splitlines():
        problems.append(f"Required managed marker '{marker}' is missing in {path}")


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

    content = path.read_text(encoding="utf-8")
    if all(_entry_exists(content, entry, entry_type=entry_type) for entry in entries):
        return

    if marker not in content.splitlines():
        problems.append(f"Required managed marker '{marker}' is missing in {path}")


def _entry_exists(content: str, entry: str, *, entry_type: str) -> bool:
    if entry_type == "setting":
        return any(
            line.strip().startswith(f"{entry}:")
            for line in content.splitlines()
        )

    return any(
        _env_line_key(line) == entry
        for line in content.splitlines()
    )


def _ensure_integration_files(package_root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        path = package_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def _files_for_contract(
    contract: IntegrationContract,
    files: dict[str, str],
) -> dict[str, str]:
    missing = set(contract.file_names) - set(files)
    extra = set(files) - set(contract.file_names)
    if missing or extra:
        raise RuntimeError(f"Integration file contract drifted: {contract.name}")

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


def _ensure_kafka_settings(path: Path, package_name: str) -> None:
    _ensure_settings_entries_before_marker_or_anchor(
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


def _ensure_kafka_env(path: Path, package_name: str) -> None:
    _ensure_env_entries_before_marker_or_anchor(
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


def _ensure_rabbitmq_settings(path: Path, package_name: str) -> None:
    _ensure_settings_entries_before_marker_or_anchor(
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


def _ensure_rabbitmq_env(path: Path, package_name: str) -> None:
    _ensure_env_entries_before_marker_or_anchor(
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


def _ensure_settings_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
) -> None:
    _ensure_block_entries_before_marker_or_anchor(
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
) -> None:
    _ensure_block_entries_before_marker_or_anchor(
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
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    existing_keys = {
        key
        for line in lines
        if (key := key_for_line(line)) is not None
    }
    missing_lines = [
        line
        for line in block
        if (key := key_for_line(line)) is not None and key not in existing_keys
    ]

    if not missing_lines:
        return

    insert_at = _find_insert_index(lines, markers, anchor)
    lines[insert_at:insert_at] = missing_lines + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _settings_line_key(line: str) -> str | None:
    stripped = line.strip()
    if ":" not in stripped:
        return None
    key = stripped.split(":", 1)[0]
    return key if key.isidentifier() else None


def _env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("# "):
        stripped = stripped[2:].strip()
    if "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0]
    return key if key else None


def _insert_block_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    insert_at = _find_insert_index(lines, markers, anchor)

    lines[insert_at:insert_at] = block + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
