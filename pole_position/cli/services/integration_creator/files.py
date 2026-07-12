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


def _render_integration_template(relative_path: str, package_name: str) -> str:
    return render_template(
        f"integrations/{relative_path}.tpl",
        {"package_name": package_name},
    )


def _integration_files(
    contract: IntegrationContract, package_name: str
) -> dict[str, str]:
    # The contract's file names are the generated paths under the package
    # (e.g. ``integrations/kafka/consumer.py``), which map one-to-one to the
    # ``integrations/<...>.tpl`` templates. The shared ``integrations/__init__``
    # is an empty package marker with no template.
    files: dict[str, str] = {}
    for file_name in contract.file_names:
        if file_name == "integrations/__init__.py":
            files[file_name] = ""
            continue
        template_path = file_name.removeprefix("integrations/")
        files[file_name] = _render_integration_template(
            template_path, package_name
        )

    return files


def _kafka_integration_files(package_name: str) -> dict[str, str]:
    return _integration_files(KAFKA_INTEGRATION_CONTRACT, package_name)


def _rabbitmq_integration_files(package_name: str) -> dict[str, str]:
    return _integration_files(RABBITMQ_INTEGRATION_CONTRACT, package_name)


def _redis_integration_files(package_name: str) -> dict[str, str]:
    return _integration_files(REDIS_INTEGRATION_CONTRACT, package_name)


def _rq_integration_files(package_name: str) -> dict[str, str]:
    return _integration_files(RQ_INTEGRATION_CONTRACT, package_name)
