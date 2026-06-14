# Maintainer Guide

This page surfaces the maintainer-level conventions that govern changes to
PolePosition. It complements the [Architecture](architecture.md) (how the system
works) and [Contributing](contributing.md) (how to set up and submit changes)
pages by explaining the *rules and invariants* a change should respect.

The canonical, exhaustive version lives in
[`AGENTS.md`](https://github.com/polepos/poleposition/blob/main/AGENTS.md)
at the repository root. It is also bundled into generated projects so coding
agents working inside a scaffolded app follow the same conventions. When this
page and `AGENTS.md` disagree, `AGENTS.md` wins.

## Invariants to protect

- **`polepos check` stays read-only.** It must report drift without a running
  database, broker, LLM provider, network access, or optional integration
  dependency — no installs, migrations, or mutations of the generated project.
- **`remove module` is a file operation, not a database operation.** It never
  opens a connection, drops tables, deletes data, or rewrites Alembic history.
- **Managed markers are a contract.** PolePosition only inserts before the
  `# polepos:*` markers; never reformat or relocate them in a way that breaks
  `add` / `remove` patching. See
  [Managed Block Contract](architecture.md#managed-block-contract).
- **Migration-first.** Schema changes flow through reviewed Alembic migrations,
  not auto-applied DDL.

## Conventions

- **Commit messages** — [Conventional Commits](https://www.conventionalcommits.org/)
  with the project's preferred types and scopes (see
  [Contributing](contributing.md#commit-messages)).
- **CLI shape** — keep commands consistent; prefer changes that improve the
  end-to-end developer workflow and keep the generated app understandable to a
  FastAPI developer.
- **Documentation expectations** — update the README and the relevant `docs/`
  page whenever user-facing behavior changes (CLI commands, setup steps,
  database workflow, generated structure, example workflows).
- **Testing expectations** — the repo test suite is the main validation layer;
  add or update tests next to the area you change. See
  [Contributing → Running the tests](contributing.md#running-the-tests).

## When changing a subsystem

`AGENTS.md` includes step-by-step checklists ("Common Agent Tasks") for the
recurring changes — adding a CLI command, changing module generation or removal,
changing database command behavior, changing project-check behavior, and
improving a generated template. Each lists the files and tests to touch. Use
those checklists as the source of truth for which files a change must keep in
sync.

## Things that do not exist yet

Do not assume these are implemented unless you add them (with docs and tests):

- `polepos delete module`
- production presets

For the full ruleset, read
[`AGENTS.md`](https://github.com/polepos/poleposition/blob/main/AGENTS.md).
