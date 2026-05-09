# Database and Migrations

PolePosition generated projects are migration-first. Database schema changes
should move through Alembic migration files, not through table creation during
application startup.

The normal local workflow is:

```bash
polepos db upgrade
polepos db revision -m "add customers table"
polepos db upgrade
```

## What `polepos db` Does

`polepos db` is a small PolePosition command group around Alembic.

It keeps database work inside the same lifecycle vocabulary as:

- `polepos start`
- `polepos add module`
- `polepos remove module`
- `polepos check`

The command group currently exposes:

```bash
polepos db upgrade [target]
polepos db revision -m "<message>"
polepos db downgrade <target>
```

`polepos db` finds the PolePosition project root from the current directory.
That means you can run it from the project root or from a nested directory under
`src/<package>/`.

## Why Not `create_all()` At Startup

Generated applications do not create tables during FastAPI startup.

PolePosition avoids startup-time schema creation because production schema
changes should be:

- explicit
- reviewable
- reproducible
- reversible
- independent from API process startup

Alembic migration files give the team a history of schema changes. They can be
reviewed in pull requests, applied in CI or deployment jobs, and rolled back
when needed.

Generated test fixtures may create SQLite tables for fast local tests. That is
test setup only. Runtime database schema changes should still go through
Alembic.

## Initial Migration

After creating a project, copy the environment file, install dependencies, and
apply the initial migration:

```bash
polepos start shop-api
cd shop-api
cp .env.example .env
uv sync
polepos db upgrade
```

The initial migration command is still part of the startup flow even though the
default project has no application tables yet. It verifies that Alembic can read
your settings and that the migration environment is healthy. After it completes,
run the app:

```bash
uv run python -m shop_api.run
```

## Adding a Module With a Model

The default module template generates SQLAlchemy model and repository files:

```bash
polepos add module customers
```

Then refine the generated domain files:

```text
src/shop_api/modules/customers/model.py
src/shop_api/modules/customers/schemas.py
src/shop_api/modules/customers/repository.py
src/shop_api/modules/customers/services/customers_service.py
src/shop_api/modules/customers/router.py
```

After changing the model, create and apply a migration:

```bash
polepos db revision -m "add customers table"
polepos db upgrade
polepos check
```

Always review generated migration files before applying them to shared
environments.

## `api-only` and AI Prompt Modules

`api-only` modules do not generate a model or repository:

```bash
polepos add module webhooks --api-only
```

AI prompt modules also do not generate database model wiring:

```bash
polepos add module assistant --template ai-prompt
```

If one of these modules later needs persistence, add the model and repository
yourself, then import the model from `src/<package>/db/models.py` so Alembic can
discover its metadata.

## Model Discovery

Alembic uses `Base.metadata` as its target metadata. Generated projects keep
model imports centralized in:

```text
src/<package>/db/models.py
```

Standard modules are wired into this file automatically by:

```bash
polepos add module customers
```

If you add a SQLAlchemy model manually, update `import_models()` in
`db/models.py`. Without that import, Alembic autogenerate may not see the new
table.

## Removing a Module With Database State

`polepos remove module <name>` is a code cleanup command. It removes generated
module files, generated tests, module exports, router wiring, and, for standard
modules, the generated model import from `src/<package>/db/models.py`.

It does not:

- connect to the database
- drop tables
- delete rows
- create an Alembic revision
- edit historical migration files
- apply or downgrade migrations

For a database-backed standard module, the usual removal flow is:

```bash
polepos remove module customers
polepos db revision -m "remove customers table"
polepos db upgrade
polepos check
```

The remove command changes the model discovery surface first. Because the
module model import is removed from `db/models.py`, Alembic autogenerate can
compare the current database against the updated `Base.metadata`. If the
database contains a table that is no longer represented in metadata,
autogenerate may propose `op.drop_table(...)`.

Always review that generated revision before applying it. Dropping a table is a
data-destructive schema change. In many real projects you may need a staged
migration instead, such as removing foreign keys first, backfilling replacement
tables, archiving data, or keeping the table while only removing the API module.

If you want to remove the API code but keep the table and data, run
`polepos remove module <name>` and do not create a table-drop migration. The
database will keep its existing schema until a later Alembic migration changes
it.

`api-only` and `ai-prompt` modules do not have generated model imports, so
removing them has no database metadata effect by default. If you manually added
models, repositories, relationships, or custom imports for one of those modules,
clean up that custom model wiring and write the migration yourself.

`polepos check` can confirm that generated module wiring is clean after removal.
It does not inspect live database tables and does not prove that a table was
dropped or retained.

## `DATABASE_URL`

Alembic reads the database URL from the generated settings layer. The default
`.env.example` starts with SQLite:

```env
DATABASE_URL=sqlite:///./poleposition.db
```

For PostgreSQL, set:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/shop_api
```

Then run:

```bash
polepos db upgrade
```

The migration command does not start a database for you. Make sure PostgreSQL is
running before using a PostgreSQL `DATABASE_URL`.

## Docker and PostgreSQL

Generated projects include a Docker Compose setup with PostgreSQL:

```bash
cp .env.example .env
docker compose up --build
```

Apply migrations from the app container:

```bash
docker compose run --rm app uv run alembic upgrade head
```

The Docker command runs Alembic directly because the generated application image
contains the generated app dependencies, not the PolePosition CLI. The local
host workflow should still use `polepos db`.

If PostgreSQL is already using host port `5432`, change `POSTGRES_PORT` in
`.env` before starting the compose stack.

## Command Details

### `polepos db upgrade`

Apply migrations to a target revision. Without a target, PolePosition uses
`head`:

```bash
polepos db upgrade
polepos db upgrade head
```

Use this after creating a project, after creating a new migration, and during
deployment flows that apply already-reviewed migration files.

### `polepos db revision`

Create a new autogenerated Alembic revision:

```bash
polepos db revision -m "add customers table"
```

This runs Alembic autogenerate. The generated file should be reviewed before it
is applied. Autogenerate is helpful, but it is not a substitute for migration
review.

### `polepos db downgrade`

Revert to a target revision:

```bash
polepos db downgrade -1
```

Use downgrade commands carefully in shared environments. Review the migration's
`downgrade()` function before relying on it.

## How PolePosition Runs Alembic

`polepos db` prefers:

```text
uv run alembic ...
```

when `uv` is available.

If `uv` is not available, it falls back to:

1. the active virtualenv from `VIRTUAL_ENV`
2. the generated project's `.venv`
3. the first `python` or `python3` on `PATH`

This keeps the command useful for both `uv` and normal `pip` workflows.

## Direct Alembic Usage

Use `polepos db` for normal project lifecycle work.

Direct Alembic commands are still reasonable when you need an option that
PolePosition does not expose:

```bash
uv run alembic history
uv run alembic current
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "add customers table"
```

The direct command should be treated as advanced Alembic usage. The default
documentation and generated project flow should prefer `polepos db`.

## Troubleshooting

If a migration cannot connect, check `DATABASE_URL` in `.env` and confirm the
database server is running.

If Alembic autogenerate misses a table, check that the model is imported from
`src/<package>/db/models.py`.

If module or model wiring has drifted, run:

```bash
polepos check
```

`polepos check` is read-only. It reports missing generated files, managed
markers, router wiring, model wiring, tests, and supported integration wiring
without connecting to the database.
