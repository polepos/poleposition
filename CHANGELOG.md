# Changelog

Notable PolePosition changes are tracked here.

PolePosition follows Conventional Commits in repository history. This changelog
summarizes user-facing behavior, release readiness work, and known beta scope.

## 0.0.44 - 2026-06-14

### Added

- `polepos delete <name>` removes a whole generated project directory,
  including its in-project virtual environment. It only deletes a directory
  that contains a `.poleposition.toml` manifest, refuses to delete the current
  directory or a parent of it, and asks for confirmation unless `--force` is
  given. Use `--trace` (alias `--dry-run`) to preview the target without
  deleting anything.

### Documentation

- Documented the colorized CLI terminal output and the `NO_COLOR` /
  `FORCE_COLOR` overrides in the CLI reference.

## 0.0.43 - 2026-06-14

### Changed

- Repointed all repository, raw-asset, documentation-site, and PyPI Trusted
  Publisher references to the `polepos` GitHub organization across
  `pyproject.toml`, the README, the docs site config, and the documentation.
  The CODEOWNERS personal maintainer handle is unchanged.

## 0.0.42 - 2026-06-14

### Added

- Colorized, semantic terminal output for the CLI. A new stdlib-only console
  layer routes success, error, warning, heading, field, item, and step messages
  through consistent colors and glyphs. Styling is TTY-gated and honors
  `NO_COLOR` and `FORCE_COLOR`, so piped output, CI logs, and `--json` results
  stay byte-identical plain text. No new runtime dependencies were added.

### Fixed

- The `ai-prompt` scaffold no longer hard-codes `llm_provider="openai"` and a
  specific `llm_model`. Both default to empty strings, consistent with the
  provider-agnostic contract, so the explicit provider choice surfaces at the
  factory boundary instead of silently committing to one provider.
- `polepos version` and `pole_position.__version__` are now derived from the
  installed package metadata, fixing a drift where the reported version lagged
  behind `pyproject.toml`. Releases keep bumping `pyproject.toml` only and the
  CLI follows automatically.

### Changed

- The release workflow now guards the published tag against package version
  drift, failing the release if the tag does not match the `pyproject.toml`
  version.

## 0.0.41 - 2026-06-08

### Fixed

- `polepos remove module` no longer dead-ends with "Module does not exist"
  when the module directory was already deleted. It now cleans the orphan
  references `polepos check` reports (module exports, router wiring, model
  imports, and generated tests) even for a mis-detected template or a
  hand-edited reference shape.
- Removing a module no longer scrubs references belonging to a different
  module whose name shares a prefix (removing `user` leaves `users` intact).

### Added

- Generated projects now fail settings validation when `APP_ENV=production`
  and `AUTH_SECRET_KEY` is still the default `change-me-in-production` value,
  so the app cannot boot with an insecure secret.

### Changed

- Pinned the `qs` documentation dev dependency to a patched version.

### Documentation

- Added contributor and maintainer guides and a code-style reference, removed
  the agent recommendation guide, and documented the lifecycle manifest,
  dependency patching, and managed-import sorting. The published README now
  matches the GitHub repository.

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
