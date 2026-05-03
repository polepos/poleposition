# PolePosition

[![PyPI version](https://img.shields.io/pypi/v/poleposition?label=PyPI)](https://pypi.org/project/poleposition)
[![Python versions](https://img.shields.io/pypi/pyversions/poleposition?label=Python)](https://pypi.org/project/poleposition)
[![Package status](https://img.shields.io/pypi/status/poleposition?label=Status)](https://pypi.org/project/poleposition)
[![Downloads](https://img.shields.io/pypi/dm/poleposition?label=Downloads)](https://pypi.org/project/poleposition)
[![License](https://img.shields.io/github/license/erenertemden/poleposition?label=License)](https://raw.githubusercontent.com/erenertemden/poleposition/refs/heads/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-published-blue)](https://erenertemden.github.io/poleposition/)
[![FastAPI native](https://img.shields.io/badge/FastAPI-native-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![uv first](https://img.shields.io/badge/workflow-uv--first-261230)](https://docs.astral.sh/uv/)
[![Alembic migrations](https://img.shields.io/badge/database-Alembic%20migrations-orange)](https://alembic.sqlalchemy.org/)

![PolePosition logo](https://raw.githubusercontent.com/erenertemden/poleposition/main/assets/logo/poleposition-python-logo.svg)

A project lifecycle CLI that puts teams in pole position when starting, growing, and maintaining enterprise FastAPI projects.

PolePosition helps you keep [FastAPI](https://fastapi.tiangolo.com/)'s speed while avoiding the usual setup drag of enterprise backend work. It does more than render a project template: it gives teams commands for project creation, module growth, project checks, and migration workflows as the codebase evolves.

Start a new project lifecycle:

```bash
polepos start myapp --install
```

If you prefer not to generate Python bytecode while developing locally:

```bash
polepos start myapp --no-bytecode
```

---

## Example Output

```bash
$ polepos start myapp --install
Created project: myapp

Installing project dependencies...
Dependencies installed successfully with uv.

Next steps:
  cd myapp
  cp .env.example .env
  uv run alembic upgrade head
  uv run python -m myapp.run
```

## Why PolePosition?

PolePosition is named for the same reason teams use it: to start enterprise FastAPI development from pole position and keep it there as the project grows.

FastAPI projects should start fast, clean, and predictable, then stay easy to extend when the target is a larger production system.

PolePosition provides:

* A scalable project structure
* Environment-based configuration
* Alembic-based database migrations
* Lifecycle commands for project creation, module growth, project checks, and database migrations
* Built-in logging
* JWT-based endpoint authentication foundations
* Testing setup
* Module-oriented organization for growing codebases
* A ready-to-run FastAPI application

Less boilerplate at project creation. Less lifecycle friction as the app grows.

---

## Why not just FastAPI?

FastAPI is excellent, but turning it into a team-ready backend lifecycle often involves:

* Recreating the same structure
* Setting up logging and configuration
* Defining module boundaries
* Wiring database foundations
* Organizing modules manually
* Adding new modules without drifting from conventions
* Keeping database migrations and model imports aligned

PolePosition removes that overhead with CLI workflows that create the project, grow the codebase, validate the project contract, and keep migrations first-class.

---

## Documentation Map

Use these files to understand the repo quickly:

* [Published Docs](https://erenertemden.github.io/poleposition/)
* [Getting Started](docs/getting-started.md)
* [CLI Reference](docs/cli.md)
* [Architecture](docs/architecture.md)
* [Feature Status](docs/feature-status.md)
* [Project Checks](docs/project-checks.md)
* [Examples Index](examples/README.md)
* [Agent Guide](AGENTS.md)

Build the documentation site locally:

```bash
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

---

## Installation

PolePosition recommends a `uv`-first workflow for installation, dependency
sync, migrations, and local development. It also works with `pip` and a normal
Python virtual environment.

```bash
uv tool install poleposition
```

or

```bash
pip install poleposition
```

---

## Quick Start

Recommended `uv` workflow:

```bash
polepos start myapp --install
cd myapp
cp .env.example .env
uv run alembic upgrade head

uv run python -m myapp.run
```

Equivalent `pip` workflow:

```bash
pip install poleposition
polepos start myapp
cd myapp
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m alembic upgrade head

python -m myapp.run
```

Or start the generated app with Docker and PostgreSQL:

```bash
docker compose up --build
docker compose run --rm app uv run alembic upgrade head
```

Create and run migrations:

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "add garage table"
```

Open your API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Usage

### Create a project

```bash
polepos start myapp --install
```

`--install` runs `uv sync` when `uv` is available. If `uv` is not available, it
creates `.venv` and installs the generated project with `pip`.
`--no-bytecode` configures generated migration and runtime commands to start
with `PYTHONDONTWRITEBYTECODE=1`, preventing bytecode cache writes from
interpreter startup during common local workflows.

Project names:

* Must not be empty
* Must not contain whitespace
* May use hyphens like `my-app`
* Are normalized to a Python package name like `my_app`

### Manual setup

With `uv`:

```bash
polepos start myapp
cd myapp

cp .env.example .env
uv sync
uv run alembic upgrade head

uv run python -m myapp.run
```

With `pip`:

```bash
polepos start myapp
cd myapp

cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m alembic upgrade head

python -m myapp.run
```

### Add modules

```bash
polepos add module garage
polepos add module assistant --template ai-prompt
polepos add module webhook --api-only
```

`standard` is the default template for REST and domain modules.
`ai-prompt` adds a provider-agnostic LLM endpoint skeleton with module-local
prompt orchestration and shared `integrations/llm` adapters.
`api-only` generates router, schemas, service, and tests without model,
repository, or database wiring. Use `--api-only` as a shortcut for
`--template api-only`.

### Add integrations

```bash
polepos add integration kafka
polepos add integration rabbitmq
```

Messaging integrations add helper modules for JSON message publishing, consumer
construction, test doubles, settings, `.env.example` values, and transport
dependencies. Kafka uses `aiokafka`; RabbitMQ uses `aio-pika`. Consumers are
intentionally left as explicit worker/runtime code instead of being started
inside the API process.

### Project checks

```bash
polepos check
```

`check` runs the core project health checks for the current PolePosition
project. It validates project identity, generated structure, Alembic config,
managed markers, added module lifecycle wiring, and opt-in integration wiring
used by commands such as `polepos add module` and `polepos add integration`.

Use it after adding modules or integrations, after resolving merge conflicts in
managed files, and before handing a project to another teammate or coding
agent. The command is read-only: it reports drift but does not rewrite files,
install dependencies, run migrations, or contact external services.

The checks are organized into three layers:

* Core checks for project identity, generated structure, Alembic files, and managed markers
* Lifecycle checks for added module router/model/test wiring
* Integration checks for Kafka, RabbitMQ, and LLM files, settings, env values, and dependencies

See [Project Checks](docs/project-checks.md) for detailed user guidance and the
agent-facing check contract.

### Database commands

```bash
polepos db upgrade
polepos db revision -m "add garage table"
polepos db downgrade -1
```

Database commands prefer `uv run alembic ...` when `uv` is available. Without
`uv`, they run Alembic through the active virtualenv, the project `.venv`, or
the first `python` on `PATH`.

### Docker workflow

Generated projects include a `Dockerfile`, `.dockerignore`, and `compose.yaml`
so you can start the app with PostgreSQL in containers.

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm app uv run alembic upgrade head
```

The compose setup uses the generated `run.py` entrypoint and overrides
`DATABASE_URL` so the app talks to the bundled PostgreSQL service. If you
already have PostgreSQL on `5432`, change `POSTGRES_PORT` in `.env` before
starting the compose stack.

### Logging

Generated projects use `get_logger(__name__)` from `bootstrap.logging` as the preferred logging entrypoint.

```python
from shop_api.bootstrap.logging import get_logger

logger = get_logger(__name__)
```

### Runtime configuration

Generated projects include `src/<package>/run.py` as the preferred local and production-friendly entrypoint.

Use:

```bash
uv run python -m shop_api.run
```

The runner is configured from `settings.py` and `.env`, including:

* `APP_HOST`
* `APP_PORT`
* `APP_RELOAD`
* `LOG_LEVEL`
* `UVICORN_WORKERS`
* `UVICORN_ACCESS_LOG`
* `UVICORN_PROXY_HEADERS`
* `UVICORN_FORWARDED_ALLOW_IPS`
* `UVICORN_SERVER_HEADER`
* `UVICORN_DATE_HEADER`
* `UVICORN_TIMEOUT_KEEP_ALIVE`
* `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN`
* `UVICORN_TIMEOUT_WORKER_HEALTHCHECK`
* `UVICORN_LIMIT_CONCURRENCY`
* `UVICORN_LIMIT_MAX_REQUESTS`
* `UVICORN_LIMIT_MAX_REQUESTS_JITTER`
* `UVICORN_BACKLOG`

When the generated runner starts, it prints a compact startup table with the
current service name, environment, API prefix, database backend, host, port,
worker count, and docs URL.

### CORS

Generated projects include settings-driven CORS support with development
defaults for common localhost frontend origins.

You can control it from `.env` with:

* `CORS_ENABLED`
* `CORS_ALLOW_ORIGINS`
* `CORS_ALLOW_ORIGIN_REGEX`
* `CORS_ALLOW_CREDENTIALS`
* `CORS_ALLOW_METHODS`
* `CORS_ALLOW_HEADERS`
* `CORS_EXPOSE_HEADERS`
* `CORS_MAX_AGE`

The list-style fields accept JSON arrays in `.env`.

### Authentication

Generated projects include a minimal JWT-based authentication foundation with:

* a public `GET /api/v1/status` endpoint
* a protected `GET /api/v1/profile/me` endpoint
* a role-gated `GET /api/v1/profile/admin-preview` endpoint
* `get_current_user` and `require_roles(...)` helpers

Relevant auth settings:

* `AUTH_SECRET_KEY`
* `AUTH_ALGORITHM`
* `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`
* `AUTH_ISSUER`

### JSON logging

Generated projects support both text and JSON logging formats.

Use:

* `LOG_FORMAT=text` for local development
* `LOG_FORMAT=json` for structured production logging

The JSON formatter includes:

* `timestamp`
* `level`
* `logger`
* `message`
* `app_name`
* `environment`
* `request_id`

### When to use which command

PolePosition is a lifecycle CLI, so the commands are meant to be used over time, not only on day one:

* `polepos start` when you want to create a new FastAPI project with the PolePosition structure
* `polepos add module` when you want to add a new REST/domain module or an AI prompt module to an existing project
* `polepos add integration kafka` when you want Kafka producer and consumer wiring in an existing project
* `polepos add integration rabbitmq` when you want RabbitMQ publisher and consumer wiring in an existing project
* `polepos check` when you want to validate the project contract: generated structure, Alembic config, managed markers, module wiring, and integration wiring
* `polepos db upgrade` when you want to apply migrations to the database
* `polepos db revision -m "..."` when you changed models and need a new migration
* `polepos db downgrade` when you need to roll back a migration

### Examples

Concrete scenarios live under [examples/README.md](examples/README.md):

* auth foundation workflow
* PostgreSQL-backed HTML swap workflow

### Help and version

```bash
polepos help
polepos version
```

---

## CLI

```bash
polepos help
polepos start <name> [--install] [--no-bytecode]
polepos startproject <name> [--install] [--no-bytecode]
polepos add module <name>
polepos add integration kafka
polepos add integration rabbitmq
polepos check
polepos db upgrade [target]
polepos db revision -m "<message>"
polepos db downgrade <target>
polepos version
```

---

## Project Structure

```text
myapp/
├─ Dockerfile
├─ compose.yaml
├─ alembic.ini
├─ migrations/
│  └─ versions/
├─ pyproject.toml
├─ .dockerignore
├─ .env.example
├─ src/
│  └─ myapp/
│     ├─ run.py
│     ├─ main.py
│     ├─ app.py
│     ├─ settings.py
│     ├─ bootstrap/
│     ├─ api/
│     ├─ db/
│     ├─ domain/
│     └─ modules/
│        ├─ status/
│        └─ races/
└─ tests/
   ├─ integration/
   └─ unit/
```

---

## Status Endpoint

Check if your service is running:

```http
GET /api/v1/status
```

```json
{
  "status": "ok",
  "service": "myapp",
  "environment": "development",
  "version": "0.1.0",
  "uptime_seconds": 12,
  "timestamp": "2026-04-26T12:00:00Z"
}
```

---

## Philosophy

PolePosition is built around a few principles:

* Lifecycle-oriented: supports project creation, growth, checks, and migrations
* Minimal: no unnecessary abstractions
* Opinionated: sensible defaults
* Extensible: easy to grow into larger systems

The CLI is intentionally lightweight and avoids heavy templating engines. Templates are an implementation detail; the product surface is the project lifecycle.

---

## Roadmap

### Completed Foundations

* [x] `polepos start` project name validation
* [x] Enterprise FastAPI project lifecycle foundation
* [x] `polepos add module` for standard modules
* [x] `polepos add module --template ai-prompt`
* [x] `polepos add module --api-only`
* [x] Clearer `polepos add module` success output
* [x] `polepos add integration kafka`
* [x] `polepos add integration rabbitmq`
* [x] Alembic and database migrations
* [x] Docker and PostgreSQL local runtime support
* [x] `polepos db ...` commands
* [x] Project contract validation through `polepos check`
* [x] Settings-driven CORS support
* [x] JWT-based endpoint authentication foundation
* [x] Structured JSON logging support
* [x] Example scenarios and architecture docs

### Next Up

* [ ] Stronger request-context logging
  path, method, status code, duration, and deeper request correlation
* [ ] Full auth workflow
  login, password hashing, refresh tokens, and database-backed users
* [ ] Production-ready presets
  stronger env defaults, deployment guidance, and safer runtime conventions
* [ ] More `add module` archetypes
  additional focused module shapes beyond standard, API-only, and AI prompt modules

### Later Expansion

* [ ] `ai-openapi` module template
  provider-agnostic prompt orchestration plus external API tool patterns
* [ ] Richer AI provider adapters
  stronger out-of-the-box integrations beyond scaffold-level provider stubs
* [ ] CI and quality presets
  starter workflows for linting, tests, and release automation
* [ ] Broader deployment presets
  reverse proxy, worker/process guidance, and observability-friendly defaults

---

## Example Workflow

Here is a concrete example for a new PostgreSQL-backed FastAPI REST API project.

Create the project and install dependencies:

```bash
uv tool install poleposition
polepos start shop-api
cd shop-api
cp .env.example .env
uv sync
```

Or use the generated Docker workflow:

```bash
docker compose up --build
docker compose run --rm app uv run alembic upgrade head
```

Point the project to PostgreSQL in `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/shop_api
```

Apply the initial migration and start the API:

```bash
polepos db upgrade
uv run python -m shop_api.run
```

Add a new REST module:

```bash
polepos add module customers
```

Extend `src/shop_api/modules/customers/model.py` and `schemas.py` for your domain, then generate and apply a migration:

```bash
polepos db revision -m "add customers table"
polepos db upgrade
```

At that point, your project has:

* FastAPI app structure
* PostgreSQL-ready SQLAlchemy setup
* Alembic migration workflow
* A generated REST module with router, schemas, service, repository, and tests

That is the core PolePosition flow: start fast, add modules as the API grows, and evolve the database schema through the CLI.

### Example: build a `users` REST API

If you want a REST API that returns users, the flow is:

Generate the module:

```bash
polepos add module users
```

Update `src/shop_api/modules/users/model.py` with user fields such as:

```python
class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(default=True)
```

Update `schemas.py` so the API returns those fields, then create and apply a migration:

```bash
polepos db revision -m "create users table"
polepos db upgrade
```

At that point, you already have the generated router shape for:

```text
GET  /api/v1/users/
POST /api/v1/users/
```

From there, you refine the generated module for your actual domain instead of starting from an empty project structure.

---

## Contributing

Contributions are welcome.
Feel free to open an issue or submit a pull request.

---

## License

MIT

[License](https://raw.githubusercontent.com/erenertemden/poleposition/refs/heads/main/LICENSE)
