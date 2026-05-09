# Release and Upgrade Notes

This page explains how to think about PolePosition releases and generated
project upgrades.

## Release Status

PolePosition is currently beta software. The project lifecycle shape is stable
enough for normal use, while some surfaces are intentionally still growing:

- module templates
- opt-in integration scaffolds
- example scenarios
- production hardening guidance

Read [Feature Status](feature-status.md) for the current maturity map.

## Upgrade the CLI

If PolePosition was installed with `uv tool`:

```bash
uv tool upgrade poleposition
```

If it was installed with pip:

```bash
python -m pip install --upgrade poleposition
```

Then verify:

```bash
polepos version
```

## Generated Projects Are Not Auto-Rewritten

Upgrading the CLI does not rewrite an existing generated project. New versions
can add better defaults for future projects and new lifecycle commands, but
existing application code stays under your control.

Use:

```bash
polepos check
```

to verify whether the project still follows the PolePosition lifecycle
contract.

## Module Service Layout

New generated modules use a module-local `services/` package instead of a root
`service.py` file:

```text
src/<package>/modules/customers/
  services/
    __init__.py
    customers_service.py
```

Existing generated projects are not rewritten automatically. If an older module
still uses `service.py`, either keep managing it manually or move the service
class into the new layout and update imports before relying on the latest
`polepos check` lifecycle expectations.

## Recommended Upgrade Flow

For an existing generated project:

```bash
uv tool upgrade poleposition
cd shop-api
polepos check
uv sync
uv run pytest
```

If `polepos check` reports drift, restore the expected file, marker, import,
dependency, setting, or env value. If your team intentionally owns that surface
manually, document the drift in the project.

## When Release Notes Matter Most

Pay close attention to release notes when a change touches:

- generated project structure
- managed markers
- module generation
- integration generation
- Alembic or database command behavior
- `polepos check` expectations

Those areas affect whether lifecycle commands can keep growing a project
safely.

## Generated App Dependency Upgrades

Generated projects declare their own dependencies in the generated
`pyproject.toml`. Upgrade them like normal application dependencies:

```bash
uv add "fastapi[standard]>=0.115.0"
uv sync
uv run pytest
polepos check
```

Review generated migrations before applying them to shared environments.

## Changelog

Repository changes are summarized in the
[Changelog](https://github.com/erenertemden/poleposition/blob/main/CHANGELOG.md).
