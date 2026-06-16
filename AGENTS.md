# AGENTS

This file is for coding agents working in this repository.

If you are an agent, read this file before making changes.
Use it as the default operating guide for understanding product intent, preferred workflows, and repo conventions.

Read these companion docs when you need deeper repo context:

- `docs/architecture.md`
- `docs/feature-status.md`
- `docs/project-checks.md`
- `examples/README.md`

## What PolePosition Is

PolePosition is a CLI for starting enterprise FastAPI projects from pole position.

Its purpose is not only to scaffold a new project once, but to help teams keep a consistent development flow as the project grows.

Today that flow is centered around:

- `polepos start` for creating a project
- `polepos add module` for growing the codebase
- `polepos add auth` for adding the optional database-backed auth workflow
- `polepos remove module` for removing generated module scaffolds
- `polepos add integration ...` for opt-in external-system scaffolds
- `polepos check` for validating the project lifecycle contract
- `polepos db ...` for managing Alembic migration workflows

When in doubt, optimize for this product idea:

PolePosition should help teams keep FastAPI's speed while reducing the setup and maintenance overhead of enterprise backend work.

## Read This Before Changing Product Behavior

Prefer these product principles:

- Keep the generated project FastAPI-native.
- Prefer explicit structure over heavy framework magic.
- Prefer module-oriented organization over large flat technical layers.
- Prefer `uv`-first workflows for install, sync, run, and local developer operations.
- Prefer migration-first database workflows over startup-time schema creation.

Avoid these regressions:

- Do not reintroduce `Base.metadata.create_all()` in generated app startup code.
- Do not turn the generated project into a framework that hides FastAPI too much.
- Do not make `add module` output depend on hidden global state.
- Do not silently bypass Alembic by introducing ad hoc schema creation paths.

## Preferred User Workflow

Assume the intended user flow looks like this:

1. Create a project

```bash
polepos start shop-api
cd shop-api
cp .env.example .env
uv sync
polepos db upgrade
uv run python -m shop_api.run
```

2. Add a new domain module

```bash
polepos add module customers
```

3. Refine the generated module for the real domain

- update `model.py`
- update `schemas.py`
- update `services/<module>_service.py`
- update `router.py` if needed

4. Validate the project contract

```bash
polepos check
```

5. Create and apply a migration

```bash
polepos db revision -m "add customers table"
polepos db upgrade
```

Agents should preserve and improve this flow, not fight it.

## Generated Project Conventions

The generated app currently follows this structure:

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

Important meanings:

- `bootstrap/`: app-wide wiring such as logging, middleware, lifespan, and exception handling
- `api/`: API composition and shared dependencies
- `db/`: SQLAlchemy base, session, model import registry
- `domain/`: shared domain exceptions and similar cross-module domain primitives
- `integrations/`: opt-in external-system adapters such as LLM, Kafka, or RabbitMQ helpers
- `modules/`: feature/domain modules such as `status`, `users`, `customers`

Agents should prefer adding behavior inside modules instead of creating large global folders like `services/` or `repositories/` at the project root.

## Logging Conventions

Generated projects should prefer:

```python
from <package>.bootstrap.logging import get_logger

logger = get_logger(__name__)
```

over repeating raw `import logging` and `logging.getLogger(__name__)` in every file.

Why:

- it keeps logging usage consistent across generated code
- it leaves room for future logger adapters or context-aware wrappers
- it gives agents a single preferred logging entrypoint

When updating generated template files or module generation code, prefer `get_logger(__name__)` as the standard logging pattern.

## Runtime Conventions

Generated projects should prefer a dedicated runner module:

```bash
uv run python -m <package>.run
```

This is preferred over embedding long `uvicorn` command lines in documentation or relying only on `fastapi dev`.

The runner should read production-relevant `uvicorn` settings from `settings.py` / `.env` so teams can configure runtime behavior without editing code for common cases.

## CLI Conventions

Current CLI command groups:

- `polepos start`
- `polepos start --db sqlite|postgres|none`
- `polepos add module`
- `polepos add auth`
- `polepos remove module`
- `polepos add integration kafka`
- `polepos add integration rabbitmq`
- `polepos add integration redis`
- `polepos add integration rq`
- `polepos check`
- `polepos check --json`
- `polepos check --fix`
- `polepos db status`
- `polepos db upgrade`
- `polepos db revision -m "..."`
- `polepos db downgrade`
- `polepos upgrade`
- `polepos help`
- `polepos version`

Design expectations:

- top-level commands should stay few and intentional
- namespace commands like `add`, `remove`, and `db` should scale to more subcommands over time
- usage messages should be short, direct, and actionable
- project detection should work from nested directories inside a PolePosition project

If you add new CLI behavior:

- update command registration
- update README command documentation
- add repo tests
- keep namespace structure coherent

## Commit Message Standard

Use Conventional Commits for repository commits:

```text
<type>(<scope>): <summary>
```

Use a scope when it clarifies the product surface or code area. Keep the summary
short, imperative, and lower-case after the type. Prefer 72 characters or fewer
for the subject line.

Preferred types:

- `feat`: user-facing capability or generated-project behavior
- `fix`: bug fix or behavior correction
- `docs`: documentation-only change
- `test`: test-only change
- `refactor`: structure change without intended behavior change
- `chore`: maintenance that does not affect users
- `build`: packaging, build, or dependency metadata
- `ci`: CI or release automation
- `perf`: performance improvement

Preferred scopes:

- `cli`
- `start`
- `add`
- `check`
- `db`
- `template`
- `docs`
- `tests`

Examples:

```text
feat(template): add generated agent guidance
fix(add): require integration managed markers before patching
refactor(add): harden pyproject dependency patching
docs: clarify project validation via polepos check
test(check): cover missing integration env markers
```

Add a short body when the change needs rationale, migration notes, or a behavior
summary. Do not use vague subjects such as `updates`, `fix stuff`, or `wip`.

## Project Check Rules

`polepos check` is the lifecycle contract validator for generated projects.
It should stay read-only, deterministic, and file-based.

Current layers:

- core checks: project identity, generated structure, Alembic config, and managed markers
- lifecycle checks: added module files, module exports, router wiring, model wiring, and generated tests
- integration checks: Kafka, RabbitMQ, Redis, RQ, LLM, and auth workflow files, settings, env values, and dependencies

When changing generated structure, module generation, integration generation,
managed markers, or Alembic behavior:

- update `pole_position/cli/services/project_checker/`
- update `pole_position/tests/test_check_command.py`
- update `pole_position/tests/test_project_checker.py` when helper behavior changes
- update `docs/project-checks.md`
- update README if user-facing behavior changes

Do not make `check` require a running database, broker, LLM provider, network
access, or optional integration dependency. It should report drift without
installing packages, applying migrations, or mutating generated projects.

## Database and Migration Rules

PolePosition uses:

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

Current database philosophy:

- generated apps are migration-first
- schema changes should flow through Alembic
- `db/models.py` is the model import aggregation point for metadata discovery
- new generated modules with models should be wired into `db/models.py`
- removing a module cleans generated model imports but does not drop live
  database tables; table removal still needs a reviewed Alembic migration

If you touch migration behavior:

- preserve `DATABASE_URL`-based configuration
- preserve `Base.metadata` as Alembic target metadata
- preserve `import_models()` in the Alembic flow
- do not move schema creation into app startup

## Module Generation Rules

`polepos add module <name>` currently generates:

- `__init__.py`
- `model.py`
- `repository.py`
- `router.py`
- `schemas.py`
- `services/__init__.py`
- `services/<module>_service.py`
- integration test
- unit test

It also updates:

- `src/<package>/modules/__init__.py`
- `src/<package>/api/router.py`
- `src/<package>/db/models.py`

`polepos add module <name> --template crud` generates a fuller database-backed
CRUD module:

- `__init__.py`
- `model.py`
- `repository.py`
- `router.py`
- `schemas.py`
- `services/__init__.py`
- `services/<module>_crud_service.py`
- CRUD integration and unit tests

It also updates module exports, API router wiring, and `db/models.py`.

`polepos add module <name> --template ai-prompt` generates an LLM-oriented
module skeleton instead:

- `__init__.py`
- `prompts.py`
- `orchestrator.py`
- `router.py`
- `schemas.py`
- `services/__init__.py`
- `services/<module>_service.py`
- integration and unit tests
- shared `src/<package>/integrations/llm/*` files when missing
- `settings.py` / `.env.example` LLM settings when missing

`polepos add module <name> --api-only` and
`polepos add module <name> --template api-only` generate a lightweight API
module instead:

- `__init__.py`
- `router.py`
- `schemas.py`
- `services/__init__.py`
- `services/<module>_service.py`
- integration and unit tests

API-only modules do not generate `model.py`, `repository.py`, or `db/models.py`
wiring.

When changing module generation:

- keep generated code simple and readable
- keep imports sorted and deterministic
- keep generated tests useful but lightweight
- avoid generating auth-specific behavior by default
- preserve a REST-friendly starting point
- keep AI templates provider-agnostic unless the user explicitly asks for a provider-specific scaffold

Do not assume a generated module means a complete auth or domain solution.
It is a strong starting skeleton, not a full business system.

## Managed Block Rules

Some generated files contain PolePosition-managed markers.

Examples:

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

Why they matter:

- `polepos add module` inserts generated lines relative to these markers
- surrounding custom code is allowed
- removing the marker may break future automated updates

If you change managed files, prefer preserving the marker and customizing code around it rather than deleting it.

If you must redesign a managed file completely, treat that as opting out of future automatic patching for that surface.

## Documentation Expectations

README is important in this repo.

If you change user-facing behavior, update README when relevant.
Especially update README if you change:

- CLI commands
- setup steps
- database workflow
- generated project structure
- example workflows

The README should help both humans and coding agents understand:

- what the product is
- which command to use when
- how a PostgreSQL + FastAPI REST workflow looks

## Testing Expectations

Repo tests are the main validation layer.

When you change behavior, prefer adding or updating tests under:

- `pole_position/tests/test_cli.py`
- `pole_position/tests/test_startproject.py`
- `pole_position/tests/test_add_module.py`
- `pole_position/tests/test_check_command.py`
- `pole_position/tests/test_project_checker.py`
- `pole_position/tests/test_db_commands.py`

Typical validation command:

```bash
PYTHONPATH=/Users/eren/Developer/poleposition /Users/eren/.pyenv/versions/3.11.9/bin/python3 -m pytest pole_position/tests
```

If you cannot run a heavier integration flow because a dependency is missing in the environment, prefer:

- adding the highest-value repo-level test you can
- documenting what could not be executed

## Common Agent Tasks

### Add a new CLI command

1. Add a command file under the correct namespace
2. Register it in the correct root or subcommand registry
3. Add repo tests
4. Update README if user-facing

### Improve generated project template

1. Change files under `pole_position/template/`
2. Verify placeholders still render correctly
3. Update generated-project tests in `test_startproject.py`
4. Update README and template README if needed

### Change module generation or removal

1. Update `pole_position/cli/services/module_creator/`
2. Update `pole_position/cli/services/module_remover/` when removal behavior changes
3. Verify router wiring, model wiring, test generation, and cleanup symmetry
4. Add or update tests under `test_add_module.py` and `test_remove_module.py`

### Change database command behavior

1. Update files under `pole_position/cli/commands/db/`
2. Keep project-root discovery working
3. Add or update tests under `test_db_commands.py`
4. Keep README command docs aligned

### Change project check behavior

1. Update `pole_position/cli/services/project_checker/`
2. Keep checks read-only and file-based
3. Add or update tests under `test_check_command.py`
4. Add or update helper tests under `test_project_checker.py` when needed
5. Update `docs/project-checks.md`
6. Update README if user-facing behavior changes

## Things That Do Not Exist Yet

Do not assume these are implemented unless you add them:

- `polepos delete module`
- production presets

If you introduce one of these, document it clearly and add tests.

## Decision Heuristics

When several options are possible, prefer the one that:

- improves the end-to-end developer workflow
- keeps the generated app understandable to a FastAPI developer
- makes the CLI more consistent
- preserves explicit structure
- reduces manual setup for PostgreSQL-backed REST APIs

If a change would make PolePosition more magical but less understandable, prefer the more understandable version.
