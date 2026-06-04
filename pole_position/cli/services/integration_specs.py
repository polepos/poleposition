from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationContract:
    name: str
    file_names: tuple[str, ...]
    settings: tuple[str, ...]
    env: tuple[str, ...]
    dependency: str | None = None
    creatable: bool = True
    optional_env: tuple[str, ...] = ()


KAFKA_INTEGRATION_CONTRACT = IntegrationContract(
    name="kafka",
    dependency="aiokafka>=0.12.0",
    file_names=(
        "integrations/__init__.py",
        "integrations/kafka/__init__.py",
        "integrations/kafka/consumer.py",
        "integrations/kafka/factory.py",
        "integrations/kafka/producer.py",
        "integrations/kafka/schemas.py",
        "integrations/kafka/testing.py",
    ),
    settings=(
        "kafka_enabled",
        "kafka_bootstrap_servers",
        "kafka_client_id",
        "kafka_default_topic",
        "kafka_group_id",
        "kafka_auto_offset_reset",
        "kafka_acks",
        "kafka_compression_type",
        "kafka_request_timeout_ms",
    ),
    env=(
        "KAFKA_ENABLED",
        "KAFKA_BOOTSTRAP_SERVERS",
        "KAFKA_CLIENT_ID",
        "KAFKA_DEFAULT_TOPIC",
        "KAFKA_GROUP_ID",
        "KAFKA_AUTO_OFFSET_RESET",
        "KAFKA_ACKS",
        "KAFKA_REQUEST_TIMEOUT_MS",
    ),
    optional_env=("KAFKA_COMPRESSION_TYPE",),
)

RABBITMQ_INTEGRATION_CONTRACT = IntegrationContract(
    name="rabbitmq",
    dependency="aio-pika>=9.0.0",
    file_names=(
        "integrations/__init__.py",
        "integrations/rabbitmq/__init__.py",
        "integrations/rabbitmq/consumer.py",
        "integrations/rabbitmq/factory.py",
        "integrations/rabbitmq/publisher.py",
        "integrations/rabbitmq/schemas.py",
        "integrations/rabbitmq/testing.py",
    ),
    settings=(
        "rabbitmq_enabled",
        "rabbitmq_url",
        "rabbitmq_client_id",
        "rabbitmq_exchange",
        "rabbitmq_exchange_type",
        "rabbitmq_exchange_durable",
        "rabbitmq_default_routing_key",
        "rabbitmq_default_queue",
        "rabbitmq_queue_durable",
        "rabbitmq_prefetch_count",
    ),
    env=(
        "RABBITMQ_ENABLED",
        "RABBITMQ_URL",
        "RABBITMQ_CLIENT_ID",
        "RABBITMQ_EXCHANGE",
        "RABBITMQ_EXCHANGE_TYPE",
        "RABBITMQ_EXCHANGE_DURABLE",
        "RABBITMQ_DEFAULT_ROUTING_KEY",
        "RABBITMQ_DEFAULT_QUEUE",
        "RABBITMQ_QUEUE_DURABLE",
        "RABBITMQ_PREFETCH_COUNT",
    ),
)

REDIS_INTEGRATION_CONTRACT = IntegrationContract(
    name="redis",
    dependency="redis>=5.0.0",
    file_names=(
        "integrations/__init__.py",
        "integrations/redis/__init__.py",
        "integrations/redis/cache.py",
        "integrations/redis/factory.py",
        "integrations/redis/schemas.py",
        "integrations/redis/testing.py",
    ),
    settings=(
        "redis_enabled",
        "redis_url",
        "redis_client_name",
        "redis_key_prefix",
        "redis_socket_timeout_seconds",
    ),
    env=(
        "REDIS_ENABLED",
        "REDIS_URL",
        "REDIS_CLIENT_NAME",
        "REDIS_KEY_PREFIX",
        "REDIS_SOCKET_TIMEOUT_SECONDS",
    ),
)

RQ_INTEGRATION_CONTRACT = IntegrationContract(
    name="rq",
    dependency="rq>=1.16.0",
    file_names=(
        "integrations/__init__.py",
        "integrations/rq/__init__.py",
        "integrations/rq/factory.py",
        "integrations/rq/jobs.py",
        "integrations/rq/schemas.py",
        "integrations/rq/testing.py",
        "integrations/rq/worker.py",
    ),
    settings=(
        "rq_enabled",
        "rq_redis_url",
        "rq_default_queue",
        "rq_worker_name",
        "rq_job_timeout_seconds",
        "rq_result_ttl_seconds",
    ),
    env=(
        "RQ_ENABLED",
        "RQ_REDIS_URL",
        "RQ_DEFAULT_QUEUE",
        "RQ_WORKER_NAME",
        "RQ_JOB_TIMEOUT_SECONDS",
        "RQ_RESULT_TTL_SECONDS",
    ),
)

LLM_INTEGRATION_CONTRACT = IntegrationContract(
    name="llm",
    file_names=(
        "integrations/__init__.py",
        "integrations/llm/__init__.py",
        "integrations/llm/anthropic_client.py",
        "integrations/llm/factory.py",
        "integrations/llm/openai_client.py",
        "integrations/llm/provider.py",
        "integrations/llm/schemas.py",
    ),
    settings=(
        "llm_provider",
        "llm_model",
        "llm_api_key",
        "llm_base_url",
        "llm_timeout_seconds",
        "llm_temperature",
        "llm_max_tokens",
    ),
    env=(
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_TEMPERATURE",
    ),
    optional_env=("LLM_MAX_TOKENS",),
    creatable=False,
)

INTEGRATION_CONTRACTS = {
    contract.name: contract
    for contract in (
        KAFKA_INTEGRATION_CONTRACT,
        RABBITMQ_INTEGRATION_CONTRACT,
        REDIS_INTEGRATION_CONTRACT,
        RQ_INTEGRATION_CONTRACT,
        LLM_INTEGRATION_CONTRACT,
    )
}

CREATABLE_INTEGRATION_CONTRACTS = tuple(
    contract
    for contract in INTEGRATION_CONTRACTS.values()
    if contract.creatable
)
CHECKED_INTEGRATION_CONTRACTS = tuple(INTEGRATION_CONTRACTS.values())
SUPPORTED_INTEGRATIONS = tuple(
    contract.name for contract in CREATABLE_INTEGRATION_CONTRACTS
)


def get_integration_contract(integration_name: str) -> IntegrationContract:
    try:
        return INTEGRATION_CONTRACTS[integration_name]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_INTEGRATIONS)
        raise ValueError(
            f"Unsupported integration '{integration_name}'. Expected one "
            f"of: {supported}."
        ) from exc


def get_creatable_integration_contract(
    integration_name: str,
) -> IntegrationContract:
    contract = get_integration_contract(integration_name)
    if not contract.creatable:
        supported = ", ".join(SUPPORTED_INTEGRATIONS)
        raise ValueError(
            f"Unsupported integration '{integration_name}'. Expected one "
            f"of: {supported}."
        )
    return contract
