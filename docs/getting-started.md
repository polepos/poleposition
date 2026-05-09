# Getting Started

PolePosition is designed around a `uv`-first workflow, while still supporting a
normal `pip` and virtualenv setup.

## Install

Install the CLI as a tool:

```bash
uv tool install poleposition
```

Or install with pip:

```bash
pip install poleposition
```

## Create a Project

```bash
polepos start shop-api
cd shop-api
cp .env.example .env
uv sync
polepos db upgrade
uv run python -m shop_api.run
```

Open the generated FastAPI docs at:

```text
http://127.0.0.1:8000/docs
```

For all generated `.env` values, see the
[Configuration Reference](configuration.md).

## Add a Module

```bash
polepos add module customers
```

The command creates a module under `src/shop_api/modules/customers/`, adds
starter tests, wires the router, and registers model imports for Alembic
metadata discovery.

Refine the generated files for the real domain:

- `model.py`
- `schemas.py`
- `services/<module>_service.py`
- `repository.py`
- `router.py`

If you generated the wrong boundary, remove it before adding the replacement:

```bash
polepos remove module customers
```

The remove command deletes the generated module, generated tests, and managed
router/model/export wiring. It stops before deleting files if the wiring has
drifted away from a managed layout.

Removal does not change the live database. If the removed standard module had a
table and you want that table removed too, create and review a migration after
the code cleanup:

```bash
polepos db revision -m "remove customers table"
polepos db upgrade
```

## Validate the Project Contract

```bash
polepos check
```

The check command is read-only and file-based. It reports lifecycle drift
without installing dependencies, running migrations, starting services, or
contacting external systems.

## Create and Apply Migrations

```bash
polepos db revision -m "add customers table"
polepos db upgrade
```

PolePosition generated projects are migration-first. Keep schema changes in
Alembic instead of creating tables during application startup.

For details on `polepos db`, `DATABASE_URL`, PostgreSQL, and direct Alembic
usage, see [Database and Migrations](database.md).

If something drifts, run `polepos check` and use the
[Troubleshooting and FAQ](troubleshooting.md) guide.

## Docker Workflow

Generated projects include a Docker setup with PostgreSQL:

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm app uv run alembic upgrade head
```
