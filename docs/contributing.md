# Contributing

This guide is for contributing to **PolePosition itself** (the CLI and its
generated templates) — not for the FastAPI projects PolePosition generates.

Contributions are welcome: open an
[issue](https://github.com/polepos/poleposition/issues) or a
[pull request](https://github.com/polepos/poleposition/pulls).

## Development setup

PolePosition targets Python 3.10+ and has no runtime dependencies. Install it in
editable mode together with the test and lint tools:

```bash
git clone https://github.com/polepos/poleposition.git
cd poleposition

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

python -m pip install -e .           # installs the polepos / poleposition CLIs
python -m pip install pytest ruff    # test runner + linter/formatter
```

After this, the `polepos` and `poleposition` commands are available and run from
your working copy.

## Running the tests

The repository test suite is the primary validation layer. From the repo root:

```bash
python -m pytest                     # full unit/integration suite
python -m pytest pole_position/tests/test_check_command.py   # a single file
```

End-to-end tests are **opt-in** because they generate real projects and need
extra tooling. They are skipped by default:

```bash
# Non-Docker e2e (requires `uv` on PATH)
POLEPOSITION_RUN_E2E=1 python -m pytest -m "e2e and not docker_e2e"

# Docker e2e (also requires Docker + Docker Compose)
POLEPOSITION_RUN_E2E=1 POLEPOSITION_RUN_DOCKER_E2E=1 \
    python -m pytest -m docker_e2e
```

When you change behavior, add or update tests next to the area you touched
(`test_cli.py`, `test_startproject.py`, `test_add_module.py`,
`test_check_command.py`, `test_project_checker.py`, `test_db_commands.py`, …).

## Code style

Python code follows the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html),
enforced with [Ruff](https://docs.astral.sh/ruff/). The `CI` workflow fails on
any violation, so run it before pushing:

```bash
ruff check pole_position polepos
ruff format pole_position polepos
```

See [Code Style](code-style.md) for the full rule set and rationale.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <summary>`.
Keep the summary short, imperative, and lower-case after the type (≤72 chars).

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci`, `perf`
- **Scopes:** `cli`, `start`, `add`, `check`, `db`, `template`, `docs`, `tests`

```text
feat(template): add generated agent guidance
fix(add): require integration managed markers before patching
test(check): cover missing integration env markers
```

Avoid vague subjects like `updates`, `fix stuff`, or `wip`.

## Where things live

| Area | Location |
|---|---|
| CLI entrypoint and command registry | `pole_position/cli/main.py`, `pole_position/cli/registry.py` |
| Commands (thin argument parsing) | `pole_position/cli/commands/` |
| Services (the actual logic) | `pole_position/cli/services/` |
| Generated project templates | `pole_position/template/` |
| Optional runtime data structures | `polepos/data/` |
| Tests | `pole_position/tests/` |

## Common tasks

**Add a CLI command** — add a command file under the right namespace, register
it in the root or subcommand registry, add tests, and update the README if it is
user-facing.

**Change module generation/removal** — update
`cli/services/module_creator.py` (and `module_remover.py` for removal); verify
router wiring, model wiring, test generation, and cleanup symmetry; update
`test_add_module.py` / `test_remove_module.py`.

**Change project checks** — update `cli/services/project_checker.py`, keep
checks read-only and file-based, update `test_check_command.py` /
`test_project_checker.py`, and keep [Project Checks](project-checks.md) aligned.

**Improve a generated template** — edit files under `pole_position/template/`,
confirm placeholders still render, and update `test_startproject.py`.

## Pull request checklist

1. Tests pass: `python -m pytest`
2. Lint/format clean: `ruff check pole_position polepos` and `ruff format pole_position polepos`
3. Docs updated when behavior changes (README, and the relevant `docs/` page)
4. Commit messages follow Conventional Commits

For deeper internals and the maintainer-level rule set, see
[Architecture](architecture.md) and
[`AGENTS.md`](https://github.com/polepos/poleposition/blob/main/AGENTS.md).
