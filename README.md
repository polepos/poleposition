# PolePosition

![PolePosition logo](assets/logo/poleposition-python-logo.svg)

A CLI tool that puts teams in pole position when starting enterprise FastAPI projects.

PolePosition helps you keep FastAPI's speed while avoiding the usual setup drag of enterprise backend work. It gives you a structured, production-minded starting point from day one.

Create a new project:

```bash
polepos start myapp --install
```

If you prefer not to generate Python bytecode while developing locally:

```bash
polepos start myapp --no-bytecode
```
[![PyPI version](https://img.shields.io/pypi/v/poleposition)](https://pypi.org/project/poleposition)
[![Python](https://img.shields.io/pypi/pyversions/poleposition)](https://pypi.org/project/poleposition)
[![License](https://img.shields.io/github/license/erenertem/poleposition)](https://raw.githubusercontent.com/erenertemden/poleposition/refs/heads/main/LICENSE)

---

## Example Output

```bash
$ polepos start myapp --install
Created project: myapp

Installing project dependencies with uv...
Dependencies installed successfully.

Next steps:
  cd myapp
  cp .env.example .env
  alembic upgrade head
  uv run python -m myapp.run
```

## Why PolePosition?

PolePosition is named for the same reason teams use it: to start enterprise FastAPI development from pole position.

FastAPI projects should start fast, clean, and predictable, even when the target is a larger production system.

PolePosition provides:

* A scalable project structure
* Environment-based configuration
* Alembic-based database migrations
* Built-in logging
* Testing setup
* Module-oriented organization for growing codebases
* A ready-to-run FastAPI application

No boilerplate. No setup friction.

---

## Why not just FastAPI?

FastAPI is excellent, but starting a new project often involves:

* Recreating the same structure
* Setting up logging and configuration
* Defining module boundaries
* Wiring database foundations
* Organizing modules manually

PolePosition removes that overhead by providing a clean, production-ready starting point out of the box.

---

## Installation

PolePosition follows a `uv`-first workflow for installation, dependency sync, migrations, and local development.

```bash
uv tool install poleposition
```

or

```bash
pip install poleposition
```

---

## Quick Start

```bash
polepos start myapp --install
cd myapp
cp .env.example .env
alembic upgrade head

uv run python -m myapp.run
```

Or start the generated app with Docker and PostgreSQL:

```bash
docker compose up --build
docker compose run --rm app uv run alembic upgrade head
```

Create and run migrations:

```bash
alembic upgrade head
alembic revision --autogenerate -m "add garage table"
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

`--install` runs `uv sync` inside the generated project for you.
`--no-bytecode` configures the generated runner, Alembic entrypoint, and test
fixture setup to disable Python bytecode writes during common local workflows.

Project names:

* Must not be empty
* Must not contain whitespace
* May use hyphens like `my-app`
* Are normalized to a Python package name like `my_app`

### Manual setup

```bash
polepos start myapp
cd myapp

cp .env.example .env
uv sync
alembic upgrade head

uv run python -m myapp.run
```

### Add modules

```bash
polepos add module garage
```

### Database commands

```bash
polepos db upgrade
polepos db revision -m "add garage table"
polepos db downgrade -1
```

### Docker workflow

Generated projects include a `Dockerfile`, `.dockerignore`, and `compose.yaml`
so you can start the app with PostgreSQL in containers.

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm app uv run alembic upgrade head
```

The compose setup uses the generated `run.py` entrypoint and overrides
`DATABASE_URL` so the app talks to the bundled PostgreSQL service.

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

### When to use which command

* `polepos start` when you want to create a new FastAPI project with the PolePosition structure
* `polepos add module` when you want to add a new REST/domain module to an existing project
* `polepos db upgrade` when you want to apply migrations to the database
* `polepos db revision -m "..."` when you changed models and need a new migration
* `polepos db downgrade` when you need to roll back a migration

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

* Minimal: no unnecessary abstractions
* Opinionated: sensible defaults
* Extensible: easy to grow into larger systems

The CLI is intentionally lightweight and avoids heavy templating engines.

---

## Roadmap

* [x] Project name validation
* [x] `polepos add module`
* [x] Alembic and database migrations
* [x] Docker support
* [x] `polepos db ...` commands
* [ ] JSON logging support
* [ ] Auth foundation
* [ ] Production-ready presets

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
