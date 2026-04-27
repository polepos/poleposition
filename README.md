# PolePosition

A CLI tool that puts teams in pole position when starting enterprise FastAPI projects.

PolePosition helps you keep FastAPI's speed while avoiding the usual setup drag of enterprise backend work. It gives you a structured, production-minded starting point from day one.

Create a new project:

```bash
polepos start myapp --install
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
  uv run fastapi dev src/myapp/main.py
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

uv run fastapi dev src/myapp/main.py
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

uv run fastapi dev src/myapp/main.py
```

### Help and version

```bash
polepos help
polepos version
```

---

## CLI

```bash
polepos help
polepos start <name> [--install]
polepos startproject <name> [--install]
polepos version
```

---

## Project Structure

```text
myapp/
├─ alembic.ini
├─ migrations/
│  └─ versions/
├─ pyproject.toml
├─ .env.example
├─ src/
│  └─ myapp/
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
* [ ] Docker support
* [ ] `polepos db ...` commands
* [ ] JSON logging support
* [ ] Auth foundation
* [ ] Production-ready presets

---

## Contributing

Contributions are welcome.
Feel free to open an issue or submit a pull request.

---

## License

MIT

[License](https://raw.githubusercontent.com/erenertemden/poleposition/refs/heads/main/LICENSE)
