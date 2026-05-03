from pathlib import Path
import os
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(cwd, *args):
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(REPO_ROOT)
    )

    return subprocess.run(
        [sys.executable, "-m", "pole_position.cli.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def test_add_command_shows_usage(tmp_path: Path):
    result = run_cli(tmp_path, "add")

    assert result.returncode == 0
    assert "Usage: polepos add <subcommand>" in result.stdout
    assert "integration" in result.stdout
    assert "module" in result.stdout


def test_add_kafka_integration_creates_files_and_updates_project(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode == 0
    assert "Added integration: kafka" in result.stdout

    package_root = project_root / "src" / "myapp"
    kafka_root = package_root / "integrations" / "kafka"
    expected_files = [
        package_root / "integrations" / "__init__.py",
        kafka_root / "__init__.py",
        kafka_root / "consumer.py",
        kafka_root / "factory.py",
        kafka_root / "producer.py",
        kafka_root / "schemas.py",
        kafka_root / "testing.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated Kafka file is missing: {path}"

    settings_content = (package_root / "settings.py").read_text(encoding="utf-8")
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    pyproject_content = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    producer_content = (kafka_root / "producer.py").read_text(encoding="utf-8")
    factory_content = (kafka_root / "factory.py").read_text(encoding="utf-8")
    testing_content = (kafka_root / "testing.py").read_text(encoding="utf-8")

    assert 'kafka_bootstrap_servers: str = "localhost:9092"' in settings_content
    assert 'kafka_client_id: str = "myapp"' in settings_content
    assert "kafka_request_timeout_ms: int = 40000" in settings_content
    assert "KAFKA_BOOTSTRAP_SERVERS=localhost:9092" in env_content
    assert "KAFKA_CLIENT_ID=myapp" in env_content
    assert '"aiokafka>=0.12.0",' in pyproject_content
    assert "from myapp.bootstrap.logging import get_logger" in producer_content
    assert "class KafkaEventProducer:" in producer_content
    assert "from aiokafka import AIOKafkaProducer" in factory_content
    assert "from aiokafka import AIOKafkaConsumer" in factory_content
    assert "class InMemoryKafkaEventProducer:" in testing_content
    assert "{{" not in producer_content
    assert "{{" not in factory_content


def test_add_kafka_integration_rejects_duplicate(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "integration", "kafka")
    second_result = run_cli(project_root, "add", "integration", "kafka")

    assert first_result.returncode == 0
    assert second_result.returncode != 0
    assert "Integration already exists: kafka" in second_result.stdout


def test_add_integration_preflight_fails_before_writing_when_marker_is_missing(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    env_path = project_root / ".env.example"

    settings_path.write_text(
        settings_path.read_text(encoding="utf-8").replace(
            "    # polepos:integration-settings",
            "    # integration settings are managed manually",
        ),
        encoding="utf-8",
    )
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "# polepos:integration-env",
            "# integration env values are managed manually",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode != 0
    assert "Cannot add integration because the project layout is not ready" in result.stdout
    assert (
        "Required managed marker '    # polepos:integration-settings' is missing"
        in result.stdout
    )
    assert (
        "Required managed marker '# polepos:integration-env' is missing"
        in result.stdout
    )
    assert not (package_root / "integrations" / "kafka").exists()
    assert "kafka_bootstrap_servers:" not in settings_path.read_text(encoding="utf-8")
    assert "KAFKA_BOOTSTRAP_SERVERS=" not in env_path.read_text(encoding="utf-8")
    assert '"aiokafka>=0.12.0",' not in (
        project_root / "pyproject.toml"
    ).read_text(encoding="utf-8")


def test_add_rabbitmq_integration_creates_files_and_updates_project(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "rabbitmq")

    assert result.returncode == 0
    assert "Added integration: rabbitmq" in result.stdout

    package_root = project_root / "src" / "myapp"
    rabbitmq_root = package_root / "integrations" / "rabbitmq"
    expected_files = [
        package_root / "integrations" / "__init__.py",
        rabbitmq_root / "__init__.py",
        rabbitmq_root / "consumer.py",
        rabbitmq_root / "factory.py",
        rabbitmq_root / "publisher.py",
        rabbitmq_root / "schemas.py",
        rabbitmq_root / "testing.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated RabbitMQ file is missing: {path}"

    settings_content = (package_root / "settings.py").read_text(encoding="utf-8")
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    pyproject_content = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    publisher_content = (rabbitmq_root / "publisher.py").read_text(encoding="utf-8")
    factory_content = (rabbitmq_root / "factory.py").read_text(encoding="utf-8")
    testing_content = (rabbitmq_root / "testing.py").read_text(encoding="utf-8")

    assert 'rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"' in settings_content
    assert 'rabbitmq_client_id: str = "myapp"' in settings_content
    assert "rabbitmq_prefetch_count: int = 10" in settings_content
    assert "RABBITMQ_URL=amqp://guest:guest@localhost:5672/" in env_content
    assert "RABBITMQ_CLIENT_ID=myapp" in env_content
    assert '"aio-pika>=9.0.0",' in pyproject_content
    assert "from myapp.bootstrap.logging import get_logger" in publisher_content
    assert "class RabbitMQEventPublisher:" in publisher_content
    assert "from aio_pika import connect_robust" in factory_content
    assert "class InMemoryRabbitMQEventPublisher:" in testing_content
    assert "{{" not in publisher_content
    assert "{{" not in factory_content


def test_add_rabbitmq_integration_rejects_duplicate(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "integration", "rabbitmq")
    second_result = run_cli(project_root, "add", "integration", "rabbitmq")

    assert first_result.returncode == 0
    assert second_result.returncode != 0
    assert "Integration already exists: rabbitmq" in second_result.stdout


def test_add_kafka_and_rabbitmq_integrations_can_coexist(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    kafka_result = run_cli(project_root, "add", "integration", "kafka")
    rabbitmq_result = run_cli(project_root, "add", "integration", "rabbitmq")

    assert kafka_result.returncode == 0
    assert rabbitmq_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    pyproject_content = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    settings_content = (package_root / "settings.py").read_text(encoding="utf-8")
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")

    assert (package_root / "integrations" / "kafka" / "producer.py").exists()
    assert (package_root / "integrations" / "rabbitmq" / "publisher.py").exists()
    assert pyproject_content.count('"aiokafka>=0.12.0",') == 1
    assert pyproject_content.count('"aio-pika>=9.0.0",') == 1
    assert settings_content.count("kafka_bootstrap_servers:") == 1
    assert settings_content.count("rabbitmq_url:") == 1
    assert env_content.count("KAFKA_BOOTSTRAP_SERVERS=") == 1
    assert env_content.count("RABBITMQ_URL=") == 1


def test_add_integration_rejects_unknown_integration(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "redis")

    assert result.returncode != 0
    assert "Unsupported integration 'redis'" in result.stdout
    assert "Integrations: kafka, rabbitmq" in result.stdout


def test_module_templates_render_without_leftover_placeholders() -> None:
    from pole_position.cli.services.module_templates import (
        build_module_template,
        llm_integration_files,
    )

    standard_template = build_module_template(
        template="standard",
        package_name="myapp",
        module_name="garage",
    )
    ai_template = build_module_template(
        template="ai-prompt",
        package_name="myapp",
        module_name="assistant",
    )
    api_only_template = build_module_template(
        template="api-only",
        package_name="myapp",
        module_name="webhooks",
    )
    rendered_content = [
        *standard_template.files.values(),
        standard_template.integration_test_content,
        standard_template.unit_test_content,
        *ai_template.files.values(),
        ai_template.integration_test_content,
        ai_template.unit_test_content,
        *api_only_template.files.values(),
        api_only_template.integration_test_content,
        api_only_template.unit_test_content,
        *llm_integration_files("myapp").values(),
    ]

    assert all("{{" not in content for content in rendered_content)
    assert all("}}" not in content for content in rendered_content)


def test_add_module_creates_module_files_and_updates_router(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode == 0
    assert "Added module: garage" in result.stdout
    assert "Template: standard" in result.stdout
    assert "Created:" in result.stdout
    assert "Updated:" in result.stdout
    assert "Next steps:" in result.stdout
    assert "src/myapp/modules/garage/router.py" in result.stdout
    assert "tests/integration/test_garage.py" in result.stdout
    assert "Run `polepos check`" in result.stdout
    assert 'polepos db revision -m "add garage table"' in result.stdout

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "garage"

    expected_files = [
        module_root / "__init__.py",
        module_root / "model.py",
        module_root / "repository.py",
        module_root / "router.py",
        module_root / "schemas.py",
        module_root / "service.py",
        project_root / "tests" / "integration" / "test_garage.py",
        project_root / "tests" / "unit" / "test_garage_service.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated module file is missing: {path}"

    router_content = (package_root / "api" / "router.py").read_text(encoding="utf-8")
    db_models_content = (package_root / "db" / "models.py").read_text(encoding="utf-8")
    modules_init_content = (package_root / "modules" / "__init__.py").read_text(encoding="utf-8")
    integration_test_content = (
        project_root / "tests" / "integration" / "test_garage.py"
    ).read_text(encoding="utf-8")
    service_content = (module_root / "service.py").read_text(encoding="utf-8")

    assert "from myapp.modules.garage.router import router as garage_router" in router_content
    assert 'api_router.include_router(garage_router, prefix="/garage", tags=["garage"])' in router_content
    assert router_content.splitlines()[0] == "from fastapi import APIRouter"
    assert "from myapp.modules.garage import model" in db_models_content
    assert '"garage"' in modules_init_content
    assert 'client.post("/api/v1/garage/"' in integration_test_content
    assert "from myapp.bootstrap.logging import get_logger" in service_content
    assert "logger = get_logger(__name__)" in service_content


def test_add_module_keeps_router_imports_sorted(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"

    first_result = run_cli(project_root, "add", "module", "zebra")
    second_result = run_cli(project_root, "add", "module", "alpha")

    assert first_result.returncode == 0
    assert second_result.returncode == 0

    router_lines = (project_root / "src" / "myapp" / "api" / "router.py").read_text(
        encoding="utf-8"
    ).splitlines()
    import_lines = [line for line in router_lines if line.startswith("from ")]

    assert import_lines == sorted(import_lines)


def test_add_module_rejects_duplicate_module(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "module", "garage")
    second_result = run_cli(project_root, "add", "module", "garage")

    assert first_result.returncode == 0
    assert second_result.returncode != 0
    assert "Module already exists: garage" in second_result.stdout


def test_add_module_requires_poleposition_project(tmp_path: Path):
    result = run_cli(tmp_path, "add", "module", "garage")

    assert result.returncode != 0
    assert "does not look like a PolePosition project" in result.stdout


def test_add_module_works_from_nested_directory(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    nested_dir = tmp_path / "myapp" / "src" / "myapp"
    result = run_cli(nested_dir, "add", "module", "garage")

    assert result.returncode == 0
    assert (tmp_path / "myapp" / "src" / "myapp" / "modules" / "garage" / "router.py").exists()


def test_add_module_works_with_custom_content_around_markers(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"

    router_path = package_root / "api" / "router.py"
    router_content = router_path.read_text(encoding="utf-8")
    router_content = router_content.replace(
        "# polepos:router-imports",
        "# custom import note\n# polepos:router-imports",
    ).replace(
        "# polepos:router-includes",
        "# custom include note\n# polepos:router-includes",
    )
    router_path.write_text(router_content, encoding="utf-8")

    models_path = package_root / "db" / "models.py"
    models_content = models_path.read_text(encoding="utf-8").replace(
        "    # polepos:model-imports",
        "    # custom model note\n    # polepos:model-imports",
    )
    models_path.write_text(models_content, encoding="utf-8")

    modules_init_path = package_root / "modules" / "__init__.py"
    modules_init_content = modules_init_path.read_text(encoding="utf-8").replace(
        "    # polepos:module-exports",
        "    # custom exports note\n    # polepos:module-exports",
    )
    modules_init_path.write_text(modules_init_content, encoding="utf-8")

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode == 0

    router_content = router_path.read_text(encoding="utf-8")
    models_content = models_path.read_text(encoding="utf-8")
    modules_init_content = modules_init_path.read_text(encoding="utf-8")

    assert "from myapp.modules.garage.router import router as garage_router" in router_content
    assert 'api_router.include_router(garage_router, prefix="/garage", tags=["garage"])' in router_content
    assert "# custom import note" in router_content
    assert "# custom include note" in router_content
    assert "from myapp.modules.garage import model  # noqa: F401" in models_content
    assert "# custom model note" in models_content
    assert '"garage"' in modules_init_content
    assert "# custom exports note" in modules_init_content


def test_add_module_preflight_fails_before_writing_when_marker_is_missing(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    models_path = package_root / "db" / "models.py"
    models_content = models_path.read_text(encoding="utf-8").replace(
        "    # polepos:model-imports",
        "    # custom model imports are managed manually",
    )
    models_path.write_text(models_content, encoding="utf-8")

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert "Cannot add module because the project layout is not ready" in result.stdout
    assert "Required managed marker '    # polepos:model-imports' is missing" in result.stdout
    assert "db/models.py" in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (project_root / "tests" / "integration" / "test_garage.py").exists()
    assert not (project_root / "tests" / "unit" / "test_garage_service.py").exists()


def test_add_module_with_ai_prompt_template_creates_llm_module_files(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "assistant", "--template", "ai-prompt")

    assert result.returncode == 0
    assert "Added module: assistant" in result.stdout

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "assistant"

    expected_files = [
        module_root / "__init__.py",
        module_root / "orchestrator.py",
        module_root / "prompts.py",
        module_root / "router.py",
        module_root / "schemas.py",
        module_root / "service.py",
        package_root / "integrations" / "__init__.py",
        package_root / "integrations" / "llm" / "__init__.py",
        package_root / "integrations" / "llm" / "factory.py",
        package_root / "integrations" / "llm" / "openai_client.py",
        package_root / "integrations" / "llm" / "anthropic_client.py",
        package_root / "integrations" / "llm" / "provider.py",
        package_root / "integrations" / "llm" / "schemas.py",
        project_root / "tests" / "integration" / "test_assistant.py",
        project_root / "tests" / "unit" / "test_assistant_orchestrator.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated AI module file is missing: {path}"

    router_content = (package_root / "api" / "router.py").read_text(encoding="utf-8")
    db_models_content = (package_root / "db" / "models.py").read_text(encoding="utf-8")
    settings_content = (package_root / "settings.py").read_text(encoding="utf-8")
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    service_content = (module_root / "service.py").read_text(encoding="utf-8")
    orchestrator_content = (module_root / "orchestrator.py").read_text(encoding="utf-8")
    integration_test_content = (
        project_root / "tests" / "integration" / "test_assistant.py"
    ).read_text(encoding="utf-8")

    assert 'api_router.include_router(assistant_router, prefix="/assistant", tags=["assistant"])' in router_content
    assert "from myapp.modules.assistant import model" not in db_models_content
    assert 'llm_provider: str = "openai"' in settings_content
    assert 'llm_model: str = "gpt-5.4-mini"' in settings_content
    assert "llm_timeout_seconds: float = 30.0" in settings_content
    assert "LLM_PROVIDER=openai" in env_content
    assert "LLM_MODEL=gpt-5.4-mini" in env_content
    assert "LLM_API_KEY=" in env_content
    assert "from myapp.bootstrap.logging import get_logger" in service_content
    assert "logger = get_logger(__name__)" in service_content
    assert "from myapp.integrations.llm.factory import get_llm_provider" in orchestrator_content
    assert "/api/v1/assistant/respond" in integration_test_content
    assert "return_value=StubProvider()" in integration_test_content


def test_add_module_with_api_only_option_creates_api_module_without_db_files(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "webhooks", "--api-only")

    assert result.returncode == 0
    assert "Added module: webhooks" in result.stdout
    assert "Template: api-only" in result.stdout
    assert "Run `polepos check`" in result.stdout
    assert "polepos db revision" not in result.stdout

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "webhooks"

    expected_files = [
        module_root / "__init__.py",
        module_root / "router.py",
        module_root / "schemas.py",
        module_root / "service.py",
        project_root / "tests" / "integration" / "test_webhooks.py",
        project_root / "tests" / "unit" / "test_webhooks_api_service.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated API-only file is missing: {path}"

    assert not (module_root / "model.py").exists()
    assert not (module_root / "repository.py").exists()

    router_content = (package_root / "api" / "router.py").read_text(encoding="utf-8")
    db_models_content = (package_root / "db" / "models.py").read_text(encoding="utf-8")
    integration_test_content = (
        project_root / "tests" / "integration" / "test_webhooks.py"
    ).read_text(encoding="utf-8")

    assert (
        'api_router.include_router(webhooks_router, prefix="/webhooks", '
        'tags=["webhooks"])'
    ) in router_content
    assert "from myapp.modules.webhooks import model" not in db_models_content
    assert 'client.post("/api/v1/webhooks/"' in integration_test_content


def test_add_module_with_api_only_template_alias(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "callbacks", "--template", "api-only")

    assert result.returncode == 0
    assert "Template: api-only" in result.stdout
    assert (
        project_root
        / "src"
        / "myapp"
        / "modules"
        / "callbacks"
        / "router.py"
    ).exists()
    assert (
        project_root
        / "tests"
        / "unit"
        / "test_callbacks_api_service.py"
    ).exists()


def test_add_module_rejects_api_only_with_other_template(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
        "--api-only",
    )

    assert result.returncode != 0
    assert "--api-only cannot be combined with another module template." in result.stdout


def test_add_module_ai_prompt_does_not_duplicate_llm_settings_or_integrations(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "module", "assistant", "--template", "ai-prompt")
    second_result = run_cli(project_root, "add", "module", "copilot", "--template", "ai-prompt")

    assert first_result.returncode == 0
    assert second_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_content = (package_root / "settings.py").read_text(encoding="utf-8")
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    provider_content = (
        package_root / "integrations" / "llm" / "provider.py"
    ).read_text(encoding="utf-8")

    assert settings_content.count('llm_provider: str = "openai"') == 1
    assert env_content.count("LLM_PROVIDER=openai") == 1
    assert provider_content.count("class LLMProvider(Protocol):") == 1


def test_add_module_rejects_unknown_template(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "assistant", "--template", "unknown")

    assert result.returncode != 0
    assert "Unsupported module template 'unknown'" in result.stdout
    assert "Templates: standard, ai-prompt, api-only" in result.stdout
