# PolePosition Architecture

This document explains how PolePosition is structured as a product and as a codebase.

For a visual overview, see the [Architecture Diagram](architecture-diagram.md).

It is meant to help both humans and coding agents answer the same questions quickly:

- what the product does
- where CLI behavior lives
- where generated project behavior lives
- how `add module` safely updates files
- which parts are stable conventions versus evolving surfaces

## Product Shape

PolePosition is a project lifecycle CLI, not only a one-time scaffold tool or template repository.

Its value comes from connected lifecycle workflows:

1. `polepos start`
2. `polepos add module`
3. `polepos add integration ...`
4. `polepos check`
5. `polepos db ...`

That means the product helps at:

- project creation
- codebase growth
- project contract checks
- schema lifecycle management

Templates are a delivery mechanism for those workflows, not the product boundary.

The generated project should stay FastAPI-native while still giving teams opinionated structure and defaults.

## High-Level Flow

```text
User command
  -> CLI command handler
  -> service layer
  -> template copy/render and project patching
  -> generated FastAPI project
```

More concretely:

```text
polepos start myapp
  -> startproject.py
  -> project_creator.py
  -> template_renderer.py
  -> generated app under myapp/

polepos add module users
  -> commands/add/module.py
  -> module_creator.py
  -> module_templates/
  -> generated module files + managed updates

polepos add integration kafka
  -> commands/add/integration.py
  -> integration_creator.py
  -> generated integration files + managed settings/dependency updates

polepos add integration rabbitmq
  -> commands/add/integration.py
  -> integration_creator.py
  -> generated integration files + managed settings/dependency updates

polepos db upgrade
  -> commands/db/upgrade.py
  -> db_runner.py
  -> Alembic in generated project

polepos check
  -> commands/check.py
  -> project_checker.py
  -> core project diagnostics + added module lifecycle wiring + opt-in integration diagnostics
```

## CLI Map

Main entry:

```text
pole_position/cli/main.py
```

Important pieces:

- `command.py`: command model
- `registry.py`: command registry
- `commands/`: user-facing command handlers
- `services/`: reusable implementation logic

Current command groups:

- `start`
- `add module`
- `add integration`
- `check`
- `db upgrade`
- `db revision`
- `db downgrade`
- `help`
- `version`

## Template Map

The generated project template lives under:

```text
pole_position/template/
```

This folder is copied first, then rendered with placeholder replacement.

Main placeholders include:

- `{{project_name}}`
- `{{project_import_name}}`
- `{{no_bytecode_command_prefix}}`
- `{{no_bytecode_readme_note}}`

Rendering logic lives in:

```text
pole_position/cli/services/template_renderer.py
```

## Generated Project Shape

Generated apps use this layout:

```text
src/<package>/
  app.py
  main.py
  run.py
  settings.py
  auth/
  bootstrap/
  api/
  db/
  domain/
  integrations/
  modules/
```

The responsibilities are:

- `auth/`: endpoint authentication foundation
- `bootstrap/`: logging, middleware, lifespan, error wiring
- `api/`: API composition and shared dependencies
- `db/`: SQLAlchemy base, session, model import aggregation
- `domain/`: domain exceptions and shared primitives
- `integrations/`: external systems such as LLM adapters
- `modules/`: feature modules such as `status`, `profile`, `races`

## `add module` Architecture

`polepos add module` has two layers:

1. template selection
2. project patching

Template selection lives in:

```text
pole_position/cli/services/module_templates/
```

Current templates:

- `standard`
- `ai-prompt`
- `api-only`

Project patching lives in:

```text
pole_position/cli/services/module_creator.py
```

This file:

- writes module files
- writes generated tests
- updates shared registration points
- optionally adds LLM integration files
- optionally patches settings and `.env.example`

The `--api-only` CLI option is a shortcut for the `api-only` template. It
generates router, schemas, service, and tests without model, repository, or
database model wiring.

## `add integration` Architecture

`polepos add integration ...` grows an existing project with external system
helpers while keeping the base template lean.

Current integrations:

- `kafka`
- `rabbitmq`

Messaging support is intentionally opt-in. Kafka writes `integrations/kafka`
helpers and adds `aiokafka`; RabbitMQ writes `integrations/rabbitmq` helpers
and adds `aio-pika`. Both integrations patch settings and `.env.example`
values. Consumer loops are left as explicit worker/runtime code instead of
being started inside the FastAPI app process.

## `check` Architecture

`polepos check` is the lifecycle contract validator. It keeps project
diagnostics separate from project mutation: it reads generated files and reports
drift, but it does not patch files, install packages, connect to databases, or
start external services.

Implementation lives in:

```text
pole_position/cli/services/project_checker.py
```

The command handler lives in:

```text
pole_position/cli/commands/check.py
```

Current check layers:

- core checks: project identity, generated structure, Alembic config, and managed markers
- lifecycle checks: added module files, exports, router wiring, model wiring, and generated tests
- integration checks: Kafka, RabbitMQ, and LLM files, dependencies, settings keys, and env keys

Core-only behavior is kept available through `check_core_project()` so future
CLI modes can reuse the foundation without lifecycle or integration checks.
The public `check_project()` path runs the full current contract.

For the detailed user guide and agent-facing contract, see:

```text
docs/project-checks.md
```

## Managed Block Contract

`add module` depends on marker comments in generated files.

Current managed markers include:

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

These markers define PolePosition-managed regions.

Meaning:

- PolePosition may insert generated lines before these markers
- users may add surrounding code and comments
- users should not remove these markers unless they intend to manage those files manually

The most important managed files are:

- `src/<package>/api/router.py`
- `src/<package>/db/models.py`
- `src/<package>/modules/__init__.py`
- `src/<package>/settings.py`
- `.env.example`

If these markers are removed or rearranged incorrectly, `polepos add module` or
`polepos add integration ...` may fail or stop updating the file automatically.

## Database Lifecycle

PolePosition is migration-first.

Generated projects include:

- Alembic
- SQLAlchemy
- `db/models.py` as the import aggregation point

This means:

- schema changes should go through Alembic
- app startup should not recreate schema ad hoc
- new database-backed modules must be wired into `db/models.py`

The main lifecycle is:

```text
polepos start
-> edit models
-> polepos db revision -m "..."
-> polepos db upgrade
```

## Authentication Boundary

Generated projects now include a JWT-based authentication foundation.

The important separation is:

- authentication: who is calling?
- authorization: what can this user access?

The generated example endpoints show this difference:

- `GET /api/v1/status` is public
- `GET /api/v1/profile/me` is authenticated
- `GET /api/v1/profile/admin-preview` is role-gated

This is meant as a reusable route-boundary pattern, not a full identity system yet.

## Logging Boundary

Generated projects support:

- `LOG_FORMAT=text`
- `LOG_FORMAT=json`

Logging is configured centrally in:

```text
src/<package>/bootstrap/logging.py
```

The generated logging contract is:

- `get_logger(__name__)` is the preferred entrypoint
- text logs are good for development
- JSON logs are good for production pipelines

## Examples Map

Concrete scenario guides live under:

```text
examples/
```

Current examples:

- `examples/auth-foundation/`
- `examples/html-swap/`

Use these when you want to understand how the generated project should be reshaped for a real use case instead of reading only the raw template files.

## How To Read This Repo Efficiently

If you are new to the repository, the shortest reliable reading path is:

1. `README.md`
2. `AGENTS.md`
3. this file
4. `pole_position/cli/main.py`
5. `pole_position/cli/commands/`
6. `pole_position/cli/services/`
7. `pole_position/template/`
8. `pole_position/tests/`
9. `examples/`

This order helps because it moves from product intent to command flow to generated runtime behavior.
