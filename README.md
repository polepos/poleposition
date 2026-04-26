# PolePosition

A CLI tool to quickly scaffold production-ready FastAPI projects.

Create a clean, structured API project in seconds with built-in logging, configuration, and testing.

Create a new project:

```bash
polepos start myapp --install
```
[![PyPI version](https://img.shields.io/pypi/v/poleposition)](https://pypi.org/project/poleposition)
[![Python](https://img.shields.io/pypi/pyversions/poleposition)](https://pypi.org/project/poleposition)
[![License](https://img.shields.io/github/license/erenertem/poleposition)](https://raw.githubusercontent.com/erenertemden/poleposition/refs/heads/main/LICENSE)

---

## Example output

```bash
$ polepos start myapp --install
Created project: myapp

Installing project dependencies with uv...
Resolved 47 packages in 40ms
Installed 47 packages in 52ms

Project ready.

Next steps:
  cd myapp
  uv run fastapi dev src/myapp/main.py
```


## Why PolePosition?

Starting a FastAPI project should be fast, clean, and predictable.

PolePosition provides:

* A scalable project structure
* Environment-based configuration
* Built-in logging
* Testing setup
* A ready-to-run FastAPI application

No boilerplate. No setup friction.

---

## Why not just FastAPI?

FastAPI is excellent, but starting a new project often involves:

* Recreating the same structure
* Setting up logging and configuration
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

## Quick example

```bash
polepos start myapp --install
cd myapp

uv run fastapi dev src/myapp/main.py
```

Open your API documentation:

```
http://127.0.0.1:8000/docs
```

---

## Quickstart

### One-command setup (recommended)

```bash
polepos start myapp --install
cd myapp

uv run fastapi dev src/myapp/main.py
```

### Manual setup

```bash
polepos start myapp
cd myapp

cp .env.example .env
uv sync

uv run fastapi dev src/myapp/main.py
```

---

## CLI

```bash
polepos start <name> [--install]
polepos version
```

---

## Project Structure

```text
myapp/
├─ pyproject.toml
├─ .env.example
├─ src/
│  └─ myapp/
│     ├─ main.py
│     ├─ app.py
│     ├─ api/
│     │  └─ routes/
│     │     └─ status.py
│     └─ core/
│        ├─ config.py
│        └─ logging.py
└─ tests/
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
  "version": "0.1.0"
}
```

---

## Philosophy

PolePosition is built around a few principles:

* Minimal — no unnecessary abstractions
* Opinionated — sensible defaults
* Extensible — easy to grow into larger systems

The CLI is intentionally lightweight and avoids heavy templating engines.

---

## Roadmap

* [x] Project name validation
* [ ] `poleposition add module`
* [ ] JSON logging support
* [ ] Docker support
* [ ] Production-ready presets

---

## Contributing

Contributions are welcome.
Feel free to open an issue or submit a pull request.

---

## License

MIT

[License](https://raw.githubusercontent.com/erenertemden/poleposition/refs/heads/main/LICENSE)
