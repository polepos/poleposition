# CLI Reference

PolePosition keeps the top-level command surface intentionally small. Namespace
commands grow under `add`, `remove`, and `db` as the lifecycle expands.

## Create a Project

```bash
polepos start shop-api
polepos start shop-api --install
polepos start shop-api --no-bytecode
polepos start --help
```

`--install` syncs the generated project after creation. `--no-bytecode`
configures generated runtime and migration commands to avoid Python bytecode
cache writes during common local workflows.

## Add a Module

```bash
polepos add --help
polepos add module customers
polepos add module assistant --template ai-prompt
polepos add module webhook --api-only
polepos add module webhook --template api-only
```

The standard module template generates a REST-friendly starting point with
model, repository, schemas, a module-local `services/` package, router, and
tests.

The `ai-prompt` template generates a provider-agnostic LLM-oriented module
skeleton and shared `integrations/llm` files when they are missing.

The `api-only` template generates router, schemas, a module-local `services/`
package, and tests without model, repository, or database wiring. `--api-only`
is the shortcut form.

## Remove a Module

```bash
polepos remove --help
polepos remove module customers
polepos remove module customers --trace
polepos remove module customers --force
```

`remove module` is the counterpart to `add module`. It removes the module
directory, generated integration and unit tests, module exports, API router
wiring, and standard-module model imports.

By default, the command stops before deleting the module directory when the
module files or generated tests appear to contain custom changes. Use `--trace`
to preview the planned removals and updates without changing files. Use
`--force` only when you intentionally want to remove a customized module
directory.

The command is intentionally file-based. It does not connect to the database,
create a migration, drop tables, or edit migration history. If the removed
module had a SQLAlchemy model and you want to remove its table, create and
review an Alembic revision after removal:

```bash
polepos remove module customers
polepos db revision -m "remove customers table"
polepos db upgrade
```

For `ai-prompt` modules, removing the last AI prompt module also removes the
shared LLM settings, `.env.example` values, and `integrations/llm` scaffold.
If another AI prompt module remains, the shared LLM scaffold is kept.

The command also stops before deleting files when managed wiring has drifted
into a layout it cannot clean safely. Fix the reported layout or remove the
custom wiring manually, then retry.

## Add Integrations

```bash
polepos add integration kafka
polepos add integration rabbitmq
```

Integration commands add opt-in adapter scaffolds, settings, environment
examples, transport dependencies, and lightweight test doubles.

See the [Integration Guides](integrations/index.md) for Kafka, RabbitMQ, and LLM
scaffold details.

## Check a Project

```bash
polepos check
```

`check` validates generated structure, managed markers, Alembic configuration,
added module wiring, generated tests, and supported integration scaffolds. It
works from nested directories inside a PolePosition project.

PolePosition does not currently provide a separate `polepos validate` command.
Project contract validation is handled by `polepos check`.

## Database Commands

```bash
polepos db --help
polepos db upgrade
polepos db revision -m "add customers table"
polepos db downgrade -1
```

Database commands prefer `uv run alembic ...` when `uv` is available. Without
`uv`, they fall back to the active virtualenv, the project `.venv`, or the
first `python` on `PATH`.

For the full database workflow, see [Database and Migrations](database.md).

For generated `.env` values, see the
[Configuration Reference](configuration.md).

## Help and Version

```bash
polepos help
polepos version
polepos version --help
```
