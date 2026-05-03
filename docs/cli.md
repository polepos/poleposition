# CLI Reference

PolePosition keeps the top-level command surface intentionally small. Namespace
commands grow under `add` and `db` as the lifecycle expands.

## Create a Project

```bash
polepos start shop-api
polepos start shop-api --install
polepos start shop-api --no-bytecode
```

`--install` syncs the generated project after creation. `--no-bytecode`
configures generated runtime and migration commands to avoid Python bytecode
cache writes during common local workflows.

## Add a Module

```bash
polepos add module customers
polepos add module assistant --template ai-prompt
polepos add module webhook --api-only
polepos add module webhook --template api-only
```

The standard module template generates a REST-friendly starting point with
model, repository, schemas, service, router, and tests.

The `ai-prompt` template generates a provider-agnostic LLM-oriented module
skeleton and shared `integrations/llm` files when they are missing.

The `api-only` template generates router, schemas, service, and tests without
model, repository, or database wiring. `--api-only` is the shortcut form.

## Add Integrations

```bash
polepos add integration kafka
polepos add integration rabbitmq
```

Integration commands add opt-in adapter scaffolds, settings, environment
examples, transport dependencies, and lightweight test doubles.

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
polepos db upgrade
polepos db revision -m "add customers table"
polepos db downgrade -1
```

Database commands prefer `uv run alembic ...` when `uv` is available. Without
`uv`, they fall back to the active virtualenv, the project `.venv`, or the
first `python` on `PATH`.

## Help and Version

```bash
polepos help
polepos version
```
