from pole_position.cli.services.database_options import SUPPORTED_DATABASES
from pole_position.cli.services.integration_specs import (
    SUPPORTED_INTEGRATIONS,
)
from pole_position.cli.services.module_templates import (
    CRUD_FEATURE_FLAGS,
    SUPPORTED_MODULE_TEMPLATES,
)
from pole_position.cli.usage.model import (
    CommandHelp,
    OptionHelp,
)

DATABASE_CHOICES = "|".join(SUPPORTED_DATABASES)


MODULE_TEMPLATE_CHOICES = ", ".join(SUPPORTED_MODULE_TEMPLATES)


CRUD_FEATURE_CHOICES = ", ".join(CRUD_FEATURE_FLAGS)


INTEGRATION_CHOICES = ", ".join(SUPPORTED_INTEGRATIONS)


COMMAND_HELP: dict[tuple[str, ...], CommandHelp] = {
    ("start",): CommandHelp(
        path=("start",),
        usage=(
            "Usage: polepos start <project_name> "
            f"[--install] [--no-bytecode] [--db {DATABASE_CHOICES}]"
        ),
        summary=(
            "Create a new FastAPI project with PolePosition's generated "
            "lifecycle files.",
            "Project names may use hyphens and are normalized to Python "
            "package names.",
        ),
        options=(
            OptionHelp(
                "--install",
                "Install generated project dependencies after creation.",
            ),
            OptionHelp(
                "--no-bytecode",
                "Configure generated local commands to start with "
                "PYTHONDONTWRITEBYTECODE=1.",
            ),
            OptionHelp(
                f"--db {DATABASE_CHOICES}",
                "Choose the generated database posture. Default: sqlite.",
            ),
        ),
        examples=(
            "polepos start shop-api",
            "polepos start shop-api --install",
            "polepos start shop-api --db postgres",
            "polepos start kafka-worker --db none",
        ),
        notes=(
            "`sqlite` creates the DB-ready starter with Alembic and "
            "SQLAlchemy.",
            "`postgres` uses a PostgreSQL DATABASE_URL and matching "
            "Docker database name.",
            "`none` omits SQLAlchemy, Alembic, migrations, DATABASE_URL, "
            "and db/ wiring.",
        ),
    ),
    ("add",): CommandHelp(
        path=("add",),
        usage="Usage: polepos add <subcommand>",
        summary=(
            "Grow the current project with modules, auth, or integration "
            "scaffolds.",
        ),
        subcommands=(
            OptionHelp(
                "auth", "Add the optional database-backed auth workflow."
            ),
            OptionHelp("integration", "Add an external integration scaffold."),
            OptionHelp("module", "Add a new module to the current project."),
        ),
        examples=(
            "polepos add module customers",
            "polepos add auth",
            "polepos add integration kafka",
        ),
        notes=(
            "Run `polepos help add <subcommand>` for subcommand-specific "
            "options.",
        ),
    ),
    ("add", "module"): CommandHelp(
        path=("add", "module"),
        usage=(
            "Usage: polepos add module <module_name> "
            "[--template <template_name>] [--api-only] "
            "[--pagination] [--timestamps] [--soft-delete] "
            "[--tenant-scoped] [--auth-required]"
        ),
        summary=(
            "Generate a module under src/<package>/modules/ and wire "
            "generated tests.",
            "Database-backed templates also update API router and model "
            "discovery wiring.",
        ),
        options=(
            OptionHelp(
                "--template <template_name>",
                f"Choose a module template. Templates: "
                f"{MODULE_TEMPLATE_CHOICES}.",
            ),
            OptionHelp(
                "--api-only",
                "Shortcut for --template api-only; no model, repository, "
                "or db wiring.",
            ),
            OptionHelp(
                "--pagination",
                "CRUD-only: add limit/offset query params and a paginated "
                "response.",
            ),
            OptionHelp(
                "--timestamps",
                "CRUD-only: add created_at and updated_at model/response "
                "fields.",
            ),
            OptionHelp(
                "--soft-delete",
                "CRUD-only: mark rows deleted with deleted_at instead of "
                "hard delete.",
            ),
            OptionHelp(
                "--tenant-scoped",
                "CRUD-only: add tenant_id fields and tenant query filtering.",
            ),
            OptionHelp(
                "--auth-required",
                "CRUD-only: protect generated routes with bearer "
                "authentication.",
            ),
        ),
        examples=(
            "polepos add module customers",
            "polepos add module customers --template crud",
            "polepos add module customers --template crud --pagination "
            "--timestamps",
            "polepos add module webhooks --api-only",
            "polepos add module assistant --template ai-prompt",
        ),
        notes=(
            f"Templates: {MODULE_TEMPLATE_CHOICES}",
            f"CRUD feature options require --template crud: "
            f"{CRUD_FEATURE_CHOICES}",
            "Run `polepos check` after changing generated wiring or "
            "module files.",
            "Create an Alembic revision after changing database-backed models.",
        ),
    ),
    ("add", "auth"): CommandHelp(
        path=("add", "auth"),
        usage="Usage: polepos add auth",
        summary=(
            "Add optional database-backed registration and token scaffolding.",
            (
                "The command creates auth model, repository, service, router, "
                "schemas, tests, and wiring."
            ),
        ),
        examples=("polepos add auth",),
        notes=(
            (
                "Requires a generated database layer; projects created with "
                "--db none cannot add auth directly."
            ),
            "Review the generated auth workflow before treating it as a "
            "complete auth product.",
        ),
    ),
    ("add", "integration"): CommandHelp(
        path=("add", "integration"),
        usage="Usage: polepos add integration <integration_name>",
        summary=(
            (
                "Add opt-in adapter scaffolds, settings, .env.example values, "
                "dependencies, and test doubles."
            ),
        ),
        examples=(
            "polepos add integration kafka",
            "polepos add integration rabbitmq",
            "polepos add integration redis",
            "polepos add integration rq",
        ),
        notes=(
            f"Integrations: {INTEGRATION_CHOICES}",
            "Long-running consumers and workers remain explicit runtime "
            "processes.",
        ),
    ),
    ("remove",): CommandHelp(
        path=("remove",),
        usage="Usage: polepos remove <subcommand>",
        summary=("Remove generated resources from the current project.",),
        subcommands=(
            OptionHelp(
                "module", "Remove a generated module and managed wiring."
            ),
        ),
        examples=("polepos remove module customers",),
        notes=("Run `polepos help remove module` for removal safety options.",),
    ),
    ("remove", "module"): CommandHelp(
        path=("remove", "module"),
        usage=(
            "Usage: polepos remove module <module_name> "
            "[--force] [--trace] [--wiring-only]"
        ),
        summary=(
            (
                "Delete generated module files, generated tests, manifest "
                "metadata, "
                "and managed wiring."
            ),
            "The command is conservative when custom code or unmanaged "
            "references are detected.",
        ),
        options=(
            OptionHelp(
                "--force",
                "Remove module files even when custom changes are detected.",
            ),
            OptionHelp(
                "--trace",
                "Show planned removals and updates without changing files.",
            ),
            OptionHelp(
                "--wiring-only",
                "Remove managed wiring and generated tests, but keep "
                "module files.",
            ),
        ),
        examples=(
            "polepos remove module customers",
            "polepos remove module customers --trace",
            "polepos remove module customers --wiring-only",
            "polepos remove module customers --force",
        ),
        notes=(
            "This command does not drop database tables or edit migration "
            "history.",
            (
                "Create and review a migration separately when a removed "
                "model's "
                "table should be dropped."
            ),
        ),
    ),
    ("check",): CommandHelp(
        path=("check",),
        usage="Usage: polepos check [--json] [--fix]",
        summary=(
            "Validate the generated project contract from the project "
            "root or a nested directory.",
            "Checks are read-only unless --fix is used.",
        ),
        options=(
            OptionHelp(
                "--json",
                "Print a machine-readable JSON result and exit non-zero "
                "on failure.",
            ),
            OptionHelp(
                "--fix",
                "Restore safe PolePosition-managed markers before validation.",
            ),
        ),
        examples=(
            "polepos check",
            "polepos check --json",
            "polepos check --fix",
        ),
        notes=(
            (
                "The checker validates structure, managed markers, module "
                "wiring, "
                "tests, and integrations."
            ),
            "It does not install dependencies, run migrations, or contact "
            "external services.",
        ),
    ),
    ("db",): CommandHelp(
        path=("db",),
        usage="Usage: polepos db <subcommand>",
        summary=(
            "Run Alembic migration commands through the generated project "
            "environment.",
        ),
        subcommands=(
            OptionHelp(
                "status", "Show current and target migration revisions."
            ),
            OptionHelp("upgrade", "Apply migrations."),
            OptionHelp(
                "revision", "Create an autogenerated migration revision."
            ),
            OptionHelp("downgrade", "Revert migrations."),
        ),
        examples=(
            "polepos db status",
            "polepos db upgrade",
            'polepos db revision -m "add customers table"',
            "polepos db downgrade -1",
        ),
        notes=(
            "Database commands prefer `uv run alembic ...` when uv is "
            "available.",
            (
                "Projects created with --db none do not include Alembic "
                "and should "
                "not use `polepos db`."
            ),
        ),
    ),
    ("db", "status"): CommandHelp(
        path=("db", "status"),
        usage="Usage: polepos db status",
        summary=(
            "Print Alembic's current revision and heads for the generated "
            "project.",
        ),
        examples=("polepos db status",),
    ),
    ("db", "upgrade"): CommandHelp(
        path=("db", "upgrade"),
        usage="Usage: polepos db upgrade [target]",
        summary=(
            "Apply migrations up to the selected target. Default target: head.",
        ),
        examples=(
            "polepos db upgrade",
            "polepos db upgrade head",
        ),
    ),
    ("db", "revision"): CommandHelp(
        path=("db", "revision"),
        usage='Usage: polepos db revision -m "<message>"',
        summary=("Create an Alembic revision with autogenerate enabled.",),
        options=(
            OptionHelp(
                "-m, --message <message>",
                "Describe the schema change in the migration file name.",
            ),
        ),
        examples=(
            'polepos db revision -m "add customers table"',
            'polepos db revision --message "remove garage table"',
        ),
        notes=("Review autogenerated migrations before applying them.",),
    ),
    ("db", "downgrade"): CommandHelp(
        path=("db", "downgrade"),
        usage="Usage: polepos db downgrade <target>",
        summary=("Revert migrations to the selected target.",),
        examples=(
            "polepos db downgrade -1",
            "polepos db downgrade base",
        ),
        notes=("Use downgrade commands carefully in shared environments.",),
    ),
    ("upgrade",): CommandHelp(
        path=("upgrade",),
        usage="Usage: polepos upgrade",
        summary=(
            "Print a read-only upgrade readiness report for the current "
            "project.",
            (
                "The report includes CLI version, package, database mode, "
                "modules, "
                "integrations, and check status."
            ),
        ),
        examples=("polepos upgrade",),
        notes=(
            (
                "Run this after upgrading PolePosition or before changing "
                "generated "
                "lifecycle surfaces."
            ),
        ),
    ),
    ("help",): CommandHelp(
        path=("help",),
        usage="Usage: polepos help [command] [subcommand]",
        summary=(
            "Print detailed CLI usage. Without a topic, it prints the "
            "full command reference.",
        ),
        examples=(
            "polepos help",
            "polepos help start",
            "polepos help add module",
            "polepos help db revision",
        ),
    ),
    ("version",): CommandHelp(
        path=("version",),
        usage="Usage: polepos version",
        summary=("Print the installed PolePosition CLI version.",),
        examples=(
            "polepos version",
            "polepos --version",
        ),
    ),
    ("delete",): CommandHelp(
        path=("delete",),
        usage="Usage: polepos delete <project_name> [--force] [--trace]",
        summary=(
            "Delete a generated PolePosition project directory, including its "
            "in-project virtual environment.",
            "Asks for confirmation and only deletes a directory that contains "
            "a .poleposition.toml manifest.",
        ),
        options=(
            OptionHelp("--force, -y", "Skip the confirmation prompt."),
            OptionHelp(
                "--trace, --dry-run",
                "Show what would be removed without deleting anything.",
            ),
        ),
        examples=(
            "polepos delete shop-api",
            "polepos delete shop-api --trace",
            "polepos delete shop-api --force",
        ),
        notes=(
            "Run it from outside the project directory; it refuses to delete "
            "the current directory or a parent of it.",
            "It removes local files only and never changes a database.",
        ),
    ),
}


TOP_LEVEL_SECTIONS: tuple[tuple[str, tuple[OptionHelp, ...]], ...] = (
    (
        "Project Lifecycle Commands",
        (
            OptionHelp("start", "Create a new FastAPI project lifecycle."),
            OptionHelp(
                "add",
                "Grow the current project with modules, auth, or integrations.",
            ),
            OptionHelp(
                "remove", "Remove generated resources from the current project."
            ),
            OptionHelp("delete", "Delete a generated project directory."),
            OptionHelp("check", "Validate the current PolePosition project."),
            OptionHelp("db", "Run database and migration commands."),
        ),
    ),
    (
        "Utility Commands",
        (
            OptionHelp("help", "Show detailed CLI usage."),
            OptionHelp("upgrade", "Report project upgrade readiness."),
            OptionHelp("version", "Show the installed CLI version."),
        ),
    ),
)


COMMAND_TOPIC_ORDER: tuple[tuple[str, ...], ...] = (
    ("start",),
    ("add",),
    ("add", "module"),
    ("add", "auth"),
    ("add", "integration"),
    ("remove",),
    ("remove", "module"),
    ("delete",),
    ("check",),
    ("db",),
    ("db", "status"),
    ("db", "upgrade"),
    ("db", "revision"),
    ("db", "downgrade"),
    ("help",),
    ("upgrade",),
    ("version",),
)
