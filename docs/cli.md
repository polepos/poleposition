# CLI Usage and Options

PolePosition keeps the top-level command surface small, but each command is
part of a project lifecycle. Use this page like a command-line reference:
start with the synopsis, then jump to the command group you need.

```text
polepos <command> [options]
polepos help [command] [subcommand]
```

Use focused help when you are in the terminal:

```bash
polepos help
polepos help start
polepos help add module
polepos help remove module
polepos help db revision
```

## Common Workflows

Create and run a database-backed project:

```bash
polepos start shop-api
cd shop-api
cp .env.example .env
uv sync --extra dev
polepos db upgrade
uv run python -m shop_api.run
```

Add a new domain module and migrate its model changes:

```bash
polepos add module customers
polepos check
polepos db revision -m "add customers table"
polepos db upgrade
```

Create an API-only project for integration or worker examples:

```bash
polepos start kafka-quick-start --db none
cd kafka-quick-start
cp .env.example .env
uv sync --extra dev
polepos add integration kafka
polepos add module greetings --api-only
polepos check
```

## Command Overview

| Command | Purpose |
| --- | --- |
| `polepos start` | Create a new generated FastAPI project. |
| `polepos add module` | Add a module under `src/<package>/modules/`. |
| `polepos add auth` | Add optional database-backed auth scaffolding. |
| `polepos add integration` | Add Kafka, RabbitMQ, Redis, or RQ scaffolding. |
| `polepos remove module` | Remove generated module files and managed wiring. |
| `polepos check` | Validate the generated project contract. |
| `polepos db` | Run Alembic migration commands through the generated project. |
| `polepos upgrade` | Print a read-only project upgrade readiness report. |
| `polepos version` | Print the installed CLI version. |
| `polepos completion` | Print a bash, zsh, or fish completion script. |
| `polepos help` | Print detailed CLI usage. |

## Project Creation

```bash
polepos start <project_name> [--install] [--no-bytecode] [--db sqlite|postgres|none]
polepos startproject <project_name> [--install] [--no-bytecode] [--db sqlite|postgres|none]
```

`startproject` is an alias for `start`.

| Option | Behavior |
| --- | --- |
| `--install` | Install generated project dependencies after creation. It uses `uv sync --extra dev` when `uv` is available; otherwise it creates `.venv` and installs with `pip`. |
| `--no-bytecode` | Configure generated local runtime and migration commands to start with `PYTHONDONTWRITEBYTECODE=1`. |
| `--db sqlite` | Generate the default DB-ready starter with SQLAlchemy, Alembic, migrations, and SQLite `DATABASE_URL`. |
| `--db postgres` | Generate the DB-ready starter with PostgreSQL-oriented `DATABASE_URL` and Docker database naming. |
| `--db none` | Omit SQLAlchemy, Alembic, migrations, `DATABASE_URL`, and generated `db/` wiring. |

Project names must not be empty, contain whitespace, contain path separators,
or use characters outside letters, digits, hyphen, and underscore. Hyphenated
project names are normalized to Python package names:

```text
shop-api -> shop_api
```

Examples:

```bash
polepos start shop-api
polepos start shop-api --install
polepos start shop-api --db postgres
polepos start webhook-gateway --db none
```

## Add Commands

```bash
polepos add <subcommand>
```

Subcommands:

| Subcommand | Purpose |
| --- | --- |
| `auth` | Add optional database-backed registration and token scaffolding. |
| `integration` | Add an external-system integration scaffold. |
| `module` | Add a generated module to the current project. |

### `polepos add module`

```bash
polepos add module <module_name> [--template <template_name>] [--api-only] [--service-only]
polepos add module <module_name> --template crud [--pagination] [--timestamps]
polepos add module <module_name> --template crud [--soft-delete] [--tenant-scoped]
polepos add module <module_name> --template crud [--auth-required]
```

The command creates module files, generated tests, module exports, API router
wiring, and database model discovery wiring when the selected template has a
model. The `service-only` template is internal and skips the API router wiring
while still updating database model discovery.

| Option | Behavior |
| --- | --- |
| `--template standard` | Default REST-friendly module with model, repository, schemas, service, router, and tests. |
| `--template crud` | Fuller CRUD module with collection, detail, create, update, delete, repository, service, and tests. |
| `--template api-only` | Router, schemas, service, and tests without model, repository, or database wiring. |
| `--template ai-prompt` | LLM-oriented module skeleton plus shared provider-agnostic `integrations/llm` files when missing. |
| `--template service-only` | Internal database-backed module with model, repository, service, and tests but no router, schemas, or API wiring. |
| `--api-only` | Shortcut for `--template api-only`. |
| `--service-only` | Shortcut for `--template service-only`. |
| `--pagination` | CRUD-only. Adds `limit`/`offset` query params and a `<ClassName>Page` response envelope. |
| `--timestamps` | CRUD-only. Adds `created_at` and `updated_at` columns and response fields. |
| `--soft-delete` | CRUD-only. Adds `deleted_at` and changes delete behavior to mark rows deleted. |
| `--tenant-scoped` | CRUD-only. Adds `tenant_id` and filters list/get/update/delete by tenant query parameter. |
| `--auth-required` | CRUD-only. Protects generated CRUD routes with the starter bearer auth dependency. |

Examples:

```bash
polepos add module customers
polepos add module customers --template crud
polepos add module customers --template crud --pagination --timestamps
polepos add module customers --template crud --soft-delete --tenant-scoped --auth-required
polepos add module webhooks --api-only
polepos add module notifications --service-only
polepos add module assistant --template ai-prompt
```

After adding a database-backed module, edit the generated model for the real
domain and create a reviewed migration:

```bash
polepos db revision -m "add customers table"
polepos db upgrade
polepos check
```

For detailed template layouts, CRUD feature behavior, generated schema names,
and safe customization guidance for renaming or deleting generated schema
classes, see [Module Templates](module-templates.md).

### `polepos add auth`

```bash
polepos add auth
```

`add auth` creates the optional database-backed auth workflow:

- auth user model
- password hashing helper
- repository and service
- registration and token router
- schemas and tests
- dependency, router, and model wiring

It requires a generated database layer. Projects created with `--db none` need
an explicit database layer before this command can apply cleanly.

For scope and migration guidance, see [Auth Workflow](auth-workflow.md).

### `polepos add integration`

```bash
polepos add integration <integration_name>
```

Supported integration names:

| Integration | Adds |
| --- | --- |
| `kafka` | `aiokafka` dependency, Kafka producer/consumer helpers, settings, env examples, and in-memory test double. |
| `rabbitmq` | `aio-pika` dependency, publisher/consumer helpers, settings, env examples, and in-memory test double. |
| `redis` | `redis` dependency, async cache helper, settings, env examples, and in-memory test double. |
| `rq` | `rq` dependency, Redis-backed queue helper, worker entrypoint, settings, env examples, and test double. |

Examples:

```bash
polepos add integration kafka
polepos add integration rabbitmq
polepos add integration redis
polepos add integration rq
```

Long-running consumers and workers are intentionally explicit runtime
processes. PolePosition does not start Kafka consumers, RabbitMQ workers, Redis
workers, or RQ workers inside the API process by default.

See the [Integration Guides](integrations/index.md) for per-integration details.

## Remove Commands

```bash
polepos remove <subcommand>
polepos remove module <module_name> [--force] [--trace] [--wiring-only]
```

`remove module` removes generated module files, generated tests, manifest
metadata, module exports, API router wiring, and database-backed module model
imports.

| Option | Behavior |
| --- | --- |
| `--trace` | Show planned removals and updates without changing files. |
| `--force` | Remove module files even when custom changes are detected. |
| `--wiring-only` | Remove managed wiring and generated tests, but keep the module directory. |

Examples:

```bash
polepos remove module customers
polepos remove module customers --trace
polepos remove module customers --wiring-only
polepos remove module customers --force
```

The remover is file-based and conservative. It stops before deleting module
files when custom changes or unmanaged references are detected. If you manually
deleted the module directory, rerun `polepos remove module <name>` to clean
remaining generated tests, manifest metadata, and managed wiring.

If an expected generated file can no longer be decoded as text, `remove module`
treats it as a modified generated file. A normal remove stops before deleting
it; `--force` can still remove the module directory when that is intentional.

For CRUD modules generated with options such as `--pagination` or
`--tenant-scoped`, the manifest records the selected options as part of the
module template value, for example `crud[pagination,tenant-scoped]`. The
remover uses that metadata when comparing generated files against the expected
template variant.

The command does not mutate the live database. If a removed module had a model
and you want to remove its table, create and review an Alembic migration
separately:

```bash
polepos remove module customers
polepos db revision -m "remove customers table"
polepos db upgrade
```

## Delete Command

```bash
polepos delete <project_name>
polepos delete <project_name> --trace
polepos delete <project_name> --force
```

`delete` removes a whole generated project directory, including its in-project
`.venv` (both `uv` and pip create the virtual environment inside the project,
so deleting the directory removes the environment too). Use it to discard a
project created with the wrong name or configuration and start fresh.

It is intentionally cautious:

- It only deletes a directory that contains a `.poleposition.toml` manifest, so
  it will not remove an arbitrary, unrelated folder. If the manifest is missing,
  it refuses and asks you to delete the directory manually.
- It refuses to delete the current directory or a parent of it, so run it from
  outside the project (for example from the directory where you ran
  `polepos start`).
- Without `--force`, it asks for confirmation (`[y/N]`, default no) and aborts
  on any answer other than `y`.

Use `--trace` (alias `--dry-run`) to preview the directory that would be removed
without deleting anything. Use `--force` (alias `-y`) to skip the confirmation
prompt in scripts.

`delete` only removes local files; it never changes a database. Removing a
project does not drop any external database it pointed at.

## Project Checks

```bash
polepos check [--json] [--fix]
```

`check` validates generated structure, managed markers, Alembic configuration,
starter routing, added module wiring, generated tests, orphan generated
references, and supported integration scaffolds. It works from the project root
or nested directories inside a PolePosition project.

| Option | Behavior |
| --- | --- |
| `--json` | Print a machine-readable result and exit non-zero when validation fails. |
| `--fix` | Restore safe PolePosition-managed markers before validation. |

Examples:

```bash
polepos check
polepos check --json
polepos check --fix
```

Failed checks include `PPCHK` issue codes and `Fix:` hints. The command does
not install dependencies, run migrations, contact brokers, call LLM providers,
or mutate files unless `--fix` is supplied.

`--fix` is limited to safe managed-marker restoration. In `api/router.py`, it
places the router include marker after the complete `api_router.include_router(...)`
statement, including multi-line calls.

For check layers and issue behavior, see [Project Checks](project-checks.md).

## Database Commands

```bash
polepos db <subcommand>
```

Subcommands:

| Command | Behavior |
| --- | --- |
| `polepos db status` | Print Alembic current revision and heads. |
| `polepos db upgrade [target]` | Apply migrations. Default target: `head`. |
| `polepos db revision -m "<message>"` | Create an autogenerated Alembic revision. |
| `polepos db downgrade <target>` | Revert migrations to the selected target. |

Examples:

```bash
polepos db status
polepos db upgrade
polepos db upgrade head
polepos db revision -m "add customers table"
polepos db downgrade -1
polepos db downgrade base
```

Database commands prefer `uv run alembic ...` when `uv` is available. Without
`uv`, they fall back to the active virtualenv, the generated project `.venv`,
or the first `python` on `PATH`.

Review autogenerated migrations before applying them. For advanced Alembic
flags not exposed by PolePosition, run `uv run alembic ...` directly inside the
generated project.

For full schema workflow guidance, see [Database and Migrations](database.md).

## Upgrade and Version

```bash
polepos upgrade
polepos version
polepos --version
```

`upgrade` is read-only. It reports the CLI version, project root, package,
database mode, recorded modules, enabled integrations, current check status,
and next-step commands.

`version` prints the installed PolePosition package version.

See [Upgrade Reports](upgrade-command.md) and
[Release and Upgrade Notes](release-upgrade-notes.md) for upgrade guidance.

## Shell Completion

```bash
polepos completion <bash|zsh|fish>
```

`completion` prints a tab-completion script for the chosen shell. The script is
thin: it calls back into PolePosition for every completion, so the candidates
are always derived from the live command tree. Adding a command, subcommand, or
flag updates completion automatically, with no separate list to maintain.

Completion covers command names, subcommands, flags, `--template` and `--db`
values, integration names, the supported shells, and the current project's
module names for `polepos remove module`.

Install it for your shell:

```bash
# bash (requires bash-completion)
polepos completion bash >> ~/.bashrc

# zsh (save onto a directory in your $fpath, then restart the shell)
polepos completion zsh > ~/.zfunc/_polepos

# fish
polepos completion fish > ~/.config/fish/completions/polepos.fish
```

To try it in the current shell without installing, source it directly:

```bash
source <(polepos completion bash)
```

Completion works for both the `polepos` and `poleposition` entry points.

## Option Conventions

- Commands fail fast on unexpected arguments or unknown options.
- Long options with values generally accept the space-separated form, such as
  `--db postgres` or `--template crud`.
- `polepos start` also accepts `--db=postgres`.
- `polepos add module` also accepts `--template=crud`.
- Commands that operate on an existing project use project-root discovery from
  nested directories.
- `polepos check` is the lifecycle validator; there is no separate
  `polepos validate` command.

## Terminal Output

The CLI styles its own output with simple ANSI colors and status glyphs: green
`✓` for success, red `✗` for errors, yellow `!` for warnings, cyan `→` for
next-step hints, bold section headings, and dim field labels and list items.
The styling uses only the standard library, so the CLI stays dependency-free.

Color is applied only when standard output is an interactive terminal, so piped
output, CI logs, the test suite, and `polepos check --json` receive the same
plain, byte-identical text as before. Two environment variables override the
detection:

- `NO_COLOR` (set to any value) disables all color and glyphs. It takes
  precedence over `FORCE_COLOR`.
- `FORCE_COLOR` (set to any value) forces colored output even when standard
  output is not an interactive terminal.

This styling affects only the CLI. It is independent of the generated
application's logging format, which is configured separately with `LOG_FORMAT`.

## Safe Customization Boundary

PolePosition generates normal FastAPI application code. Customize module
models, schemas, repositories, services, routers, tests, and migrations for the
real domain. Keep managed marker comments and generated wiring shapes intact if
you want lifecycle commands to keep working:

```text
# polepos:router-imports
# polepos:router-includes
# polepos:model-imports
# polepos:module-exports
# polepos:integration-settings
# polepos:integration-env
```

After structural edits, merge-conflict resolution, module removal, integration
scaffolding, or migration work, run:

```bash
polepos check
```
