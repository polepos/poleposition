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
uv sync --extra dev
polepos db upgrade
uv run python -m shop_api.run
```

The generated runner reads `.env` at process startup, creates the FastAPI app
through `create_app()`, and serves the ASGI app exposed from `shop_api.main`.
Importing `shop_api.app` by itself does not initialize settings or logging.

`polepos start` defaults to `--db sqlite`. Use `--db postgres` when the generated
project should start with PostgreSQL settings, or `--db none` for a database-free
starter that omits SQLAlchemy and Alembic wiring.

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

Generated module endpoint paths are relative to the module router. The standard
starter uses collection handlers such as `@router.get("/")` and
`@router.post("/")`, while `api/router.py` includes that router with a
module-specific prefix:

```python
api_router.include_router(customers_router, prefix="/customers", tags=["customers"])
```

With the default `API_V1_PREFIX`, those handlers are served as:

```text
GET  /api/v1/customers/
POST /api/v1/customers/
```

Refine the generated files for the real domain:

- `model.py`
- `schemas.py`
- `services/<module>_service.py`
- `repository.py`
- `router.py`

Use a different module template when the boundary is clearer:

```bash
polepos add module customers --template crud
polepos add module webhooks --api-only
polepos add module notifications --service-only
polepos add module assistant --template ai-prompt
```

`--service-only` generates an internal module (model, repository, service, and
tests) that owns data but exposes no HTTP routes, for domain services, event
handlers, background jobs, or integrations.

See [Module Templates](module-templates.md) for the generated file layouts and
tradeoffs.

If you generated the wrong boundary, remove it before adding the replacement:

```bash
polepos remove module customers
```

The remove command deletes the generated module, generated tests, and managed
router/model/export wiring. It stops before deleting files if the wiring has
drifted away from a managed layout.

If the module directory was already deleted manually, rerun
`polepos remove module customers` to clean the remaining generated tests and
managed router, model, and export wiring.

Removal does not change the live database. If the removed database-backed module had a
table and you want that table removed too, create and review a migration after
the code cleanup:

```bash
polepos db revision -m "remove customers table"
polepos db upgrade
```

## Validate the Project Contract

```bash
polepos check
polepos check --json
polepos check --fix
```

The default check command is read-only and file-based. It reports lifecycle
drift without installing dependencies, running migrations, starting services, or
contacting external systems. Use `--json` for CI or agent workflows. Use
`--fix` when safe managed markers should be restored after a merge conflict.

## Create and Apply Migrations

```bash
polepos db status
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

The Docker migration command runs Alembic directly inside the generated app
container. For the host workflow, keep using `polepos db upgrade`.

## Enable Shell Completion

Add tab completion for commands, subcommands, flags, template and database
values, integration names, and the current project's module names:

```bash
# bash (requires bash-completion)
polepos completion bash >> ~/.bashrc

# zsh (save onto a directory on your $fpath, then restart the shell)
polepos completion zsh > ~/.zfunc/_polepos

# fish
polepos completion fish > ~/.config/fish/completions/polepos.fish
```

To try it in the current shell without installing, source it directly:

```bash
source <(polepos completion bash)
```

See the [CLI Reference](cli.md#shell-completion) for the full details.
