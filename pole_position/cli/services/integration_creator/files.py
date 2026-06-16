from pathlib import Path

from pole_position.cli.services.integration_specs import (
    KAFKA_INTEGRATION_CONTRACT,
    RABBITMQ_INTEGRATION_CONTRACT,
    REDIS_INTEGRATION_CONTRACT,
    RQ_INTEGRATION_CONTRACT,
    IntegrationContract,
)
from pole_position.cli.services.module_templates.renderer import render_template


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
