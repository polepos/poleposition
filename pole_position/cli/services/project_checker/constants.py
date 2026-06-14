"""Shared constants for the project-check service modules."""

from pathlib import Path

MANAGED_MARKERS = {
    "api/router.py": [
        "# polepos:router-imports",
        "# polepos:router-includes",
    ],
    "db/models.py": [
        "    # polepos:model-imports",
    ],
    "modules/__init__.py": [
        "    # polepos:module-exports",
    ],
    "settings.py": [
        "    # polepos:auth-settings",
        "    # polepos:integration-settings",
        "    # polepos:llm-settings",
    ],
    "../../.env.example": [
        "# polepos:auth-env",
        "# polepos:integration-env",
        "# polepos:llm-env",
    ],
}

DATABASE_MANAGED_MARKERS = {
    "db/models.py",
}


STARTER_MODULES = {
    "status",
}

IGNORED_ORPHAN_MODULE_REFERENCES = {
    "auth",
}

IGNORED_MODULE_DIRECTORIES = {
    "__pycache__",
}

LEGACY_PROFILE_MODULE_FILES = {
    "__init__.py",
    "router.py",
    "schemas.py",
}

LEGACY_RACES_UNIT_TEST = Path("tests/unit/test_race_service.py")

PROJECT_IDENTITY_PATHS = [
    "pyproject.toml",
    "alembic.ini",
]

PACKAGE_IDENTITY_PATHS = [
    "app.py",
    "settings.py",
    "api",
    "bootstrap",
    "modules",
]

CORE_PROJECT_PATHS = [
    ".env.example",
    "AGENTS.md",
    "README.md",
    "tests/conftest.py",
    "tests/integration/test_status.py",
]

CORE_PACKAGE_PATHS = [
    "__init__.py",
    "app.py",
    "main.py",
    "run.py",
    "settings.py",
    "api/__init__.py",
    "api/router.py",
    "api/deps.py",
    "auth/__init__.py",
    "auth/dependencies.py",
    "auth/schemas.py",
    "auth/service.py",
    "auth/token.py",
    "bootstrap/__init__.py",
    "bootstrap/errors.py",
    "bootstrap/lifespan.py",
    "bootstrap/logging.py",
    "bootstrap/middleware.py",
    "domain/__init__.py",
    "domain/exceptions.py",
    "modules/__init__.py",
    "modules/status/__init__.py",
    "modules/status/router.py",
    "modules/status/schemas.py",
    "modules/status/services/__init__.py",
    "modules/status/services/status_service.py",
]

DATABASE_PACKAGE_PATHS = [
    "db/__init__.py",
    "db/base.py",
    "db/models.py",
    "db/session.py",
]

AUTH_WORKFLOW_PACKAGE_PATHS = [
    "auth/model.py",
    "auth/password.py",
    "auth/repository.py",
    "auth/router.py",
    "auth/user_schemas.py",
    "auth/user_service.py",
]

AUTH_WORKFLOW_TEST_PATHS = [
    "tests/integration/test_auth.py",
    "tests/unit/test_auth_service.py",
]

DATABASE_FREE_FORBIDDEN_PROJECT_CONTENT = {
    "Dockerfile": [
        "alembic.ini",
        "COPY migrations",
    ],
    "README.md": [
        "\nalembic.ini\n",
        "\nmigrations/\n",
        "\n  db/\n",
    ],
}

DATABASE_FREE_FORBIDDEN_PACKAGE_CONTENT = {
    "api/deps.py": [
        "sqlalchemy",
        ".db.session",
        "db_session",
    ],
}

ALEMBIC_PATHS = [
    "alembic.ini",
    "migrations/env.py",
    "migrations/script.py.mako",
    "migrations/versions",
]
