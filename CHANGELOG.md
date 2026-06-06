# Changelog

Notable PolePosition changes are tracked here.

PolePosition follows Conventional Commits in repository history. This changelog
summarizes user-facing behavior, release readiness work, and known beta scope.

## 0.0.40 - 2026-06-06

### Changed

- Adopted the Google Python Style Guide across the codebase, enforced with Ruff
  (lint and format) and a dedicated CI lint gate. No CLI behavior changed.

### Documentation

- Added a contributor guide, a maintainer guide, and a code-style reference to
  the documentation site, and documented the lifecycle manifest and dependency
  patching in the architecture reference.
- Refreshed the published README so PyPI matches the GitHub repository
  (resolves #39).

## 0.0.39 - 2026-06-04

### Fixed

- Made `polepos.data.Graph` traversals (`bfs`, `dfs`, `shortest_path`,
  `topological_sort`) deterministic by storing adjacency in insertion order, so
  results no longer vary across processes with `PYTHONHASHSEED`.
- `polepos.data` graph traversals now raise a clear `ValueError` for an unknown
  start node instead of a bare `KeyError`.
- Made `UnionFind.find` iterative to avoid `RecursionError` on deep chains.
- Made `SortedList.irange` a lazy generator consistent with `SortedDict`, and
  stopped `SortedSet.irange` from rebuilding a `SortedList` on every call.
- Hardened `polepos remove module` router-wiring parsing with guarded
  `ast.parse`, removed dead code, and de-duplicated the legacy `races`
  generated-test path handling.

### Added

- Added `polepos remove module <name>` for removing generated modules and their
  managed router, export, test, and model wiring.
- Added a Docker/PostgreSQL end-to-end job to the E2E workflow so the
  containerized migration smoke test runs in CI.
- Added documentation pages for troubleshooting, configuration, integration
  guides, and release or upgrade notes.
- Added a database and migrations guide for the `polepos db` lifecycle.
- Added a Spring Boot and ASP.NET Core module structure guide for teams new to
  PolePosition and FastAPI.
- Added CI coverage reporting with `pytest-cov` and uploaded coverage XML
  artifacts.
- Documented CI, E2E, docs deploy, and coverage behavior in the README.

### Changed

- Removed the generated `profile` and `races` sample modules from the default
  project template, while keeping the auth foundation, status module, and
  Alembic migration infrastructure.
- Aligned project creation next steps and generated README migration workflow
  around `polepos db upgrade`.
- Hardened `polepos add integration ...` preflight checks so unsupported
  dependency layouts are reported before generated files or settings are
  written.

### Notes

- Versions 0.0.28 through 0.0.38 were incremental development bumps that were not
  individually changelogged; see the git history for details.

## 0.0.27 - 2026-05-05

### Added

- Added GitHub Actions test CI for Python `3.10`, `3.11`, `3.12`, `3.13`, and
  `3.14`.
- Added docs strict build coverage in CI.
- Added a non-Docker e2e workflow for generated-project lifecycle smoke tests.
- Added generated `AGENTS.md` guidance so coding agents check PolePosition
  lifecycle commands before manually scaffolding modules, integrations, checks,
  or migrations.
- Expanded README positioning for teams coming from Spring Boot or ASP.NET Core.

### Changed

- Hardened TOML dependency patching for generated project `pyproject.toml`
  updates.
- Added preflight marker checks before integration patching so drift is reported
  before generated files are partially written.
- Tightened `polepos start` option parsing.
- Documented the repository commit message standard.
- Moved the package classifier to `Development Status :: 4 - Beta`.

### Notes

- The PolePosition CLI supports Python `>=3.10`.
- Generated FastAPI projects target Python `>=3.11`.
- Docker/PostgreSQL e2e coverage should be confirmed in a Docker-capable
  environment before publishing a beta release.
