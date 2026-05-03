# PolePosition

PolePosition is a project lifecycle CLI for starting and growing enterprise
FastAPI projects without losing the clarity of a normal FastAPI codebase.

It helps teams create a project, add modules, wire integrations, validate the
project contract, and keep database migration workflows first-class as the
application grows.

## Core Workflow

```bash
polepos start shop-api
cd shop-api
cp .env.example .env
uv sync
polepos db upgrade
uv run python -m shop_api.run
```

Then add domain modules as the product grows:

```bash
polepos add module customers
polepos check
polepos db revision -m "add customers table"
polepos db upgrade
```

## What PolePosition Gives You

- FastAPI-native application structure
- Module-oriented organization for domain growth
- Settings, logging, middleware, and exception wiring
- SQLAlchemy and Alembic migration foundations
- JWT-based authentication foundations
- Optional integration scaffolds for Kafka, RabbitMQ, and LLM adapters
- Read-only project contract checks
- A dedicated runtime entrypoint with `uv run python -m <package>.run`

## Documentation Map

- [Getting Started](getting-started.md): create and run a project.
- [CLI Reference](cli.md): command groups and common usage.
- [Architecture](architecture.md): generated project structure and design intent.
- [Architecture Diagram](architecture-diagram.md): visual CLI and generated project flow.
- [Project Checks](project-checks.md): what `polepos check` validates.
- [Feature Status](feature-status.md): implemented and planned behavior.
- [Examples](examples/index.md): scenario-oriented usage guides.
