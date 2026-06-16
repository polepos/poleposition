# Project Checks

This document explains `polepos check` for both human users and coding agents.

`polepos check` is the project contract validator for PolePosition-generated
FastAPI projects. It answers one practical question:

```text
Can this project still be grown safely with PolePosition lifecycle commands?
```

It does not connect to the database, start FastAPI, call Kafka, call RabbitMQ,
call Redis/RQ, or contact an LLM provider. It reads files and reports
structural drift.

## User Guide

Run the command from the project root or any nested directory inside a
PolePosition project:

```bash
polepos check
polepos check --json
polepos check --fix
```

Run it after:

- creating a project with `polepos start`
- adding a module with `polepos add module`
- removing a module with `polepos remove module`
- adding Kafka, RabbitMQ, Redis, or RQ with `polepos add integration ...`
- adding auth with `polepos add auth`
- manually editing `.poleposition.toml`, `api/router.py`, `db/models.py`,
  `modules/__init__.py`, `settings.py`, `.env.example`, or `pyproject.toml`
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
  - [PPCHK034] Lifecycle module 'garage' is missing API router include in ...
    Fix: Restore the router include, or clean the detached module with ...
```

For CI and coding-agent workflows, use `--json`:

```bash
polepos check --json
```

Successful JSON output looks like this:

```json
{
  "issues": [],
  "package_name": "myapp",
  "passed": true,
  "project_root": "/path/to/myapp"
}
```

Use `--fix` when only safe managed markers need restoration:

```bash
polepos check --fix
```

`--fix` restores missing PolePosition markers in managed files, then runs the
same checks again. It does not install packages, generate migrations, or call
external services. In `api/router.py`, it places the router include marker
after the complete `api_router.include_router(...)` statement, including
multi-line include calls, so later lifecycle commands can keep inserting new
router wiring safely.

If fixes are applied, text output lists the changed paths before the check
result:

```text
Applied fixes:
  src/myapp/api/router.py
PolePosition project check passed.
Project root: /path/to/myapp
Package: myapp
```

With `--json --fix`, the payload also includes `fixed`:

```json
{
  "fixed": ["src/myapp/api/router.py"],
  "issues": [],
  "package_name": "myapp",
  "passed": true,
  "project_root": "/path/to/myapp"
}
```

Failed JSON output keeps the same process exit behavior as the text output and
reports issues as structured objects:

```json
{
  "issues": [
    {
      "code": "PPCHK034",
      "message": "Lifecycle module 'garage' is missing API router include in ...",
      "remediation": "Restore the router include, or clean the detached module with ..."
    }
  ],
  "package_name": "myapp",
  "passed": false,
  "project_root": "/path/to/myapp"
}
```

The default command is intentionally diagnostic. It does not rewrite files,
install dependencies, create migrations, or apply fixes. The only mutating mode
is `--fix`, and it is limited to safe managed-marker restoration.

After `polepos remove module`, `check` can verify that generated router,
export, model-import, and test wiring no longer references the removed module.
It does not connect to the database and does not verify whether a removed
module's table still exists. Schema cleanup remains an Alembic migration
decision.

When `check` reports a removed module, it is reporting file drift, not runtime
state. The usual fix is to restore the missing module directory or run:

```bash
polepos remove module <name>
```

If the remaining reference is custom code, remove or rewire that reference
manually before rerunning `check`.

## Safe Customization Boundaries

PolePosition projects are normal FastAPI projects, so users can and should edit
their application code. The important boundary is the lifecycle contract used by
`polepos add module`, `polepos remove module`, `polepos add integration ...`,
`polepos db ...`, and `polepos check`.

Safe customization examples:

- edit generated module `model.py`, `schemas.py`, `repository.py`,
  `services/<module>_service.py`, and `router.py` for the real domain
- add new route handlers inside an existing module router
- add custom helper modules under `src/<package>/`
- add reviewed Alembic revisions under `migrations/versions/`
- change runtime values in `.env`
- add application tests under `tests/`

Avoid these changes unless the team intentionally opts out of PolePosition
lifecycle management for that file:

- removing or renaming `# polepos:*` managed marker comments
- manually rewriting managed imports, router includes, model imports, or module
  exports into a shape the CLI cannot recognize
- deleting a generated module directory or generated tests by hand and leaving
  router, model, export, or test references behind
- moving or renaming generated core files such as `api/router.py`,
  `db/models.py`, `settings.py`, `.env.example`, `.poleposition.toml`, or
  Alembic files
- adding a SQLAlchemy model without importing it through `db/models.py`
- creating tables during FastAPI startup instead of using Alembic migrations
- partially adding integration settings or `.env.example` values by hand while
  relying on `polepos add integration ...` or `polepos check` to manage the same
  integration later
- commenting out required generated integration values such as
  `KAFKA_BOOTSTRAP_SERVERS` or `LLM_PROVIDER` while expecting `check` to treat
  them as present
- editing `.env.example` as a secret store; put local secrets in `.env`

Generated module schema classes and fields are normal application code. You can
rename or replace them, but update the router, service, repository, generated
tests, and any custom imports at the same time. `polepos check` does not try to
enforce every generated Pydantic class name or every generated field because
those are expected to become domain-specific quickly. For example, if a
`customers` module changes `CustomerCreate` to `CreateCustomerRequest`, update
all imports and type annotations that reference `CustomerCreate`.

Do not delete generated schema classes or generated fields in isolation while
leaving generated router, service, or tests unchanged. In that case pytest is
the right validation layer: import errors, FastAPI `response_model` errors,
`payload.name` attribute errors, and response shape assertion failures are
runtime/test-contract issues rather than lifecycle wiring issues.

If a module was already deleted manually, run
`polepos remove module <name>` before making more structural edits. The command
can clean generated wiring and tests that still reference the missing module.

After any structural customization, run:

```bash
polepos check
```

After schema, service, router, repository, or model customization, also run the
generated pytest suite:

```bash
uv run pytest
```

## What It Checks

`polepos check` currently has three layers.

### 1. Core Check

Core check validates the generated project foundation:

- project identity
- `.poleposition.toml` package and database mode metadata when present
- generated project structure
- Alembic migration files for database-backed projects
- PolePosition-managed markers

Project identity means the command can find one generated application package
under `src/` and can report missing core paths instead of simply saying the
directory is unknown.

Core generated paths include the package entrypoints, settings, bootstrap
files, API files, domain files, the `status` starter module, test conftest,
the generated `status` integration test, README, `AGENTS.md`, and
`.env.example`. Database-backed projects also include generated `db/` files.

Alembic paths are checked only when the project has generated database wiring.
They include:

- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions`

Projects generated with `polepos start --db none` intentionally omit
SQLAlchemy, Alembic, `DATABASE_URL`, and generated `db/` paths. `polepos check`
accepts that shape and skips database-specific structure checks.

New generated projects include `.poleposition.toml`. The file records the
application package, database mode, generated modules, and generated
integrations. Older projects without the file still work through structural
inference. Integration values must use TOML booleans such as `kafka = true` or
`kafka = false`; quoted strings such as `kafka = "false"` are reported as
invalid manifest values instead of being treated as generated integration
signals. CRUD module options are recorded on the module template value, such as
`customers = "crud[pagination,timestamps,soft-delete]"`, so lifecycle commands
can compare generated files against the right template variant. If the manifest
cannot be decoded as UTF-8, `check` reports it as manifest drift and lifecycle
commands leave it untouched instead of overwriting a corrupt file. If a project
intentionally uses a user-managed database workflow
outside PolePosition's SQLAlchemy/Alembic lifecycle, set:

```toml
[poleposition]
db = "custom"
```

`custom` tells `check` not to infer the standard Alembic lifecycle from custom
database settings or dependencies.

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

Generated managed files are expected to be UTF-8 text. If `check` cannot decode
a managed file, it reports that file as project drift instead of crashing with a
raw decode traceback. Restore the file as UTF-8 text, regenerate the affected
scaffold, or intentionally detach that managed surface.

### 2. Lifecycle Check

Lifecycle check validates modules added after project creation.

Starter modules are not treated as added modules:

- `status`

Projects generated by older PolePosition versions may still contain the legacy
`profile` and `races` sample modules. `check` treats those legacy sample
modules as starter modules when their original generated signals are present,
so upgraded CLI versions can still validate older generated projects.

Lifecycle check also validates that the starter `status` module remains wired
into `api/router.py` without an added router prefix, and reports orphan
generated references when a module directory was deleted manually but
router/model/export/test references remain. Python references are parsed from
the full managed file, so custom imports below PolePosition markers are still
reported when they point at a missing module.

For example, if `src/myapp/modules/garage/` is gone, all of these count as
orphan references:

```python
from myapp.modules.garage.router import router as garage_router
api_router.include_router(garage_router, prefix="/garage", tags=["garage"])
from myapp.modules.garage import model as garage_model
```

Generated wiring can usually be cleaned with:

```bash
polepos remove module garage
```

Custom references are not guessed away. If the project intentionally replaced
the generated router include or model import with a custom line, remove or
rewrite that custom line explicitly before expecting `check` to pass.

For a standard module, `check` expects:

- module files: `__init__.py`, `model.py`, `repository.py`, `router.py`,
  `schemas.py`, `services/__init__.py`, `services/<module>_service.py`
- export in `src/<package>/modules/__init__.py`
- router import in `src/<package>/api/router.py`
- router include in `src/<package>/api/router.py`
- model import in `src/<package>/db/models.py`
- integration test under `tests/integration/test_<module>.py`
- unit test under `tests/unit/test_<module>_service.py`

For a `crud` module, `check` expects the standard database-backed wiring plus:

- module service file: `services/<module>_crud_service.py`
- integration test under `tests/integration/test_<module>_crud.py`
- unit test under `tests/unit/test_<module>_crud_service.py`

CRUD feature options such as pagination, timestamps, soft delete, tenant scope,
and auth-required routes do not change the required file names, but the
manifest keeps the selected option list so other lifecycle commands can
recognize the generated content.

For an `ai-prompt` module, `check` expects:

- module files: `__init__.py`, `orchestrator.py`, `prompts.py`, `router.py`,
  `schemas.py`, `services/__init__.py`, `services/<module>_service.py`
- export in `src/<package>/modules/__init__.py`
- router import and include in `src/<package>/api/router.py`
- integration test under `tests/integration/test_<module>.py`
- unit test under `tests/unit/test_<module>_orchestrator.py`

`ai-prompt` modules are intentionally not required to have a model import in
`db/models.py`.

For an `api-only` module, `check` expects:

- module files: `__init__.py`, `router.py`, `schemas.py`,
  `services/__init__.py`, `services/<module>_service.py`
- export in `src/<package>/modules/__init__.py`
- router import and include in `src/<package>/api/router.py`
- integration test under `tests/integration/test_<module>.py`
- unit test under `tests/unit/test_<module>_api_service.py`

`api-only` modules are intentionally not required to have model, repository, or
`db/models.py` wiring.

### Auth Workflow Check

Auth workflow check validates projects that ran `polepos add auth` or otherwise
contain auth workflow signals. It expects:

- generated auth files such as `auth/model.py`, `auth/router.py`,
  `auth/user_schemas.py`, and `auth/user_service.py`
- generated tests under `tests/integration/test_auth.py` and
  `tests/unit/test_auth_service.py`
- dependency: `pwdlib[argon2]>=0.2.0`
- auth router import/include in `api/router.py`
- auth model import in `db/models.py`

The auth workflow requires generated database wiring. Projects created with
`--db none` must add an explicit database layer before using this workflow.

### 3. Integration Check

Integration check validates opt-in external-system scaffolds when the project
contains signals that those integrations are present. In projects with
`.poleposition.toml`, explicit manifest entries and file, dependency, setting,
or active env signals are both treated as integration signals. Commented
settings or env lines do not satisfy required integration values; generated
commented env examples such as optional Kafka compression or LLM token limits
are treated as optional examples.

The distinction is deliberate:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092   # required and active
# KAFKA_BOOTSTRAP_SERVERS=localhost:9092 # required but inactive, reported missing
# KAFKA_COMPRESSION_TYPE=                # optional example, allowed commented
```

The same rule applies to generated settings in `settings.py`:

```python
kafka_bootstrap_servers: str = "localhost:9092"  # present
# kafka_bootstrap_servers: str = "localhost:9092"  # commented out, missing
```

If a required env key was accidentally pre-seeded as a comment before running
`polepos add integration kafka`, the add command inserts an active generated
line instead of treating the comment as complete.

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
- optional commented env example: `KAFKA_COMPRESSION_TYPE`

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

Redis is checked when `integrations/redis`, Redis settings, Redis env values,
or the Redis dependency are present. `check` expects:

- `src/<package>/integrations/redis/__init__.py`
- `cache.py`
- `factory.py`
- `schemas.py`
- `testing.py`
- dependency: `redis>=5.0.0`
- settings such as `redis_url`, `redis_client_name`, and `redis_key_prefix`
- env values such as `REDIS_URL`, `REDIS_CLIENT_NAME`, and `REDIS_KEY_PREFIX`

RQ is checked when `integrations/rq`, RQ settings, RQ env values, or the RQ
dependency are present. `check` expects:

- `src/<package>/integrations/rq/__init__.py`
- `factory.py`
- `jobs.py`
- `schemas.py`
- `testing.py`
- `worker.py`
- dependency: `rq>=1.16.0`
- settings such as `rq_redis_url`, `rq_default_queue`, and
  `rq_job_timeout_seconds`
- env values such as `RQ_REDIS_URL`, `RQ_DEFAULT_QUEUE`, and
  `RQ_JOB_TIMEOUT_SECONDS`

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
- optional commented env example: `LLM_MAX_TOKENS`

LLM does not require a provider SDK dependency by default because the generated
adapters are provider-agnostic stubs.

## How To Read Issues

Each issue includes a stable code, the problem text, and a short remediation
hint:

```text
- [PPCHK021] Managed marker '# polepos:router-imports' is missing in ...
  Fix: Restore the listed # polepos marker or manage that file manually.
```

Issue text still names the layer by implication:

- `Required generated path is missing`: core generated structure drift
- `Required Alembic path is missing`: migration setup drift
- `Project manifest has unsupported ...`: invalid lifecycle manifest metadata
- `Managed marker ... is missing`: a managed insertion point was removed
- `Lifecycle module ...`: added module wiring drift
- `Orphan module reference ...`: generated remnants point at a missing module
- `Integration ...`: opt-in integration wiring drift

Issue codes are intended to stay stable enough for humans, coding agents, CI
logs, and future machine-readable output. The current code families are:

- `PPCHK00x`: project identity
- `PPCHK01x`: generated structure, Alembic, and database-mode drift
- `PPCHK02x`: managed file and marker drift
- `PPCHK03x`: module lifecycle drift
- `PPCHK04x`: integration drift

Fix the project by restoring the expected file, marker, import, dependency,
setting, or env value. If a team intentionally opts out of PolePosition-managed
updates for a file, treat the check failure as expected drift and document that
decision in the project.

## Agent And LLM Contract

Coding agents should treat `polepos check` as a lifecycle contract, not as a
style checker.

When changing generated structure, module generation, integration generation,
managed markers, or Alembic behavior:

- update `pole_position/cli/services/project_checker/`
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
