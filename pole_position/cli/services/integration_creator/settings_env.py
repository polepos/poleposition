from pathlib import Path

from pole_position.cli.services.integration_creator.blocks import (
    _ensure_env_entries_before_marker_or_anchor,
    _ensure_settings_entries_before_marker_or_anchor,
)
from pole_position.cli.services.integration_creator.constants import (
    ENV_INTEGRATION_MARKER,
    ENV_LLM_MARKER,
    SETTINGS_INTEGRATION_MARKER,
    SETTINGS_LLM_MARKER,
)


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
