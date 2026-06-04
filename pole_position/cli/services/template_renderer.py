from pathlib import Path

from pole_position.cli.services.database_options import get_database_option

TEXT_FILE_EXTENSIONS = {
    ".py",
    ".toml",
    ".md",
    ".env",
    ".example",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".ini",
}


def build_context(
    project_name: str,
    package_name: str,
    *,
    database: str = "sqlite",
    no_bytecode: bool = False,
) -> dict[str, str]:
    no_bytecode_command_prefix = ""
    no_bytecode_readme_note = ""
    database_option = get_database_option(database, package_name=package_name)

    if no_bytecode:
        no_bytecode_command_prefix = "PYTHONDONTWRITEBYTECODE=1 "
        no_bytecode_readme_note = (
            "\nThis project was generated with `--no-bytecode`, so "
            "migration and runtime\n"
            "commands in this README start with "
            "`PYTHONDONTWRITEBYTECODE=1` to prevent\n"
            "bytecode cache writes from interpreter startup.\n"
        )

    database_development_step = ""
    database_migrations_section = ""
    docker_database_section = ""
    docker_intro = "Start the generated project with Docker and PostgreSQL:"
    docker_alembic_copy = " alembic.ini"
    docker_migrations_copy = "COPY migrations ./migrations\n"
    module_database_removal_note = ""
    module_lifecycle_add_command = "polepos add module garage"
    project_layout = (
        "alembic.ini\n"
        "migrations/\n"
        "  versions/\n"
        f"src/{package_name}/\n"
        "  run.py\n"
        "  auth/\n"
        "  bootstrap/\n"
        "  api/\n"
        "  db/\n"
        "  modules/\n"
        "    status/"
    )
    runtime_database_summary = ""
    agents_db_commands = ""
    agents_db_guidance = ""
    agents_task_scope = "modules, integrations, or checks"
    agents_check_scope = (
        "generated structure, module wiring, integration wiring, or managed "
        "markers"
    )
    readme_lifecycle_scope = "modules, integrations, or checks"

    if database_option.uses_database:
        database_development_step = (
            f"{no_bytecode_command_prefix}polepos db upgrade\n"
        )
        docker_database_section = (
            "\nApply migrations from the app container:\n\n"
            "```bash\n"
            "docker compose run --rm app uv run alembic upgrade head\n"
            "```\n\n"
            "This Docker command runs Alembic directly inside the "
            "generated app container.\n"
            "For host-based development, keep using `polepos db upgrade`.\n\n"
            "If PostgreSQL is already using local port `5432`, update "
            "`POSTGRES_PORT` in\n"
            "`.env` before starting the compose stack.\n"
        )
        database_migrations_section = (
            "## Database Migrations\n\n"
            "Use PolePosition's database lifecycle commands for normal "
            "local development:\n\n"
            "```bash\n"
            f"{no_bytecode_command_prefix}polepos db upgrade\n"
            f'{no_bytecode_command_prefix}polepos db revision -m "add '
            f'garage table"\n'
            f"{no_bytecode_command_prefix}polepos db upgrade\n"
            f"{no_bytecode_command_prefix}polepos db downgrade -1\n"
            "```\n\n"
            "`polepos db` wraps Alembic and keeps migrations in the "
            "PolePosition lifecycle\n"
            "flow. If you need an Alembic option that PolePosition does "
            "not expose, you can\n"
            "still run Alembic directly:\n\n"
            "```bash\n"
            f"{no_bytecode_command_prefix}uv run alembic upgrade head\n"
            f"{no_bytecode_command_prefix}uv run alembic revision "
            f'--autogenerate -m "add garage table"\n'
            "```\n"
        )
        module_database_removal_note = (
            "\n`polepos remove module` removes generated code, generated "
            "tests, router wiring,\n"
            "module exports, and standard-module model imports. It does "
            "not connect to the\n"
            "database, drop tables, delete rows, create migrations, or "
            "edit migration\n"
            "history.\n\n"
            "By default, `polepos remove module` stops before deleting a "
            "module directory\n"
            "that appears to contain custom changes. Use `--trace` to "
            "preview the planned\n"
            "removals and updates without changing files, and use "
            "`--force` only when you\n"
            "intentionally want to remove a customized module directory. "
            "If an expected\n"
            "generated file has become undecodable as text, PolePosition "
            "treats it as a\n"
            "modified generated file; `--force` can still remove the "
            "module directory.\n\n"
            "Use `polepos remove module <name> --wiring-only` to clean "
            "generated tests and\n"
            "managed router, model, and export wiring while preserving "
            "customized module\n"
            "files.\n\n"
            "If the module directory was already deleted manually, rerun\n"
            "`polepos remove module <name>` to clean remaining generated "
            "tests and managed\n"
            "router, model, and export wiring.\n\n"
            "If a removed standard module had a database table and that "
            "table should be\n"
            "removed too, create and review an Alembic revision after the "
            "code cleanup:\n\n"
            "```bash\n"
            f'{no_bytecode_command_prefix}polepos db revision -m "remove '
            f'garage table"\n'
            f"{no_bytecode_command_prefix}polepos db upgrade\n"
            "```\n\n"
            "If the table or data should be retained, do not create a "
            "drop-table migration.\n"
        )
        runtime_database_summary = "database backend, "
        agents_db_commands = (
            '- `polepos db revision -m "..."`\n'
            "- `polepos db status`\n"
            "- `polepos db upgrade`\n"
            "- `polepos db downgrade <target>`"
        )
        agents_db_guidance = (
            "\nKeep this project FastAPI-native, module-oriented, "
            "`uv`-first, and\n"
            "migration-first. Do not add startup-time schema creation; "
            "use Alembic migrations\n"
            "for database changes.\n\n"
            "`polepos remove module <name>` cleans generated code and "
            "managed imports only.\n"
            "It does not drop database tables or create migrations. If "
            "removing a module\n"
            "should also change schema, create and review an Alembic "
            "revision after the\n"
            "remove command.\n"
        )
        agents_task_scope = "modules, integrations, checks, or migrations"
        agents_check_scope = (
            "generated structure, module wiring, integration wiring, managed\n"
            "markers, or migration setup"
        )
        readme_lifecycle_scope = "modules, integrations, checks, or migrations"
    else:
        docker_intro = "Start the generated project with Docker:"
        docker_alembic_copy = ""
        docker_migrations_copy = ""
        module_lifecycle_add_command = "polepos add module garage --api-only"
        project_layout = (
            f"src/{package_name}/\n"
            "  run.py\n"
            "  auth/\n"
            "  bootstrap/\n"
            "  api/\n"
            "  modules/\n"
            "    status/"
        )
        docker_database_section = (
            "\nThis project was generated with `--db none`, so the Docker "
            "workflow starts only\n"
            "the FastAPI application container. Add an explicit database "
            "or integration when\n"
            "the application needs persistence.\n"
        )
        database_migrations_section = (
            "## Database\n\n"
            "This project was generated with `--db none`. It does not "
            "include SQLAlchemy,\n"
            "Alembic, `DATABASE_URL`, or generated `db/` wiring.\n\n"
            "Use `polepos add module <name> --api-only` for route/service "
            "modules that do\n"
            "not need persistence. Add an explicit database or "
            "integration later when the\n"
            "application needs it.\n"
        )
        module_database_removal_note = (
            "\n`polepos remove module` removes generated code, generated "
            "tests, router wiring,\n"
            "and module exports. This project has no generated database "
            "model wiring.\n\n"
            "By default, `polepos remove module` stops before deleting a "
            "module directory\n"
            "that appears to contain custom changes. Use `--trace` to "
            "preview planned\n"
            "changes, and use `--force` only when you intentionally want "
            "to remove a\n"
            "customized module directory.\n\n"
            "Use `polepos remove module <name> --wiring-only` to clean "
            "generated tests and\n"
            "managed router/export wiring while preserving customized "
            "module files.\n\n"
            "If the module directory was already deleted manually, rerun\n"
            "`polepos remove module <name>` to clean remaining generated "
            "tests and managed\n"
            "router/export wiring.\n"
        )
        agents_db_guidance = (
            "\nKeep this project FastAPI-native, module-oriented, and "
            "`uv`-first. This project\n"
            "was generated with `--db none`, so it has no generated "
            "SQLAlchemy/Alembic\n"
            "lifecycle. Prefer `polepos add module <name> --api-only` "
            "unless you first add a\n"
            "database layer intentionally.\n"
        )

    return {
        "{{project_name}}": project_name,
        "{{ package_name }}": package_name,
        "{{project_import_name}}": package_name,
        "{{ app_name }}": project_name,
        "{{database_mode}}": database_option.name,
        "{{database_url_default}}": database_option.default_url,
        "{{postgres_db_name}}": database_option.postgres_db_name,
        "{{database_development_step}}": database_development_step,
        "{{docker_intro}}": docker_intro,
        "{{docker_alembic_copy}}": docker_alembic_copy,
        "{{docker_migrations_copy}}": docker_migrations_copy,
        "{{docker_database_section}}": docker_database_section,
        "{{database_migrations_section}}": database_migrations_section,
        "{{module_database_removal_note}}": module_database_removal_note,
        "{{module_lifecycle_add_command}}": module_lifecycle_add_command,
        "{{project_layout}}": project_layout,
        "{{runtime_database_summary}}": runtime_database_summary,
        "{{agents_db_commands}}": agents_db_commands,
        "{{agents_db_guidance}}": agents_db_guidance,
        "{{agents_task_scope}}": agents_task_scope,
        "{{agents_check_scope}}": agents_check_scope,
        "{{readme_lifecycle_scope}}": readme_lifecycle_scope,
        "{{no_bytecode_command_prefix}}": no_bytecode_command_prefix,
        "{{no_bytecode_readme_note}}": no_bytecode_readme_note,
    }


def should_render_file(path: Path) -> bool:
    if path.name in {
        ".dockerignore",
        ".env.example",
        ".gitignore",
        "Dockerfile",
    }:
        return True

    if path.suffix in TEXT_FILE_EXTENSIONS:
        return True

    return False


def render_text(content: str, context: dict[str, str]) -> str:
    rendered = content
    for key, value in context.items():
        rendered = rendered.replace(key, value)
    return rendered


def render_project_files(project_path: Path, context: dict[str, str]) -> None:
    for file_path in project_path.rglob("*"):
        if not file_path.is_file():
            continue

        if not should_render_file(file_path):
            continue

        content = file_path.read_text(encoding="utf-8")
        rendered = render_text(content, context)
        file_path.write_text(rendered, encoding="utf-8")
