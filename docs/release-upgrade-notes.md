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

Use `polepos upgrade` inside a generated project for a read-only readiness
report that includes the CLI version, package, database mode, recorded module
templates, enabled integrations, and current `polepos check` status.

## Publish a Release

Repository releases publish to PyPI through GitHub Actions and PyPI Trusted
Publishing. The workflow is `.github/workflows/release.yml`, and it runs when a
GitHub release is published.

Before the first trusted publish, configure the existing PyPI project with a
GitHub Actions Trusted Publisher:

```text
PyPI project: poleposition
Owner: polepos
Repository: poleposition
Workflow name: release.yml
Environment name: pypi
```

The release workflow builds the source distribution and wheel, checks the
package metadata with `twine check`, and publishes through
`pypa/gh-action-pypi-publish` without a `PYPI_API_TOKEN` secret. The publish job
is the only job with `id-token: write`; keep that permission scoped to the
publish job if the workflow grows.

The `pypi` GitHub Actions environment is intentionally part of the trusted
publisher identity. Configure any required reviewer or branch/tag restrictions
on that environment in GitHub before relying on automated publishing.

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
polepos upgrade
polepos check --fix
polepos check
uv sync --extra dev
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
uv sync --extra dev
uv run pytest
polepos check
```

Review generated migrations before applying them to shared environments.

## Changelog

Repository changes are summarized in the
[Changelog](https://github.com/polepos/poleposition/blob/main/CHANGELOG.md).
