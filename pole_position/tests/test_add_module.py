import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

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


def _assert_python_files_compile(project_root: Path) -> None:
    python_files = sorted(project_root.rglob("*.py"))

    assert python_files
    for path in python_files:
        py_compile.compile(str(path), doraise=True)


def _remove_first_dependencies_array(content: str) -> str:
    lines = content.splitlines()
    updated: list[str] = []
    removing = False
    removed = False

    for line in lines:
        if not removed and line.startswith("dependencies = ["):
            removing = True
            continue

        if removing:
            if line == "]":
                removing = False
                removed = True
            continue

        updated.append(line)

    return "\n".join(updated) + "\n"


def test_add_command_shows_usage(tmp_path: Path):
    result = run_cli(tmp_path, "add")

    assert result.returncode == 0
    assert "Usage: polepos add <subcommand>" in result.stdout
    assert "integration" in result.stdout
    assert "module" in result.stdout


def test_add_help_shows_namespace_usage(tmp_path: Path):
    result = run_cli(tmp_path, "add", "--help")

    assert result.returncode == 0
    assert "Usage: polepos add <subcommand>" in result.stdout
    assert "Unknown command" not in result.stdout
    assert "integration" in result.stdout
    assert "module" in result.stdout


def test_add_module_help_shows_usage_without_project(tmp_path: Path):
    result = run_cli(tmp_path, "add", "module", "--help")

    assert result.returncode == 0
    assert "Usage: polepos add module <module_name>" in result.stdout
    assert "Templates:" in result.stdout


def test_add_module_rejects_template_flag_without_value(tmp_path: Path):
    result = run_cli(
        tmp_path, "add", "module", "garage", "--template", "--api-only"
    )

    assert result.returncode != 0
    assert "Missing value for --template." in result.stdout
    assert "Unsupported module template '--api-only'" not in result.stdout


def test_add_module_rejects_empty_template_value(tmp_path: Path):
    result = run_cli(tmp_path, "add", "module", "garage", "--template=")

    assert result.returncode != 0
    assert "Missing value for --template." in result.stdout


def test_add_module_rejects_crud_feature_without_crud_template(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "module", "customers", "--pagination")

    assert result.returncode != 0
    assert "CRUD feature options require `--template crud`" in result.stdout
    assert "--pagination" in result.stdout


def test_add_integration_help_shows_usage_without_project(tmp_path: Path):
    result = run_cli(tmp_path, "add", "integration", "--help")

    assert result.returncode == 0
    assert "Usage: polepos add integration <integration_name>" in result.stdout
    assert "Integrations: kafka, rabbitmq, redis, rq" in result.stdout


def test_add_kafka_integration_creates_files_and_updates_project(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode == 0
    assert "Added integration: kafka" in result.stdout
    assert "Created:" in result.stdout
    assert "src/myapp/integrations/kafka/producer.py" in result.stdout
    assert "Updated:" in result.stdout
    assert "src/myapp/settings.py" in result.stdout
    assert ".env.example" in result.stdout
    assert "pyproject.toml" in result.stdout
    assert ".poleposition.toml" in result.stdout
    assert "Next steps:" in result.stdout
    assert "Run `uv sync --extra dev`" in result.stdout

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
        assert path.exists(), (
            f"Expected generated Kafka file is missing: {path}"
        )

    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    pyproject_content = (project_root / "pyproject.toml").read_text(
        encoding="utf-8"
    )
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


def test_add_kafka_integration_keeps_existing_upgraded_dependency(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '    "pydantic-settings>=2.0.0",\n',
            '    "pydantic-settings>=2.0.0",\n    "aiokafka>=0.13.0",\n',
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode == 0
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    assert '"aiokafka>=0.13.0",' in pyproject_content
    assert '"aiokafka>=0.12.0",' not in pyproject_content
    assert pyproject_content.count("aiokafka") == 1


def test_add_kafka_integration_completes_partial_settings_and_env(
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
            '    kafka_bootstrap_servers: str = "localhost:9092"\n'
            "    # polepos:integration-settings",
        ),
        encoding="utf-8",
    )
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "# polepos:integration-env",
            "KAFKA_BOOTSTRAP_SERVERS=localhost:9092\n# polepos:integration-env",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode == 0
    settings_content = settings_path.read_text(encoding="utf-8")
    env_content = env_path.read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")

    assert settings_content.count("kafka_bootstrap_servers:") == 1
    assert "kafka_client_id: str" in settings_content
    assert "kafka_request_timeout_ms: int = 40000" in settings_content
    assert env_content.count("KAFKA_BOOTSTRAP_SERVERS=") == 1
    assert "KAFKA_CLIENT_ID=myapp" in env_content
    assert "KAFKA_REQUEST_TIMEOUT_MS=40000" in env_content
    assert "kafka = true" in manifest


def test_add_kafka_integration_does_not_treat_commented_required_env_as_present(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    env_path = project_root / ".env.example"
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "# polepos:integration-env",
            "# KAFKA_BOOTSTRAP_SERVERS=localhost:9092\n"
            "# polepos:integration-env",
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode == 0
    env_lines = env_path.read_text(encoding="utf-8").splitlines()
    assert env_lines.count("KAFKA_BOOTSTRAP_SERVERS=localhost:9092") == 1
    assert env_lines.count("# KAFKA_BOOTSTRAP_SERVERS=localhost:9092") == 1
    assert env_lines.count("# KAFKA_COMPRESSION_TYPE=") == 1


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
    assert (
        "Cannot add integration because the project layout is not ready"
        in result.stdout
    )
    assert (
        "Required managed marker '    # polepos:integration-settings' is "
        "missing" in result.stdout
    )
    assert (
        "Required managed marker '# polepos:integration-env' is missing"
        in result.stdout
    )
    assert not (package_root / "integrations" / "kafka").exists()
    assert "kafka_bootstrap_servers:" not in settings_path.read_text(
        encoding="utf-8"
    )
    assert "KAFKA_BOOTSTRAP_SERVERS=" not in env_path.read_text(
        encoding="utf-8"
    )
    assert '"aiokafka>=0.12.0",' not in (
        project_root / "pyproject.toml"
    ).read_text(encoding="utf-8")


def test_add_integration_preflight_fails_when_settings_is_non_utf8(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode != 0
    assert (
        "Cannot add integration because the project layout is not ready"
        in result.stdout
    )
    assert (
        "Could not read managed text file for integration add" in result.stdout
    )
    assert "settings.py" in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr
    assert not (package_root / "integrations" / "kafka").exists()
    assert '"aiokafka>=0.12.0",' not in (
        project_root / "pyproject.toml"
    ).read_text(encoding="utf-8")


def test_add_integration_preflight_fails_when_manifest_is_non_utf8(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode != 0
    assert (
        "Cannot add integration because the project layout is not ready"
        in result.stdout
    )
    assert "Could not read project manifest as UTF-8" in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr
    assert not (package_root / "integrations" / "kafka").exists()
    assert manifest_path.read_bytes() == b"\xff\xfe\x00"


def test_add_integration_preflight_fails_when_dependency_layout_is_unsupported(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    env_path = project_root / ".env.example"
    pyproject_path = project_root / "pyproject.toml"
    pyproject_path.write_text(
        _remove_first_dependencies_array(
            pyproject_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "integration", "kafka")

    assert result.returncode != 0
    assert (
        "Cannot add integration because the project layout is not ready"
        in result.stdout
    )
    assert "Unsupported dependency layout" in result.stdout
    assert not (package_root / "integrations" / "kafka").exists()
    assert "kafka_bootstrap_servers:" not in settings_path.read_text(
        encoding="utf-8"
    )
    assert "KAFKA_BOOTSTRAP_SERVERS=" not in env_path.read_text(
        encoding="utf-8"
    )
    assert '"aiokafka>=0.12.0",' not in pyproject_path.read_text(
        encoding="utf-8"
    )


def test_add_rabbitmq_integration_creates_files_and_updates_project(
    tmp_path: Path,
):
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
        assert path.exists(), (
            f"Expected generated RabbitMQ file is missing: {path}"
        )

    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    pyproject_content = (project_root / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    publisher_content = (rabbitmq_root / "publisher.py").read_text(
        encoding="utf-8"
    )
    factory_content = (rabbitmq_root / "factory.py").read_text(encoding="utf-8")
    testing_content = (rabbitmq_root / "testing.py").read_text(encoding="utf-8")

    assert (
        'rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"'
        in settings_content
    )
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


def test_add_redis_integration_creates_files_and_updates_project(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "redis")

    assert result.returncode == 0
    assert "Added integration: redis" in result.stdout

    package_root = project_root / "src" / "myapp"
    redis_root = package_root / "integrations" / "redis"
    expected_files = [
        package_root / "integrations" / "__init__.py",
        redis_root / "__init__.py",
        redis_root / "cache.py",
        redis_root / "factory.py",
        redis_root / "schemas.py",
        redis_root / "testing.py",
    ]
    for path in expected_files:
        assert path.exists(), (
            f"Expected generated Redis file is missing: {path}"
        )

    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    pyproject_content = (project_root / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    cache_content = (redis_root / "cache.py").read_text(encoding="utf-8")
    factory_content = (redis_root / "factory.py").read_text(encoding="utf-8")
    testing_content = (redis_root / "testing.py").read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")

    assert 'redis_url: str = "redis://localhost:6379/0"' in settings_content
    assert 'redis_client_name: str = "myapp"' in settings_content
    assert 'redis_key_prefix: str = "myapp"' in settings_content
    assert "REDIS_URL=redis://localhost:6379/0" in env_content
    assert "REDIS_CLIENT_NAME=myapp" in env_content
    assert '"redis>=5.0.0",' in pyproject_content
    assert "class RedisCache:" in cache_content
    assert "from redis.asyncio import from_url" in factory_content
    assert "class InMemoryRedisClient:" in testing_content
    assert "redis = true" in manifest
    assert "{{" not in cache_content
    assert "{{" not in factory_content


def test_add_redis_integration_rejects_duplicate(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "integration", "redis")
    second_result = run_cli(project_root, "add", "integration", "redis")

    assert first_result.returncode == 0
    assert second_result.returncode != 0
    assert "Integration already exists: redis" in second_result.stdout


def test_add_rq_integration_creates_files_and_updates_project(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "rq")

    assert result.returncode == 0
    assert "Added integration: rq" in result.stdout

    package_root = project_root / "src" / "myapp"
    rq_root = package_root / "integrations" / "rq"
    expected_files = [
        package_root / "integrations" / "__init__.py",
        rq_root / "__init__.py",
        rq_root / "factory.py",
        rq_root / "jobs.py",
        rq_root / "schemas.py",
        rq_root / "testing.py",
        rq_root / "worker.py",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected generated RQ file is missing: {path}"

    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    pyproject_content = (project_root / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    factory_content = (rq_root / "factory.py").read_text(encoding="utf-8")
    jobs_content = (rq_root / "jobs.py").read_text(encoding="utf-8")
    testing_content = (rq_root / "testing.py").read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")

    assert 'rq_redis_url: str = "redis://localhost:6379/0"' in settings_content
    assert 'rq_default_queue: str = "myapp.default"' in settings_content
    assert 'rq_worker_name: str = "myapp-worker"' in settings_content
    assert "RQ_REDIS_URL=redis://localhost:6379/0" in env_content
    assert "RQ_DEFAULT_QUEUE=myapp.default" in env_content
    assert '"rq>=1.16.0",' in pyproject_content
    assert "from rq import Queue" in factory_content
    assert "def enqueue_job(" in jobs_content
    assert "class InMemoryRqQueue:" in testing_content
    assert "rq = true" in manifest
    assert "{{" not in factory_content
    assert "{{" not in jobs_content


def test_add_rq_integration_rejects_duplicate(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(project_root, "add", "integration", "rq")
    second_result = run_cli(project_root, "add", "integration", "rq")

    assert first_result.returncode == 0
    assert second_result.returncode != 0
    assert "Integration already exists: rq" in second_result.stdout


def test_add_messaging_integrations_can_coexist(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    kafka_result = run_cli(project_root, "add", "integration", "kafka")
    rabbitmq_result = run_cli(project_root, "add", "integration", "rabbitmq")
    redis_result = run_cli(project_root, "add", "integration", "redis")
    rq_result = run_cli(project_root, "add", "integration", "rq")

    assert kafka_result.returncode == 0
    assert rabbitmq_result.returncode == 0
    assert redis_result.returncode == 0
    assert rq_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    pyproject_content = (project_root / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    settings_lines = settings_content.splitlines()
    env_lines = env_content.splitlines()

    assert (package_root / "integrations" / "kafka" / "producer.py").exists()
    assert (
        package_root / "integrations" / "rabbitmq" / "publisher.py"
    ).exists()
    assert (package_root / "integrations" / "redis" / "cache.py").exists()
    assert (package_root / "integrations" / "rq" / "jobs.py").exists()
    assert pyproject_content.count('"aiokafka>=0.12.0",') == 1
    assert pyproject_content.count('"aio-pika>=9.0.0",') == 1
    assert pyproject_content.count('"redis>=5.0.0",') == 1
    assert pyproject_content.count('"rq>=1.16.0",') == 1
    assert (
        settings_lines.count(
            '    kafka_bootstrap_servers: str = "localhost:9092"'
        )
        == 1
    )
    assert (
        settings_lines.count(
            '    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"'
        )
        == 1
    )
    assert (
        settings_lines.count('    redis_url: str = "redis://localhost:6379/0"')
        == 1
    )
    assert (
        settings_lines.count(
            '    rq_redis_url: str = "redis://localhost:6379/0"'
        )
        == 1
    )
    assert env_lines.count("KAFKA_BOOTSTRAP_SERVERS=localhost:9092") == 1
    assert (
        env_lines.count("RABBITMQ_URL=amqp://guest:guest@localhost:5672/") == 1
    )
    assert env_lines.count("REDIS_URL=redis://localhost:6379/0") == 1
    assert env_lines.count("RQ_REDIS_URL=redis://localhost:6379/0") == 1


def test_add_integration_rejects_unknown_integration(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(project_root, "add", "integration", "elasticsearch")

    assert result.returncode != 0
    assert "Unsupported integration 'elasticsearch'" in result.stdout
    assert "Integrations: kafka, rabbitmq, redis, rq" in result.stdout


def test_module_templates_render_without_leftover_placeholders() -> None:
    from pole_position.cli.services.module_templates import (
        CrudFeatureSet,
        build_module_template,
        llm_integration_files,
    )

    standard_template = build_module_template(
        template="standard",
        package_name="myapp",
        module_name="garage",
    )
    crud_template = build_module_template(
        template="crud",
        package_name="myapp",
        module_name="customers",
    )
    feature_crud_template = build_module_template(
        template="crud",
        package_name="myapp",
        module_name="accounts",
        crud_features=CrudFeatureSet(
            pagination=True,
            timestamps=True,
            soft_delete=True,
            tenant_scoped=True,
            auth_required=True,
        ),
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
        *crud_template.files.values(),
        crud_template.integration_test_content,
        crud_template.unit_test_content,
        *feature_crud_template.files.values(),
        feature_crud_template.integration_test_content,
        feature_crud_template.unit_test_content,
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
    assert ".poleposition.toml" in result.stdout
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
        module_root / "services" / "__init__.py",
        module_root / "services" / "garage_service.py",
        project_root / "tests" / "integration" / "test_garage.py",
        project_root / "tests" / "unit" / "test_garage_service.py",
    ]
    for path in expected_files:
        assert path.exists(), (
            f"Expected generated module file is missing: {path}"
        )

    assert not (module_root / "service.py").exists()

    router_content = (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )
    db_models_content = (package_root / "db" / "models.py").read_text(
        encoding="utf-8"
    )
    modules_init_content = (package_root / "modules" / "__init__.py").read_text(
        encoding="utf-8"
    )
    integration_test_content = (
        project_root / "tests" / "integration" / "test_garage.py"
    ).read_text(encoding="utf-8")
    service_content = (
        module_root / "services" / "garage_service.py"
    ).read_text(encoding="utf-8")

    assert (
        "from myapp.modules.garage.router import router as garage_router"
        in router_content
    )
    assert (
        'api_router.include_router(garage_router, prefix="/garage", '
        'tags=["garage"])' in router_content
    )
    assert router_content.splitlines()[0] == "from fastapi import APIRouter"
    assert "from myapp.modules.garage import model" in db_models_content
    assert '"garage"' in modules_init_content
    assert 'client.post("/api/v1/garage/"' in integration_test_content
    assert "from myapp.bootstrap.logging import get_logger" in service_content
    assert "logger = get_logger(__name__)" in service_content


def test_add_module_with_crud_template_creates_full_crud_module(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root, "add", "module", "customers", "--template", "crud"
    )

    assert result.returncode == 0
    assert "Added module: customers" in result.stdout
    assert "Template: crud" in result.stdout

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "customers"
    expected_files = [
        module_root / "__init__.py",
        module_root / "model.py",
        module_root / "repository.py",
        module_root / "router.py",
        module_root / "schemas.py",
        module_root / "services" / "__init__.py",
        module_root / "services" / "customers_crud_service.py",
        project_root / "tests" / "integration" / "test_customers_crud.py",
        project_root / "tests" / "unit" / "test_customers_crud_service.py",
    ]
    for path in expected_files:
        assert path.exists(), (
            f"Expected generated CRUD module file is missing: {path}"
        )

    router_content = (module_root / "router.py").read_text(encoding="utf-8")
    service_content = (
        module_root / "services" / "customers_crud_service.py"
    ).read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")

    assert '@router.get("/{item_id}"' in router_content
    assert '@router.patch("/{item_id}"' in router_content
    assert '@router.delete("/{item_id}"' in router_content
    assert (
        "from myapp.domain.exceptions import NotFoundError" in service_content
    )
    assert "def delete_customers" in service_content
    assert 'customers = "crud"' in manifest


def test_add_module_with_crud_feature_options(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root,
        "add",
        "module",
        "customers",
        "--template",
        "crud",
        "--pagination",
        "--timestamps",
        "--soft-delete",
        "--tenant-scoped",
        "--auth-required",
    )

    assert result.returncode == 0
    assert "Template: crud" in result.stdout
    assert (
        "Features: pagination, timestamps, soft-delete, tenant-scoped, "
        "auth-required" in result.stdout
    )

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "customers"
    model_content = (module_root / "model.py").read_text(encoding="utf-8")
    schemas_content = (module_root / "schemas.py").read_text(encoding="utf-8")
    repository_content = (module_root / "repository.py").read_text(
        encoding="utf-8"
    )
    router_content = (module_root / "router.py").read_text(encoding="utf-8")
    integration_test_content = (
        project_root / "tests" / "integration" / "test_customers_crud.py"
    ).read_text(encoding="utf-8")
    manifest = (project_root / ".poleposition.toml").read_text(encoding="utf-8")

    assert "tenant_id: Mapped[str]" in model_content
    assert "created_at: Mapped[datetime]" in model_content
    assert "deleted_at: Mapped[datetime | None]" in model_content
    assert "class CustomersPage(BaseModel)" in schemas_content
    assert (
        "statement = statement.offset(offset).limit(limit)"
        in repository_content
    )
    assert "item.deleted_at = utc_now()" in repository_content
    assert (
        "APIRouter(dependencies=[Depends(get_current_user)])" in router_content
    )
    assert "tenant_id: str = Query(..., min_length=1)" in router_content
    assert "headers=_auth_headers()" in integration_test_content
    assert (
        'customers = "crud[pagination,timestamps,soft-delete,tenant-scoped,'
        'auth-required]"'
    ) in manifest

    _assert_python_files_compile(project_root)

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0


def test_added_module_templates_keep_project_python_files_compileable(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    standard_result = run_cli(project_root, "add", "module", "garage")
    crud_result = run_cli(
        project_root,
        "add",
        "module",
        "customers",
        "--template",
        "crud",
    )
    ai_result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
    )
    api_only_result = run_cli(
        project_root,
        "add",
        "module",
        "webhooks",
        "--api-only",
    )

    assert standard_result.returncode == 0
    assert crud_result.returncode == 0
    assert ai_result.returncode == 0
    assert api_only_result.returncode == 0
    _assert_python_files_compile(project_root)


def test_add_module_keeps_router_imports_sorted(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"

    first_result = run_cli(project_root, "add", "module", "zebra")
    second_result = run_cli(project_root, "add", "module", "alpha")

    assert first_result.returncode == 0
    assert second_result.returncode == 0

    router_lines = (
        (project_root / "src" / "myapp" / "api" / "router.py")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    import_lines = [line for line in router_lines if line.startswith("from ")]

    assert import_lines == sorted(import_lines)


def test_add_module_preserves_multiline_import_blocks(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    models_path = package_root / "db" / "models.py"

    router_path.write_text(
        router_path.read_text(encoding="utf-8").replace(
            "from myapp.modules.status.router import router as status_router\n",
            (
                "from myapp.modules.status.router import router as "
                "status_router\n"
                "from myapp.modules.status.schemas import (\n"
                "    StatusResponse,\n"
                ")\n"
            ),
        ),
        encoding="utf-8",
    )
    models_path.write_text(
        models_path.read_text(encoding="utf-8").replace(
            "    # polepos:model-imports",
            (
                "    from myapp.modules.status.schemas import (\n"
                "        StatusResponse,\n"
                "    )\n"
                "    # polepos:model-imports"
            ),
        ),
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "module", "customers")

    assert result.returncode == 0
    _assert_python_files_compile(project_root)

    router_content = router_path.read_text(encoding="utf-8")
    models_content = models_path.read_text(encoding="utf-8")
    assert "from myapp.modules.status.schemas import (" in router_content
    assert "    StatusResponse," in router_content
    assert (
        "from myapp.modules.customers.router import router as customers_router"
        in router_content
    )
    assert "from myapp.modules.status.schemas import (" in models_content
    assert "        StatusResponse," in models_content
    assert (
        "from myapp.modules.customers import model  # noqa: F401"
        in models_content
    )


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


def test_add_module_in_database_free_project_requires_api_only(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp", "--db", "none")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    standard_result = run_cli(project_root, "add", "module", "garage")
    api_only_result = run_cli(
        project_root, "add", "module", "webhooks", "--api-only"
    )

    assert standard_result.returncode != 0
    assert (
        "Database-backed module templates require generated db/ wiring"
        in standard_result.stdout
    )
    assert (
        "Use `polepos add module <name> --api-only`" in standard_result.stdout
    )
    assert api_only_result.returncode == 0
    assert (
        project_root / "src" / "myapp" / "modules" / "webhooks" / "router.py"
    ).exists()
    assert not (project_root / "src" / "myapp" / "db").exists()


def test_add_module_works_from_nested_directory(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    nested_dir = tmp_path / "myapp" / "src" / "myapp"
    result = run_cli(nested_dir, "add", "module", "garage")

    assert result.returncode == 0
    assert (
        tmp_path
        / "myapp"
        / "src"
        / "myapp"
        / "modules"
        / "garage"
        / "router.py"
    ).exists()


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
    modules_init_content = modules_init_path.read_text(
        encoding="utf-8"
    ).replace(
        "    # polepos:module-exports",
        "    # custom exports note\n    # polepos:module-exports",
    )
    modules_init_path.write_text(modules_init_content, encoding="utf-8")

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode == 0

    router_content = router_path.read_text(encoding="utf-8")
    models_content = models_path.read_text(encoding="utf-8")
    modules_init_content = modules_init_path.read_text(encoding="utf-8")

    assert (
        "from myapp.modules.garage.router import router as garage_router"
        in router_content
    )
    assert (
        'api_router.include_router(garage_router, prefix="/garage", '
        'tags=["garage"])' in router_content
    )
    assert "# custom import note" in router_content
    assert "# custom include note" in router_content
    assert (
        "from myapp.modules.garage import model  # noqa: F401" in models_content
    )
    assert "# custom model note" in models_content
    assert '"garage"' in modules_init_content
    assert "# custom exports note" in modules_init_content


def test_add_module_preflight_fails_before_writing_when_marker_is_missing(
    tmp_path: Path,
):
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
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert (
        "Required managed marker '    # polepos:model-imports' is missing"
        in result.stdout
    )
    assert "db/models.py" in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()
    assert not (
        project_root / "tests" / "unit" / "test_garage_service.py"
    ).exists()


def test_add_module_preflight_fails_before_writing_when_manifest_is_non_utf8(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    manifest_path = project_root / ".poleposition.toml"
    manifest_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert "Could not read project manifest as UTF-8" in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr
    assert not (package_root / "modules" / "garage").exists()
    assert manifest_path.read_bytes() == b"\xff\xfe\x00"


def test_add_module_preflight_fails_before_writing_when_router_is_invalid(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_path.write_text(
        router_path.read_text(encoding="utf-8") + "\ndef broken(:\n",
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert "Could not parse managed Python file for module add" in result.stdout
    assert "api/router.py" in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()


def test_add_module_preflight_fails_before_writing_when_router_is_non_utf8(
    tmp_path: Path,
) -> None:
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    router_path = package_root / "api" / "router.py"
    router_path.write_bytes(b"\xff\xfe\x00")

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert "Could not read managed text file for module add" in result.stdout
    assert "Could not read managed Python file for module add" in result.stdout
    assert "api/router.py" in result.stdout
    assert "UnicodeDecodeError" not in result.stdout
    assert "UnicodeDecodeError" not in result.stderr
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()


def test_add_module_preflight_fails_before_writing_when_modules_init_is_invalid(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    modules_init_path = package_root / "modules" / "__init__.py"
    modules_init_path.write_text(
        modules_init_path.read_text(encoding="utf-8") + "\ndef broken(:\n",
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert "Could not parse managed Python file for module add" in result.stdout
    assert "modules/__init__.py" in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()


def test_add_module_preflight_fails_before_writing_when_models_file_is_invalid(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    models_path = package_root / "db" / "models.py"
    models_path.write_text(
        models_path.read_text(encoding="utf-8") + "\ndef broken(:\n",
        encoding="utf-8",
    )

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert "Could not parse managed Python file for module add" in result.stdout
    assert "db/models.py" in result.stdout
    assert not (package_root / "modules" / "garage").exists()
    assert not (
        project_root / "tests" / "integration" / "test_garage.py"
    ).exists()


def test_add_ai_prompt_module_preflight_fails_when_settings_is_invalid(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    package_root = project_root / "src" / "myapp"
    settings_path = package_root / "settings.py"
    settings_path.write_text(
        settings_path.read_text(encoding="utf-8") + "\ndef broken(:\n",
        encoding="utf-8",
    )

    result = run_cli(
        project_root,
        "add",
        "module",
        "assistant",
        "--template",
        "ai-prompt",
    )

    assert result.returncode != 0
    assert (
        "Cannot add module because the project layout is not ready"
        in result.stdout
    )
    assert "Could not parse managed Python file for module add" in result.stdout
    assert "settings.py" in result.stdout
    assert not (package_root / "modules" / "assistant").exists()
    assert not (package_root / "integrations" / "llm").exists()
    assert not (
        project_root / "tests" / "integration" / "test_assistant.py"
    ).exists()


def test_add_module_rejects_stale_managed_wiring_before_readding(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    add_result = run_cli(project_root, "add", "module", "garage")
    assert add_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "garage"
    shutil.rmtree(module_root)
    (project_root / "tests" / "integration" / "test_garage.py").unlink()
    (project_root / "tests" / "unit" / "test_garage_service.py").unlink()

    result = run_cli(project_root, "add", "module", "garage")

    assert result.returncode != 0
    assert (
        "Managed references already exist for module 'garage'" in result.stdout
    )
    assert "polepos remove module garage" in result.stdout
    assert not module_root.exists()


def test_add_module_with_ai_prompt_template_creates_llm_module_files(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )

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
        module_root / "services" / "__init__.py",
        module_root / "services" / "assistant_service.py",
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
        assert path.exists(), (
            f"Expected generated AI module file is missing: {path}"
        )

    assert not (module_root / "service.py").exists()

    router_content = (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )
    db_models_content = (package_root / "db" / "models.py").read_text(
        encoding="utf-8"
    )
    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    service_content = (
        module_root / "services" / "assistant_service.py"
    ).read_text(encoding="utf-8")
    orchestrator_content = (module_root / "orchestrator.py").read_text(
        encoding="utf-8"
    )
    integration_test_content = (
        project_root / "tests" / "integration" / "test_assistant.py"
    ).read_text(encoding="utf-8")

    assert (
        'api_router.include_router(assistant_router, prefix="/assistant", '
        'tags=["assistant"])' in router_content
    )
    assert "from myapp.modules.assistant import model" not in db_models_content
    assert 'llm_provider: str = ""' in settings_content
    assert 'llm_model: str = ""' in settings_content
    assert "llm_timeout_seconds: float = 30.0" in settings_content
    assert "LLM_PROVIDER=" in env_content
    assert "LLM_MODEL=" in env_content
    assert "LLM_API_KEY=" in env_content
    assert "from myapp.bootstrap.logging import get_logger" in service_content
    assert "logger = get_logger(__name__)" in service_content
    assert (
        "from myapp.integrations.llm.factory import get_llm_provider"
        in orchestrator_content
    )
    assert "/api/v1/assistant/respond" in integration_test_content
    assert "return_value=StubProvider()" in integration_test_content
    assert 'assistant = "ai-prompt"' in (
        project_root / ".poleposition.toml"
    ).read_text(encoding="utf-8")
    assert "llm = true" in (project_root / ".poleposition.toml").read_text(
        encoding="utf-8"
    )


def test_add_module_ai_prompt_completes_partial_llm_settings_and_env(
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
            "    # polepos:llm-settings",
            '    llm_provider: str = "openai"\n    # polepos:llm-settings',
        ),
        encoding="utf-8",
    )
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "# polepos:llm-env",
            "LLM_PROVIDER=openai\n# polepos:llm-env",
        ),
        encoding="utf-8",
    )

    result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )

    assert result.returncode == 0
    settings_content = settings_path.read_text(encoding="utf-8")
    env_content = env_path.read_text(encoding="utf-8")

    assert settings_content.count("llm_provider:") == 1
    assert 'llm_model: str = ""' in settings_content
    assert "llm_timeout_seconds: float = 30.0" in settings_content
    assert env_content.count("LLM_PROVIDER=") == 1
    assert "LLM_MODEL=" in env_content
    assert "LLM_TIMEOUT_SECONDS=30" in env_content


def test_add_ai_prompt_module_ignores_commented_required_llm_env(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    env_path = project_root / ".env.example"
    env_path.write_text(
        env_path.read_text(encoding="utf-8").replace(
            "# polepos:llm-env",
            "# LLM_PROVIDER=openai\n# polepos:llm-env",
        ),
        encoding="utf-8",
    )

    result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )

    assert result.returncode == 0
    env_lines = env_path.read_text(encoding="utf-8").splitlines()
    assert env_lines.count("LLM_PROVIDER=") == 1
    assert env_lines.count("# LLM_PROVIDER=openai") == 1
    assert env_lines.count("# LLM_MAX_TOKENS=") == 1


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
        module_root / "services" / "__init__.py",
        module_root / "services" / "webhooks_service.py",
        project_root / "tests" / "integration" / "test_webhooks.py",
        project_root / "tests" / "unit" / "test_webhooks_api_service.py",
    ]
    for path in expected_files:
        assert path.exists(), (
            f"Expected generated API-only file is missing: {path}"
        )

    assert not (module_root / "model.py").exists()
    assert not (module_root / "repository.py").exists()
    assert not (module_root / "service.py").exists()

    router_content = (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )
    db_models_content = (package_root / "db" / "models.py").read_text(
        encoding="utf-8"
    )
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
    result = run_cli(
        project_root, "add", "module", "callbacks", "--template", "api-only"
    )

    assert result.returncode == 0
    assert "Template: api-only" in result.stdout
    assert (
        project_root / "src" / "myapp" / "modules" / "callbacks" / "router.py"
    ).exists()
    assert (
        project_root / "tests" / "unit" / "test_callbacks_api_service.py"
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
    assert (
        "--api-only cannot be combined with another module template."
        in result.stdout
    )


def test_add_module_ai_prompt_does_not_duplicate_llm_settings_or_integrations(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    first_result = run_cli(
        project_root, "add", "module", "assistant", "--template", "ai-prompt"
    )
    second_result = run_cli(
        project_root, "add", "module", "copilot", "--template", "ai-prompt"
    )

    assert first_result.returncode == 0
    assert second_result.returncode == 0

    package_root = project_root / "src" / "myapp"
    settings_content = (package_root / "settings.py").read_text(
        encoding="utf-8"
    )
    env_content = (project_root / ".env.example").read_text(encoding="utf-8")
    provider_content = (
        package_root / "integrations" / "llm" / "provider.py"
    ).read_text(encoding="utf-8")

    assert settings_content.count('llm_provider: str = ""') == 1
    assert env_content.count("LLM_PROVIDER=") == 1
    assert provider_content.count("class LLMProvider(Protocol):") == 1


def test_add_module_rejects_unknown_template(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root, "add", "module", "assistant", "--template", "unknown"
    )

    assert result.returncode != 0
    assert "Unsupported module template 'unknown'" in result.stdout
    assert (
        "Templates: standard, crud, ai-prompt, api-only, service-only"
        in result.stdout
    )


def test_add_module_with_service_only_option_creates_internal_module(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root, "add", "module", "notifications", "--service-only"
    )

    assert result.returncode == 0
    assert "Added module: notifications" in result.stdout
    assert "Template: service-only" in result.stdout
    # Service-only modules are database-backed, so the migration hint shows.
    assert "polepos db revision" in result.stdout

    package_root = project_root / "src" / "myapp"
    module_root = package_root / "modules" / "notifications"

    expected_files = [
        module_root / "__init__.py",
        module_root / "model.py",
        module_root / "repository.py",
        module_root / "services" / "__init__.py",
        module_root / "services" / "notifications_service.py",
        project_root / "tests" / "integration" / "test_notifications.py",
        project_root / "tests" / "unit" / "test_notifications_service_only.py",
    ]
    for path in expected_files:
        assert path.exists(), (
            f"Expected generated service-only file is missing: {path}"
        )

    # No HTTP layer is generated for an internal module.
    assert not (module_root / "router.py").exists()
    assert not (module_root / "schemas.py").exists()

    router_content = (package_root / "api" / "router.py").read_text(
        encoding="utf-8"
    )
    db_models_content = (package_root / "db" / "models.py").read_text(
        encoding="utf-8"
    )

    # The router is left untouched; the model is wired for db discovery.
    assert "notifications" not in router_content
    assert "from myapp.modules.notifications import model" in db_models_content

    _assert_python_files_compile(project_root)

    check_result = run_cli(project_root, "check")
    assert check_result.returncode == 0
    assert "passed" in check_result.stdout


def test_add_module_with_service_only_template_alias(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root,
        "add",
        "module",
        "events",
        "--template",
        "service-only",
    )

    assert result.returncode == 0
    assert "Template: service-only" in result.stdout
    module_root = project_root / "src" / "myapp" / "modules" / "events"
    assert (module_root / "services" / "events_service.py").exists()
    assert not (module_root / "router.py").exists()
    assert (
        project_root / "tests" / "unit" / "test_events_service_only.py"
    ).exists()


def test_add_module_rejects_service_only_with_other_template(tmp_path: Path):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root,
        "add",
        "module",
        "events",
        "--template",
        "crud",
        "--service-only",
    )

    assert result.returncode != 0
    assert (
        "--service-only cannot be combined with another module template."
        in result.stdout
    )


def test_add_module_rejects_api_only_and_service_only_together(
    tmp_path: Path,
):
    create_result = run_cli(tmp_path, "start", "myapp")
    assert create_result.returncode == 0

    project_root = tmp_path / "myapp"
    result = run_cli(
        project_root,
        "add",
        "module",
        "events",
        "--api-only",
        "--service-only",
    )

    assert result.returncode != 0
    assert (
        "Choose either --api-only or --service-only, not both." in result.stdout
    )
