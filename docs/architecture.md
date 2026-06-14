# PolePosition Architecture

This document explains how PolePosition is structured as a product and as a codebase.

For a visual overview, see the [Architecture Diagram](architecture-diagram.md).

It is meant to help both humans and coding agents answer the same questions quickly:

- what the product does
- where CLI behavior lives
- where runtime helper APIs live
- where generated project behavior lives
- how `add module` and `remove module` safely update files
- which parts are stable conventions versus evolving surfaces

## Product Shape

PolePosition is a project lifecycle CLI, not only a one-time scaffold tool or template repository.

Its value comes from connected lifecycle workflows:

1. `polepos start`
2. `polepos add module`
3. `polepos remove module`
4. `polepos add integration ...`
5. `polepos check`
6. `polepos db ...`

That means the product helps at:

- project creation
- codebase growth
- project contract checks
- schema lifecycle management

Templates are a delivery mechanism for those workflows, not the product boundary.

The generated project should stay FastAPI-native while still giving teams opinionated structure and defaults.

PolePosition also ships a small runtime helper package for application code:

```python
from polepos.data import LRUCache, Trie
```

The import package `polepos` is intentionally separate from the internal
`pole_position` implementation package. Generated applications may import
`polepos.data`; they should not import `pole_position.cli...`.

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

polepos remove module users
  -> commands/remove/module.py
  -> module_remover.py
  -> removes generated module files + managed updates

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
- `remove module`
- `add integration`
- `check`
- `db status`
- `db upgrade`
- `db revision`
- `db downgrade`
- `upgrade`
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

- `app.py`: FastAPI application factory; it reads settings and configures
  logging when `create_app()` is called
- `main.py`: ASGI import target; it exposes `app = create_app()` for Uvicorn
- `run.py`: local/runtime process entrypoint; it prints startup details and
  starts Uvicorn from settings
- `auth/`: endpoint authentication foundation
- `bootstrap/`: logging, middleware, lifespan, error wiring
- `api/`: API composition and shared dependencies
- `db/`: SQLAlchemy base, session, model import aggregation
- `domain/`: domain exceptions and shared primitives
- `integrations/`: external systems such as LLM adapters
- `modules/`: feature modules such as `status`, `users`, `customers`

## Runtime Entrypoints

Generated apps separate application construction from process startup:

```text
app.py
  -> create_app()
  -> read settings
  -> setup logging
  -> build FastAPI app

main.py
  -> app = create_app()
  -> ASGI import target for Uvicorn

run.py
  -> main()
  -> read settings
  -> print startup table
  -> uvicorn.run("<package>.main:app", ...)
```

This separation is deliberate. Importing `src/<package>/app.py` should not
freeze `.env` values or configure logging by itself. Tests and dynamic runtime
overrides can import `create_app`, update environment values, clear the
`get_settings()` cache when needed, and then call `create_app()`.

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
- `crud`
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
- records the module template in `.poleposition.toml` when present
- optionally adds LLM integration files
- optionally patches settings and `.env.example`

Module routers use local paths. A generated standard module can define
`@router.get("/")` and `@router.post("/")` inside
`src/<package>/modules/<name>/router.py`; `module_creator.py` then registers the
router once in `src/<package>/api/router.py` with `prefix="/<name>"`. The
FastAPI app applies the app-level API prefix in `app.py`, so a `customers`
module root route is served as `/api/v1/customers/`, not as a shared global `/`.

The `--api-only` CLI option is a shortcut for the `api-only` template. It
generates router, schemas, a module-local `services/` package, and tests
without model, repository, or database model wiring.

The `crud` template stays database-backed like `standard`, but generates
detail, update, and delete routes plus CRUD-specific service and test names.

## `remove module` Architecture

`polepos remove module` is the cleanup counterpart to `add module`.

Implementation lives in:

```text
pole_position/cli/services/module_remover.py
```

The remover detects the generated module template, then removes:

- `src/<package>/modules/<name>/`
- generated integration and unit tests for the detected template
- the module export from `modules/__init__.py`
- the API router import and include from `api/router.py`
- the model import from `db/models.py` for database-backed generated modules
- the module template entry from `.poleposition.toml` when present

It is a project-file operation, not a database operation. It does not open a
database connection, create a migration, drop tables, delete data, or rewrite
historical Alembic revisions. For database-backed modules, removing the model
import narrows Alembic metadata discovery; a later reviewed migration decides
whether the physical table is dropped, retained, or replaced.

For `ai-prompt` modules, removing the last AI prompt module also removes shared
LLM settings, `.env.example` values, and the `integrations/llm` scaffold. If
another AI prompt module remains, shared LLM files and settings stay in place.

The command checks managed markers, generated wiring, and generated module
content before deleting the module directory. If router, model, or export wiring
has drifted into an unsupported custom layout, it stops before removing files so
the project is not left partially cleaned. If module files or generated tests
appear to contain custom changes, it also stops unless `--force` is used. An
expected generated file that can no longer be decoded as text is treated as a
modified generated file, so `--force` can still remove the module intentionally
instead of failing during custom-change detection.
`--trace` reports the planned removals and updates without mutating files.

Router and model wiring checks are Python-aware. The remover can delete the
generated `from <package>.modules.<name>.router ...` import and matching
`api_router.include_router(...)` call, including multi-line generated calls. It
does not delete additional custom imports or includes for the same module. Those
custom references block removal until the user removes or rewires them.

`--wiring-only` is the escape hatch for customized module directories. It
removes PolePosition-managed exports, router wiring, database-backed module model
imports, and generated tests, but preserves the module directory and shared
integration scaffolds. This lets users detach generated wiring without deleting
custom code.

## `add integration` Architecture

`polepos add integration ...` grows an existing project with external system
helpers while keeping the base template lean.

Current integrations:

- `kafka`
- `rabbitmq`
- `redis`
- `rq`

External-system support is intentionally opt-in. Kafka writes
`integrations/kafka` helpers and adds `aiokafka`; RabbitMQ writes
`integrations/rabbitmq` helpers and adds `aio-pika`; Redis writes
`integrations/redis` helpers and adds `redis`; RQ writes `integrations/rq`
helpers and adds `rq`. These integrations patch settings and `.env.example`
values. Consumer loops and background workers are left as explicit worker/runtime
code instead of being started inside the FastAPI app process.

Integration env handling distinguishes active required keys from optional
commented examples. A required key that appears only as a comment is treated as
missing, so `polepos add integration kafka` inserts an active
`KAFKA_BOOTSTRAP_SERVERS=...` line even if `# KAFKA_BOOTSTRAP_SERVERS=...`
already exists. Optional examples such as `# KAFKA_COMPRESSION_TYPE=` and
`# LLM_MAX_TOKENS=` are allowed to remain commented.

Integration dependency patching targets `[project].dependencies` in
`pyproject.toml`. It tolerates normal TOML formatting differences such as
inline or multi-line arrays, but it does not patch dependency groups or
tool-specific dependency lists.

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
- integration checks: Kafka, RabbitMQ, Redis, RQ, LLM, and auth workflow files, dependencies, settings keys, and env keys

Lifecycle orphan checks parse router and model Python files across the whole
file, not just lines before managed markers. This lets `check` report custom
imports that still reference a missing module after the generated block was
cleaned. Integration checks parse exact active setting/env keys so comments and
substring matches do not hide missing required values.

Core-only behavior is available through `check_core_project()` for internal
callers that need the foundation without lifecycle or integration checks.
The public `check_project()` path runs the full current contract.

New generated projects include `.poleposition.toml` at the project root. It is
small lifecycle metadata, not application configuration:

- application package name
- database mode: `sqlite`, `postgres`, `none`, or user-managed `custom`
- generated module templates
- generated integration scaffolds

When the manifest is present, package detection, module template detection, and
integration checks prefer it over inference. Older generated projects without
the manifest continue to use structural inference.

CRUD feature options are encoded with the module template value, for example
`customers = "crud[pagination,timestamps,tenant-scoped]"`. That keeps lifecycle
commands able to re-render the same generated variant when checking or removing
a module.

For the detailed user guide and agent-facing contract, see:

```text
docs/project-checks.md
```

## Managed Block Contract

`add module` and `remove module` depend on marker comments in generated files.

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

### The region above a marker is PolePosition-controlled

For the import- and export-style markers (`router-imports`, `model-imports`,
`module-exports`), PolePosition keeps the generated lines directly above the
marker in **alphabetical order**, so repeated `add module` runs produce a stable,
diff-friendly block instead of append-only churn.

The trade-off: that region is managed. A line you add by hand there that *matches
the generated pattern* (for example another
`from <package>.modules.<name> import router` import placed above
`# polepos:router-imports`) is treated as part of the managed block and may be
re-sorted on the next `add module` run. This is expected behavior, not a bug.

To keep a custom line exactly where you put it, make sure it does not look like a
generated entry: place it in a clearly separate region (for example below the
marker, or grouped with your other non-generated imports) rather than interleaved
with the generated lines.

The most important managed files are:

- `src/<package>/api/router.py`
- `src/<package>/db/models.py`
- `src/<package>/modules/__init__.py`
- `src/<package>/settings.py`
- `.env.example`
- `.poleposition.toml`

If these markers are removed or rearranged incorrectly, `polepos add module`,
`polepos remove module`, or `polepos add integration ...` may fail or stop
updating the file automatically.

`polepos check --fix` can restore missing safe markers. For `api/router.py`,
the fixer treats `api_router.include_router(...)` as Python syntax and places
`# polepos:router-includes` after the complete statement, including multi-line
router include calls.

## Lifecycle Manifest and Dependency Patching

Beyond managed markers, two services give the lifecycle commands a reliable view
of project state without re-deriving everything from files on each run.

### Lifecycle manifest (`.poleposition.toml`)

`pole_position/cli/services/project_manifest.py` owns the per-project manifest
written as `.poleposition.toml` at the project root. It records what the
generated project *is*, so `add`, `remove`, and `check` do not rely only on
inference:

- `package_name`: the application package recorded at `start`
- `database`: `sqlite`, `postgres`, or `none`
- `[modules]`: each added module's template, e.g.
  `customers = "crud[pagination,timestamps]"`
- `[integrations]`: generated integrations as `kafka = true`

The `ProjectManifest` dataclass also carries `invalid_integrations` and
`read_error`, so `check` can report a malformed manifest instead of crashing.
Module template values are encoded and decoded with
`format_manifest_module_template` / `parse_manifest_module_template` (the
`crud[...]` suffix carries the opt-in CRUD feature set). Mutations go through
`record_manifest_module` / `remove_manifest_module` and
`record_manifest_integration` / `remove_manifest_integration`, which keep the
file stable and comment-tolerant.

### Dependency patching

Adding auth or an integration may require a dependency in the generated
project's `pyproject.toml`. This is split into a pure contract layer and a
file-editing layer:

- `dependency_contract.py`: parsing and comparison only. `DependencyEntry`
  preserves a line's indent, quote style, value, and trailing text, and
  `dependency_contract_satisfied(dependencies, required)` returns whether an
  existing dependency already covers the required name, extras, and minimum
  version. No file I/O.
- `pyproject_editor.py`: the editor. `ensure_project_dependency(path, dependency)`
  finds the `[project]` `dependencies` array (inline or multi-line) and replaces
  or appends the entry while preserving the file's existing formatting.

Because patching is contract-driven it is idempotent: a dependency that already
satisfies the contract is left untouched, so re-running `add` does not create
duplicates.

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

The remove lifecycle keeps the same separation:

```text
polepos remove module customers
-> review whether database tables should remain
-> polepos db revision -m "remove customers table"
-> polepos db upgrade
```

If the team wants to remove only API code while retaining data, it should stop
after the remove command and avoid generating a drop-table migration.

## Authentication Boundary

Generated projects now include a JWT-based authentication foundation.

The important separation is:

- authentication: who is calling?
- authorization: what can this user access?

The generated auth package provides token helpers, `get_current_user`, and
`require_roles(...)` so newly added modules can define protected and role-gated
routes explicitly.

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
- logging setup happens from `create_app()`, not at `app.py` import time
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
- `examples/kafka-quick-start/`
- `examples/rabbitmq-quick-start/`
- `examples/redis-cache/`
- `examples/openai-prompt/`

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
