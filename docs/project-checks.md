# Project Checks

This document explains `polepos check` for both human users and coding agents.

`polepos check` is the project contract validator for PolePosition-generated
FastAPI projects. It answers one practical question:

```text
Can this project still be grown safely with PolePosition lifecycle commands?
```

It does not connect to the database, start FastAPI, call Kafka, call RabbitMQ,
or contact an LLM provider. It reads files and reports structural drift.

## User Guide

Run the command from the project root or any nested directory inside a
PolePosition project:

```bash
polepos check
```

Run it after:

- creating a project with `polepos start`
- adding a module with `polepos add module`
- adding Kafka or RabbitMQ with `polepos add integration ...`
- manually editing `api/router.py`, `db/models.py`, `modules/__init__.py`,
  `settings.py`, `.env.example`, or `pyproject.toml`
- resolving merge conflicts in generated or managed files
- before opening a pull request or handing a project to another agent

Successful output looks like this:

```text
PolePosition project check passed.
Project root: /path/to/myapp
Package: myapp
```

Failure output lists the project, package, and every issue found:

```text
PolePosition project check failed.
Project root: /path/to/myapp
Package: myapp
Issues:
  - Lifecycle module 'garage' is missing API router include in ...
```

The command is intentionally diagnostic. It does not rewrite files, install
dependencies, create migrations, or apply fixes.

## What It Checks

`polepos check` currently has three layers.

### 1. Core Check

Core check validates the generated project foundation:

- project identity
- generated project structure
- Alembic migration files
- PolePosition-managed markers

Project identity means the command can find one generated application package
under `src/` and can report missing core paths instead of simply saying the
directory is unknown.

Core generated paths include the package entrypoints, settings, bootstrap
files, API files, database files, domain files, starter modules, test
conftest, README, and `.env.example`.

Alembic paths include:

- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions`

Managed markers include:

- `# polepos:router-imports`
- `# polepos:router-includes`
- `# polepos:model-imports`
- `# polepos:module-exports`
- `# polepos:auth-settings`
- `# polepos:auth-env`
- `# polepos:integration-settings`
- `# polepos:integration-env`
- `# polepos:llm-settings`
- `# polepos:llm-env`

These markers are also used by lifecycle commands. If the integration settings
or env markers are removed, `polepos add integration ...` stops before writing
generated files so the project is not left partially patched.

### 2. Lifecycle Check

Lifecycle check validates modules added after project creation.

Starter modules are not treated as added modules:

- `profile`
- `races`
- `status`

For a standard module, `check` expects:

- module files: `__init__.py`, `model.py`, `repository.py`, `router.py`,
  `schemas.py`, `service.py`
- export in `src/<package>/modules/__init__.py`
- router import in `src/<package>/api/router.py`
- router include in `src/<package>/api/router.py`
- model import in `src/<package>/db/models.py`
- integration test under `tests/integration/test_<module>.py`
- unit test under `tests/unit/test_<module>_service.py`

For an `ai-prompt` module, `check` expects:

- module files: `__init__.py`, `orchestrator.py`, `prompts.py`, `router.py`,
  `schemas.py`, `service.py`
- export in `src/<package>/modules/__init__.py`
- router import and include in `src/<package>/api/router.py`
- integration test under `tests/integration/test_<module>.py`
- unit test under `tests/unit/test_<module>_orchestrator.py`

`ai-prompt` modules are intentionally not required to have a model import in
`db/models.py`.

For an `api-only` module, `check` expects:

- module files: `__init__.py`, `router.py`, `schemas.py`, `service.py`
- export in `src/<package>/modules/__init__.py`
- router import and include in `src/<package>/api/router.py`
- integration test under `tests/integration/test_<module>.py`
- unit test under `tests/unit/test_<module>_api_service.py`

`api-only` modules are intentionally not required to have model, repository, or
`db/models.py` wiring.

### 3. Integration Check

Integration check validates opt-in external-system scaffolds when the project
contains signals that those integrations are present.

Kafka is checked when `integrations/kafka`, Kafka settings, Kafka env values,
or the Kafka dependency are present. `check` expects:

- `src/<package>/integrations/kafka/__init__.py`
- `consumer.py`
- `factory.py`
- `producer.py`
- `schemas.py`
- `testing.py`
- dependency: `aiokafka>=0.12.0`
- settings such as `kafka_bootstrap_servers`, `kafka_client_id`, and
  `kafka_request_timeout_ms`
- env values such as `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_CLIENT_ID`, and
  `KAFKA_REQUEST_TIMEOUT_MS`

RabbitMQ is checked when `integrations/rabbitmq`, RabbitMQ settings, RabbitMQ
env values, or the RabbitMQ dependency are present. `check` expects:

- `src/<package>/integrations/rabbitmq/__init__.py`
- `consumer.py`
- `factory.py`
- `publisher.py`
- `schemas.py`
- `testing.py`
- dependency: `aio-pika>=9.0.0`
- settings such as `rabbitmq_url`, `rabbitmq_exchange`, and
  `rabbitmq_prefetch_count`
- env values such as `RABBITMQ_URL`, `RABBITMQ_EXCHANGE`, and
  `RABBITMQ_PREFETCH_COUNT`

LLM is checked when `integrations/llm`, LLM settings, LLM env values, or an
`ai-prompt` module are present. `check` expects:

- `src/<package>/integrations/llm/__init__.py`
- `anthropic_client.py`
- `factory.py`
- `openai_client.py`
- `provider.py`
- `schemas.py`
- settings such as `llm_provider`, `llm_model`, and `llm_api_key`
- env values such as `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY`

LLM does not require a provider SDK dependency by default because the generated
adapters are provider-agnostic stubs.

## How To Read Issues

Issue text names the layer by implication:

- `Required generated path is missing`: core generated structure drift
- `Required Alembic path is missing`: migration setup drift
- `Managed marker ... is missing`: a managed insertion point was removed
- `Lifecycle module ...`: added module wiring drift
- `Integration ...`: opt-in integration wiring drift

Fix the project by restoring the expected file, marker, import, dependency,
setting, or env value. If a team intentionally opts out of PolePosition-managed
updates for a file, treat the check failure as expected drift and document that
decision in the project.

## Agent And LLM Contract

Coding agents should treat `polepos check` as a lifecycle contract, not as a
style checker.

When changing generated structure, module generation, integration generation,
managed markers, or Alembic behavior:

- update `pole_position/cli/services/project_checker.py`
- update `pole_position/tests/test_check_command.py`
- update `pole_position/tests/test_project_checker.py` when helper behavior changes
- update this document
- update README when user-facing behavior changes

Do not make `check` depend on network access, a running database, a running
message broker, or installed optional integration dependencies. The check layer
should stay fast, file-based, deterministic, and safe to run in CI.

Do not use `check` to hide FastAPI behavior behind a framework. It should
validate PolePosition-managed project shape while keeping the generated app
explicit and understandable.
