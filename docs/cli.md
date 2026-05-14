# CLI Reference

PolePosition keeps the top-level command surface intentionally small. Namespace
commands grow under `add`, `remove`, and `db` as the lifecycle expands.

## Create a Project

```bash
polepos start shop-api
polepos start shop-api --install
polepos start shop-api --no-bytecode
polepos start shop-api --db postgres
polepos start shop-api --db none
polepos start --help
```

`--install` syncs generated project dependencies after creation. It does not
run migrations; after copying `.env.example` to `.env`, run
`polepos db upgrade`. `--no-bytecode` configures generated runtime and migration
commands to avoid Python bytecode cache writes during common local workflows.

`--db` is non-interactive and accepts `sqlite`, `postgres`, or `none`. The
default is `sqlite`. Use `postgres` when the generated project should start with
a PostgreSQL `DATABASE_URL`; use `none` for a database-free [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/) starter with
no SQLAlchemy, Alembic, migrations, or generated `db/` wiring.

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

Module route decorators are relative to the module router. A generated
`customers` module can safely define `@router.get("/")` because PolePosition
registers it once in `src/<package>/api/router.py`:

```python
api_router.include_router(customers_router, prefix="/customers", tags=["customers"])
```

With the generated app-level API prefix, that route is served as
`GET /api/v1/customers/`. Other modules can also define `/` handlers because
each module gets its own router prefix.

## Remove a Module

```bash
polepos remove --help
polepos remove module customers
polepos remove module customers --trace
polepos remove module customers --force
polepos remove module customers --wiring-only
```

`remove module` is the counterpart to `add module`. It removes the module
directory, generated integration and unit tests, module exports, API router
wiring, and standard-module model imports.

If the module directory was already deleted manually, the command still cleans
remaining generated tests and managed router, model, and export wiring.

By default, the command stops before deleting the module directory when the
module files or generated tests appear to contain custom changes. Use `--trace`
to preview the planned removals and updates without changing files. Use
`--force` only when you intentionally want to remove a customized module
directory.

Use `--wiring-only` when a module directory contains custom code you want to
keep, but the PolePosition-managed references should be removed. This mode
cleans module exports, API router wiring, standard-module model imports, and
generated tests. It does not delete the module directory or shared integration
scaffold.

After `--wiring-only`, either move/delete the preserved module directory or
restore explicit wiring before expecting `polepos check` to pass.

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
starter module routing, added module wiring, orphan generated remnants,
generated tests, and supported integration scaffolds. It works from nested
directories inside a PolePosition project.

When it fails, each issue includes a `PPCHK` code and a `Fix:` hint so humans,
coding agents, and CI logs can point to the same remediation.

New generated projects include `.poleposition.toml`, which records package,
database mode, module templates, and generated integrations. If that file is
missing in an older project, `check` falls back to structural inference.

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
