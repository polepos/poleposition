import ast
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from pole_position.cli.services.auth_creator import AUTH_DEPENDENCY
from pole_position.cli.services.dependency_contract import (
    dependency_contract_satisfied,
    quoted_dependency_values,
)
from pole_position.cli.services.integration_specs import (
    CHECKED_INTEGRATION_CONTRACTS,
    IntegrationContract,
)
from pole_position.cli.services.module_templates import (
    DEFAULT_MODULE_TEMPLATE,
    SUPPORTED_MODULE_TEMPLATES,
    ModuleTemplateContract,
    get_module_template_contract,
    module_template_detection_contracts,
)
from pole_position.cli.services.project_manifest import (
    ProjectManifest,
    parse_manifest_module_template,
    read_project_manifest,
)
from pole_position.cli.services.project_wiring import (
    has_router_import,
    has_router_include,
    is_api_router_include_call,
    is_name,
    literal_keyword_value,
    module_name_from_model_reference,
    module_name_from_router_import,
    module_name_from_router_include,
    router_aliases_by_module_name,
)

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


@dataclass(frozen=True)
class ProjectCheckIssue:
    code: str
    message: str
    remediation: str


@dataclass(frozen=True)
class ProjectCheckResult:
    project_root: Path
    package_root: Path
    problems: list[str]

    @property
    def package_name(self) -> str:
        return self.package_root.name

    @property
    def passed(self) -> bool:
        return not self.problems

    @property
    def issues(self) -> tuple[ProjectCheckIssue, ...]:
        return tuple(
            describe_project_check_issue(problem) for problem in self.problems
        )


def describe_project_check_issue(problem: str) -> ProjectCheckIssue:
    return ProjectCheckIssue(
        code=_project_check_issue_code(problem),
        message=problem,
        remediation=_project_check_remediation(problem),
    )


def _project_check_issue_code(problem: str) -> str:
    if problem.startswith("Project identity file is missing"):
        return "PPCHK001"
    if problem.startswith("Project src directory is missing"):
        return "PPCHK002"
    if problem.startswith(
        "Application package is not under project src directory"
    ):
        return "PPCHK003"
    if problem.startswith(
        "Application package name is not a valid Python identifier"
    ):
        return "PPCHK004"
    if problem.startswith("Project manifest package does not match"):
        return "PPCHK005"
    if problem.startswith("Required generated path is missing"):
        return "PPCHK010"
    if problem.startswith("Required Alembic path is missing"):
        return "PPCHK011"
    if problem.startswith(
        "Database-free project contains database-specific content"
    ):
        return "PPCHK012"
    if problem.startswith("Project manifest has unsupported database mode"):
        return "PPCHK013"
    if problem.startswith("Project manifest has unsupported module template"):
        return "PPCHK014"
    if problem.startswith("Project manifest has unsupported integration value"):
        return "PPCHK015"
    if problem.startswith("Could not read project manifest as UTF-8"):
        return "PPCHK016"
    if problem.startswith("Managed file is missing"):
        return "PPCHK020"
    if problem.startswith("Managed marker"):
        return "PPCHK021"
    if problem.startswith("Starter module 'status' is missing"):
        return "PPCHK022"
    if problem.startswith("Could not read generated text file as UTF-8"):
        return "PPCHK023"
    if problem.startswith(
        "Lifecycle module directory is not a valid Python identifier"
    ):
        return "PPCHK030"
    if problem.startswith("Auth workflow requires generated database wiring"):
        return "PPCHK044"
    if problem.startswith("Auth workflow is missing generated file:"):
        return "PPCHK045"
    if problem.startswith("Auth workflow is missing integration test:"):
        return "PPCHK046"
    if problem.startswith("Auth workflow is missing unit test:"):
        return "PPCHK047"
    if problem.startswith("Auth workflow is missing dependency "):
        return "PPCHK048"
    if problem.startswith("Auth workflow is missing router import "):
        return "PPCHK049"
    if problem.startswith("Auth workflow is missing API router include "):
        return "PPCHK050"
    if problem.startswith("Auth workflow is missing model import "):
        return "PPCHK051"
    if " is missing generated path:" in problem:
        return "PPCHK031"
    if " is missing module export " in problem:
        return "PPCHK032"
    if " is missing router import " in problem:
        return "PPCHK033"
    if " is missing API router include " in problem:
        return "PPCHK034"
    if " is missing model import " in problem:
        return "PPCHK035"
    if " is missing integration test:" in problem:
        return "PPCHK036"
    if " is missing unit test:" in problem:
        return "PPCHK037"
    if problem.startswith("Could not parse Python file for lifecycle checks"):
        return "PPCHK038"
    if problem.startswith("Orphan module"):
        return "PPCHK039"
    if (
        problem.startswith("Integration ")
        and " is missing generated file:" in problem
    ):
        return "PPCHK040"
    if (
        problem.startswith("Integration ")
        and " is missing dependency " in problem
    ):
        return "PPCHK041"
    if problem.startswith("Integration ") and " is missing setting " in problem:
        return "PPCHK042"
    if (
        problem.startswith("Integration ")
        and " is missing env value " in problem
    ):
        return "PPCHK043"
    return "PPCHK000"


def _project_check_remediation(problem: str) -> str:
    module_name = _extract_lifecycle_module_name(problem)
    integration_name = _extract_integration_name(problem)

    if problem.startswith("Project identity file is missing"):
        return (
            "Restore pyproject.toml or run the command from the generated "
            "project root."
        )
    if problem.startswith("Project src directory is missing"):
        return (
            "Restore the generated src/ directory or run the command from the "
            "project root."
        )
    if problem.startswith(
        "Application package is not under project src directory"
    ):
        return (
            "Move the application package back under src/ or document the "
            "project "
            "as manually managed."
        )
    if problem.startswith(
        "Application package name is not a valid Python identifier"
    ):
        return "Rename the package directory to a valid Python identifier."
    if problem.startswith("Project manifest package does not match"):
        return (
            "Update .poleposition.toml or move the package back to the "
            "recorded name."
        )
    if problem.startswith("Required generated path is missing"):
        return (
            "Restore the generated path, or intentionally opt out and document "
            "the drift."
        )
    if problem.startswith("Required Alembic path is missing"):
        return (
            "Restore Alembic files or regenerate the migration setup "
            "before using "
            "polepos db commands."
        )
    if problem.startswith(
        "Database-free project contains database-specific content"
    ):
        return (
            "Remove database-specific remnants or add a database layer "
            "intentionally."
        )
    if problem.startswith("Project manifest has unsupported database mode"):
        return 'Use db = "sqlite", "postgres", "none", or "custom".'
    if problem.startswith("Project manifest has unsupported module template"):
        supported = ", ".join((*SUPPORTED_MODULE_TEMPLATES, "starter"))
        return (
            f"Use one of these module template values: {supported}; CRUD "
            f"options "
            "may be recorded as crud[pagination,timestamps,...]."
        )
    if problem.startswith("Project manifest has unsupported integration value"):
        return "Use unquoted true or false for generated integration values."
    if problem.startswith("Could not read project manifest as UTF-8"):
        return (
            "Restore .poleposition.toml as UTF-8 TOML or remove the corrupt "
            "file."
        )
    if problem.startswith("Managed file is missing"):
        return (
            "Restore the managed file before running PolePosition lifecycle "
            "commands."
        )
    if problem.startswith("Managed marker"):
        return (
            "Restore the listed # polepos marker or manage that file manually."
        )
    if problem.startswith("Starter module 'status' is missing"):
        return (
            "Restore the generated status router import/include in "
            "api/router.py."
        )
    if problem.startswith("Could not read generated text file as UTF-8"):
        return (
            "Restore the file as UTF-8 text or replace it with generated "
            "content."
        )
    if problem.startswith(
        "Lifecycle module directory is not a valid Python identifier"
    ):
        return "Rename the module directory to a valid Python identifier."
    if problem.startswith("Auth workflow requires generated database wiring"):
        return (
            "Create the project with database support or fully detach the auth "
            "workflow."
        )
    if problem.startswith("Auth workflow "):
        return (
            "Restore the missing auth workflow piece or fully detach auth from "
            "router wiring, db/models.py, pyproject.toml, tests, and "
            ".poleposition.toml."
        )
    if " is missing generated path:" in problem:
        return _module_fix(
            module_name,
            "Restore the missing generated module file, or detach/remove "
            "the module.",
        )
    if " is missing module export " in problem:
        return _module_fix(
            module_name,
            "Restore the module export, or clean the detached module with "
            "wiring-only removal.",
        )
    if " is missing router import " in problem:
        return _module_fix(
            module_name,
            "Restore the router import, or clean the detached module with "
            "wiring-only removal.",
        )
    if " is missing API router include " in problem:
        return _module_fix(
            module_name,
            "Restore the router include, or clean the detached module with "
            "wiring-only removal.",
        )
    if " is missing model import " in problem:
        return _module_fix(
            module_name,
            "Restore the db/models.py import so Alembic can see the model.",
        )
    if " is missing integration test:" in problem:
        return _module_fix(
            module_name,
            "Restore the generated integration test or clean detached "
            "test remnants.",
        )
    if " is missing unit test:" in problem:
        return _module_fix(
            module_name,
            "Restore the generated unit test or clean detached test remnants.",
        )
    if problem.startswith("Could not parse Python file for lifecycle checks"):
        return "Fix the Python syntax error before rerunning polepos check."
    if problem.startswith("Orphan module"):
        orphan_name = _extract_orphan_module_name(problem)
        if orphan_name is not None:
            return (
                f"Run `polepos remove module {orphan_name}` to clean generated "
                "remnants, or restore the missing module directory."
            )
        return (
            "Clean generated remnants or restore the missing module directory."
        )
    if (
        problem.startswith("Integration ")
        and " is missing generated file:" in problem
    ):
        return _integration_fix(
            integration_name,
            "Restore the generated integration file or remove the integration "
            "completely.",
        )
    if (
        problem.startswith("Integration ")
        and " is missing dependency " in problem
    ):
        return _integration_fix(
            integration_name,
            "Restore the dependency in pyproject.toml or remove the "
            "integration "
            "scaffold.",
        )
    if problem.startswith("Integration ") and " is missing setting " in problem:
        return _integration_fix(
            integration_name,
            "Restore the generated settings.py value or remove the integration "
            "scaffold.",
        )
    if (
        problem.startswith("Integration ")
        and " is missing env value " in problem
    ):
        return _integration_fix(
            integration_name,
            "Restore the .env.example value or remove the integration "
            "scaffold.",
        )

    return (
        "Review the reported drift and restore the PolePosition-managed "
        "contract."
    )


def _extract_lifecycle_module_name(problem: str) -> str | None:
    match = re.search(r"Lifecycle module '([^']+)'", problem)
    return match.group(1) if match else None


def _extract_integration_name(problem: str) -> str | None:
    match = re.search(r"Integration '([^']+)'", problem)
    return match.group(1) if match else None


def _extract_orphan_module_name(problem: str) -> str | None:
    match = re.search(r"missing module '([^']+)'", problem)
    return match.group(1) if match else None


def _module_fix(module_name: str | None, message: str) -> str:
    if module_name is None:
        return message
    return (
        f"{message} If '{module_name}' was intentionally detached, run "
        f"`polepos remove module {module_name} --wiring-only`; if it was "
        f"already "
        "detached, move, delete, or rewire the module directory."
    )


def _integration_fix(integration_name: str | None, message: str) -> str:
    if integration_name is None:
        return message
    return (
        f"{message} Re-run `polepos add integration {integration_name}` only "
        "after cleanup."
    )


def check_project(cwd: Path | None = None) -> ProjectCheckResult:
    return _run_project_checks(
        cwd, include_lifecycle=True, include_integrations=True
    )


def check_core_project(cwd: Path | None = None) -> ProjectCheckResult:
    return _run_project_checks(
        cwd, include_lifecycle=False, include_integrations=False
    )


def _run_project_checks(
    cwd: Path | None = None,
    *,
    include_lifecycle: bool,
    include_integrations: bool,
) -> ProjectCheckResult:
    project_root, package_root = _discover_core_project(cwd)
    problems: list[str] = []
    manifest = read_project_manifest(project_root)
    database_mode = _project_database_mode(project_root, package_root, manifest)
    uses_database = database_mode in {"sqlite", "postgres", "managed"}

    _check_project_identity(problems, project_root, package_root)
    _check_project_manifest(problems, project_root, package_root, manifest)
    _check_generated_structure(
        problems,
        project_root,
        package_root,
        uses_database=uses_database,
    )
    if uses_database:
        _check_alembic_config(problems, project_root)
    elif database_mode == "none":
        _check_database_free_remnants(problems, project_root, package_root)
    _check_managed_markers(problems, package_root, uses_database=uses_database)
    if include_lifecycle:
        _check_lifecycle_wiring(problems, project_root, package_root, manifest)
    if include_integrations:
        _check_integration_wiring(
            problems, project_root, package_root, manifest
        )
        _check_auth_workflow(
            problems=problems,
            project_root=project_root,
            package_root=package_root,
            manifest=manifest,
            uses_database=uses_database,
        )

    return ProjectCheckResult(
        project_root=project_root,
        package_root=package_root,
        problems=problems,
    )


def _discover_core_project(cwd: Path | None = None) -> tuple[Path, Path]:
    current = (cwd or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        package_root = _find_core_package_root_in(candidate)
        if package_root is not None:
            return candidate, package_root

    raise RuntimeError(
        "Current directory does not look like a PolePosition project."
    )


def _find_core_package_root_in(project_root: Path) -> Path | None:
    src_root = project_root / "src"
    if not src_root.is_dir():
        return None

    manifest = read_project_manifest(project_root)
    if manifest.exists and manifest.package_name:
        package_root = src_root / manifest.package_name
        if (
            package_root.is_dir()
            and package_root.name.isidentifier()
            and _has_core_project_signals(project_root, package_root)
        ):
            return package_root

    candidates = [
        path
        for path in src_root.iterdir()
        if (
            path.is_dir()
            and path.name.isidentifier()
            and _has_core_project_signals(project_root, path)
        )
    ]

    if len(candidates) != 1:
        return None

    return candidates[0]


def _has_core_project_signals(project_root: Path, package_root: Path) -> bool:
    project_signal_count = sum(
        1
        for relative_path in PROJECT_IDENTITY_PATHS
        if (project_root / relative_path).exists()
    )
    package_signal_count = sum(
        1
        for relative_path in PACKAGE_IDENTITY_PATHS
        if (package_root / relative_path).exists()
    )

    return project_signal_count >= 1 and package_signal_count >= 2


def _project_uses_database(project_root: Path, package_root: Path) -> bool:
    if (project_root / "alembic.ini").exists():
        return True
    if (project_root / "migrations").exists():
        return True
    if (package_root / "db").exists():
        return True

    settings_path = package_root / "settings.py"
    if _file_contains_text(settings_path, "database_url:"):
        return True

    env_path = project_root / ".env.example"
    if _file_contains_text(env_path, "DATABASE_URL="):
        return True

    return False


def _file_contains_text(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False

    try:
        return needle in path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False


def _project_database_mode(
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
) -> str:
    if manifest.exists and manifest.database:
        database_mode = manifest.database.strip().lower()
        if database_mode in {"sqlite", "postgres", "none", "custom"}:
            return database_mode
        return "unsupported"

    return (
        "managed"
        if _project_uses_database(project_root, package_root)
        else "none"
    )


def _check_project_identity(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    src_root = project_root / "src"

    if not (project_root / "pyproject.toml").is_file():
        problems.append(
            f"Project identity file is missing: "
            f"{project_root / 'pyproject.toml'}"
        )

    if not src_root.is_dir():
        problems.append(f"Project src directory is missing: {src_root}")

    if package_root.parent != src_root:
        problems.append(
            f"Application package is not under project src directory: "
            f"{package_root}"
        )

    if not package_root.name.isidentifier():
        problems.append(
            f"Application package name is not a valid Python identifier: "
            f"{package_root.name}"
        )


def _check_project_manifest(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
) -> None:
    if not manifest.exists:
        return

    if manifest.read_error is not None:
        problems.append(manifest.read_error)
        return

    manifest_path = project_root / ".poleposition.toml"
    if manifest.package_name and manifest.package_name != package_root.name:
        problems.append(
            "Project manifest package does not match discovered package in "
            f"{manifest_path}: {manifest.package_name} != {package_root.name}"
        )

    supported_database_modes = {
        "sqlite",
        "postgres",
        "none",
        "custom",
    }
    if (
        manifest.database
        and manifest.database.strip().lower() not in supported_database_modes
    ):
        problems.append(
            "Project manifest has unsupported database mode in "
            f"{manifest_path}: {manifest.database}"
        )

    supported_module_templates = {*SUPPORTED_MODULE_TEMPLATES, "starter"}
    for module_name, template in manifest.module_templates.items():
        try:
            parsed_template = parse_manifest_module_template(template)
        except ValueError:
            parsed_template = None

        if (
            parsed_template is not None
            and parsed_template.name in supported_module_templates
        ):
            continue
        problems.append(
            "Project manifest has unsupported module template in "
            f"{manifest_path}: {module_name} = {template}"
        )

    for integration_name, value in manifest.invalid_integration_values.items():
        problems.append(
            "Project manifest has unsupported integration value in "
            f"{manifest_path}: {integration_name} = {value}"
        )


def _check_generated_structure(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    *,
    uses_database: bool = True,
) -> None:
    package_paths = list(CORE_PACKAGE_PATHS)
    if uses_database:
        package_paths.extend(DATABASE_PACKAGE_PATHS)

    required_paths = [
        *[project_root / relative_path for relative_path in CORE_PROJECT_PATHS],
        *[package_root / relative_path for relative_path in package_paths],
    ]

    for path in required_paths:
        if not path.exists():
            problems.append(f"Required generated path is missing: {path}")


def _check_alembic_config(problems: list[str], project_root: Path) -> None:
    required_paths = [
        project_root / relative_path for relative_path in ALEMBIC_PATHS
    ]

    for path in required_paths:
        if not path.exists():
            problems.append(f"Required Alembic path is missing: {path}")


def _check_database_free_remnants(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    for (
        relative_path,
        snippets,
    ) in DATABASE_FREE_FORBIDDEN_PROJECT_CONTENT.items():
        _collect_forbidden_database_free_content(
            problems,
            project_root / relative_path,
            snippets,
        )

    for (
        relative_path,
        snippets,
    ) in DATABASE_FREE_FORBIDDEN_PACKAGE_CONTENT.items():
        _collect_forbidden_database_free_content(
            problems,
            package_root / relative_path,
            snippets,
        )


def _collect_forbidden_database_free_content(
    problems: list[str],
    path: Path,
    snippets: list[str],
) -> None:
    content = _read_file_text(path, problems)
    if content is None:
        return

    for snippet in snippets:
        if snippet not in content:
            continue

        display_snippet = snippet.strip() or snippet
        problems.append(
            "Database-free project contains database-specific content in "
            f"{path}: {display_snippet}"
        )


def _check_managed_markers(
    problems: list[str],
    package_root: Path,
    *,
    uses_database: bool = True,
) -> None:
    for relative_path, markers in MANAGED_MARKERS.items():
        if not uses_database and relative_path in DATABASE_MANAGED_MARKERS:
            continue
        path = (package_root / relative_path).resolve()

        if not path.is_file():
            problems.append(f"Managed file is missing: {path}")
            continue

        lines = _read_file_lines(path, problems)
        if lines is None:
            continue

        for marker in markers:
            if marker not in lines:
                problems.append(
                    f"Managed marker '{marker}' is missing in {path}"
                )


def _check_lifecycle_wiring(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest | None = None,
) -> None:
    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return

    module_names = {
        module_root.name
        for module_root in modules_root.iterdir()
        if module_root.is_dir()
    }

    _check_status_router_wiring(problems, package_root)

    for module_root in sorted(modules_root.iterdir()):
        if not module_root.is_dir():
            continue
        if _should_skip_lifecycle_module(project_root, module_root):
            continue

        _check_added_module_wiring(
            problems=problems,
            project_root=project_root,
            package_root=package_root,
            module_root=module_root,
            manifest=manifest,
        )

    _check_orphan_module_references(
        problems=problems,
        project_root=project_root,
        package_root=package_root,
        module_names=module_names,
    )


def _should_skip_lifecycle_module(
    project_root: Path, module_root: Path
) -> bool:
    if module_root.name in IGNORED_MODULE_DIRECTORIES:
        return True

    if module_root.name in STARTER_MODULES:
        return True

    return _is_legacy_starter_module(project_root, module_root)


def _check_status_router_wiring(
    problems: list[str],
    package_root: Path,
) -> None:
    router_path = package_root / "api" / "router.py"
    content = _read_file_text(router_path, problems)
    if content is None:
        return

    tree = _parse_python_source(content, router_path, problems)
    if tree is None:
        return

    package_name = package_root.name
    router_module = f"{package_name}.modules.status.router"
    import_line = (
        f"from {package_name}.modules.status.router import router as "
        f"status_router"
    )
    include_line = 'api_router.include_router(status_router, tags=["status"])'

    if not has_router_import(tree, router_module, "status_router"):
        problems.append(
            "Starter module 'status' is missing router import in "
            f"{router_path}: {import_line}"
        )

    if not _has_status_router_include(tree):
        problems.append(
            "Starter module 'status' is missing API router include in "
            f"{router_path}: {include_line}"
        )


def _has_status_router_include(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not is_api_router_include_call(node):
            continue
        if not node.args or not is_name(node.args[0], "status_router"):
            continue
        if any(keyword.arg == "prefix" for keyword in node.keywords):
            continue
        if literal_keyword_value(node, "tags") in (["status"], ("status",)):
            return True

    return False


def _is_legacy_starter_module(project_root: Path, module_root: Path) -> bool:
    if module_root.name == "profile":
        return (
            all(
                (module_root / file_name).exists()
                for file_name in LEGACY_PROFILE_MODULE_FILES
            )
            and not (module_root / "service.py").exists()
        )

    if module_root.name == "races":
        return (project_root / LEGACY_RACES_UNIT_TEST).exists()

    return False


def _check_added_module_wiring(
    *,
    problems: list[str],
    project_root: Path,
    package_root: Path,
    module_root: Path,
    manifest: ProjectManifest | None = None,
) -> None:
    module_name = module_root.name

    if not module_name.isidentifier():
        problems.append(
            f"Lifecycle module directory is not a valid Python "
            f"identifier: {module_root}"
        )
        return

    module_kind = _detect_module_kind(project_root, module_root, manifest)
    template_contract = get_module_template_contract(module_kind)

    for relative_path in template_contract.file_names_for(module_name):
        path = module_root / relative_path
        if not path.exists():
            problems.append(
                f"Lifecycle module '{module_name}' is missing generated "
                f"path: {path}"
            )

    _check_module_export(problems, package_root, module_name)
    _check_module_router_wiring(problems, package_root, module_name)
    if template_contract.update_db_models:
        _check_module_model_wiring(problems, package_root, module_name)
    _check_module_tests(problems, project_root, module_name, template_contract)


def _detect_module_kind(
    project_root: Path,
    module_root: Path,
    manifest: ProjectManifest | None = None,
) -> str:
    module_name = module_root.name
    manifest = manifest or read_project_manifest(project_root)
    if manifest.exists:
        module_kind = _supported_manifest_module_template_name(
            manifest.module_templates.get(module_name)
        )
        if (
            module_kind
            and module_kind != "starter"
            and module_kind in SUPPORTED_MODULE_TEMPLATES
        ):
            return module_kind

    for contract in module_template_detection_contracts():
        unit_test = (
            project_root
            / "tests"
            / "unit"
            / contract.unit_test_name(module_name)
        )
        if unit_test.exists():
            return contract.name

        if any(
            (module_root / file_name).exists()
            for file_name in contract.detection_file_names_for(module_name)
        ):
            return contract.name

    return DEFAULT_MODULE_TEMPLATE


def _supported_manifest_module_template_name(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed_template = parse_manifest_module_template(value)
    except ValueError:
        return None

    return parsed_template.name


def _check_module_export(
    problems: list[str],
    package_root: Path,
    module_name: str,
) -> None:
    modules_init_path = package_root / "modules" / "__init__.py"
    lines = _read_file_lines(modules_init_path, problems)
    if lines is None:
        return

    export_line = f'    "{module_name}",'
    if export_line not in lines:
        problems.append(
            f"Lifecycle module '{module_name}' is missing module export in "
            f"{modules_init_path}: {export_line}"
        )


def _check_module_router_wiring(
    problems: list[str],
    package_root: Path,
    module_name: str,
) -> None:
    router_path = package_root / "api" / "router.py"
    content = _read_file_text(router_path, problems)
    if content is None:
        return

    package_name = package_root.name
    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    import_line = (
        f"from {package_name}.modules.{module_name}.router import router as "
        f"{router_alias}"
    )
    include_line = (
        f'api_router.include_router({router_alias}, prefix="/{module_name}", '
        f'tags=["{module_name}"])'
    )
    tree = _parse_python_source(content, router_path, problems)
    if tree is None:
        return

    if not has_router_import(tree, router_module, router_alias):
        problems.append(
            f"Lifecycle module '{module_name}' is missing router import in "
            f"{router_path}: {import_line}"
        )

    if not has_router_include(tree, router_alias, module_name):
        problems.append(
            f"Lifecycle module '{module_name}' is missing API router "
            f"include in "
            f"{router_path}: {include_line}"
        )


def _parse_python_source(
    content: str,
    path: Path,
    problems: list[str],
) -> ast.Module | None:
    try:
        return ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        problems.append(
            f"Could not parse Python file for lifecycle checks: {path}: {exc}"
        )
        return None


def _check_module_model_wiring(
    problems: list[str],
    package_root: Path,
    module_name: str,
) -> None:
    models_path = package_root / "db" / "models.py"
    content = _read_file_text(models_path, problems)
    if content is None:
        return

    if _has_reported_parse_error(problems, models_path):
        return

    tree = _parse_python_source(content, models_path, problems)
    if tree is None:
        return

    lines = content.splitlines()

    package_name = package_root.name
    import_line = (
        f"    from {package_name}.modules.{module_name} import model  # noqa: "
        f"F401"
    )
    if import_line not in lines:
        problems.append(
            f"Lifecycle module '{module_name}' is missing model import in "
            f"{models_path}: {import_line}"
        )


def _has_reported_parse_error(problems: list[str], path: Path) -> bool:
    prefix = f"Could not parse Python file for lifecycle checks: {path}:"
    return any(problem.startswith(prefix) for problem in problems)


def _check_module_tests(
    problems: list[str],
    project_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> None:
    integration_test = (
        project_root
        / "tests"
        / "integration"
        / template_contract.integration_test_name(module_name)
    )
    unit_test = (
        project_root
        / "tests"
        / "unit"
        / template_contract.unit_test_name(module_name)
    )

    if not integration_test.exists():
        problems.append(
            f"Lifecycle module '{module_name}' is missing integration test: "
            f"{integration_test}"
        )

    if not unit_test.exists():
        problems.append(
            f"Lifecycle module '{module_name}' is missing unit test: "
            f"{unit_test}"
        )


def _check_orphan_module_references(
    *,
    problems: list[str],
    project_root: Path,
    package_root: Path,
    module_names: set[str],
) -> None:
    orphan_references = _collect_orphan_module_references(
        project_root=project_root,
        package_root=package_root,
        module_names=module_names,
    )
    seen: set[tuple[str, str, str]] = set()

    for module_name, path, description in orphan_references:
        key = (module_name, str(path), description)
        if key in seen:
            continue
        seen.add(key)
        problems.append(
            f"Orphan module reference to missing module '{module_name}' in "
            f"{path}: {description}"
        )


def _collect_orphan_module_references(
    *,
    project_root: Path,
    package_root: Path,
    module_names: set[str],
) -> list[tuple[str, Path, str]]:
    references: list[tuple[str, Path, str]] = []
    ignored_modules = (
        module_names | STARTER_MODULES | IGNORED_ORPHAN_MODULE_REFERENCES
    )

    references.extend(
        _collect_orphan_module_exports(package_root, ignored_modules)
    )
    references.extend(
        _collect_orphan_router_references(package_root, ignored_modules)
    )
    references.extend(
        _collect_orphan_model_references(package_root, ignored_modules)
    )
    references.extend(
        _collect_orphan_generated_tests(
            project_root, package_root, ignored_modules
        )
    )

    return references


def _collect_orphan_module_exports(
    package_root: Path,
    ignored_modules: set[str],
) -> list[tuple[str, Path, str]]:
    path = package_root / "modules" / "__init__.py"
    lines = _read_file_lines(path)
    if lines is None:
        return []

    references: list[tuple[str, Path, str]] = []
    for line in lines:
        match = re.match(
            r"^\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*,?\s*$", line
        )
        if match is None:
            continue
        module_name = match.group(1)
        if module_name not in ignored_modules:
            references.append((module_name, path, "module export"))

    return references


def _collect_orphan_router_references(
    package_root: Path,
    ignored_modules: set[str],
) -> list[tuple[str, Path, str]]:
    path = package_root / "api" / "router.py"
    content = _read_file_text(path)
    if content is None:
        return []

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return []

    package_name = package_root.name
    references: list[tuple[str, Path, str]] = []
    router_aliases = router_aliases_by_module_name(tree, package_name)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = module_name_from_router_import(node, package_name)
            if module_name is not None and module_name not in ignored_modules:
                references.append((module_name, path, "router import"))
            continue

        if isinstance(node, ast.Call):
            module_name = module_name_from_router_include(node, router_aliases)
            if module_name is not None and module_name not in ignored_modules:
                references.append((module_name, path, "router include"))

    return references


def _collect_orphan_model_references(
    package_root: Path,
    ignored_modules: set[str],
) -> list[tuple[str, Path, str]]:
    path = package_root / "db" / "models.py"
    content = _read_file_text(path)
    if content is None:
        return []

    package_name = package_root.name
    references: list[tuple[str, Path, str]] = []

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        module_name = module_name_from_model_reference(node, package_name)
        if module_name is not None and module_name not in ignored_modules:
            references.append((module_name, path, "model import"))

    return references


def _collect_orphan_generated_tests(
    project_root: Path,
    package_root: Path,
    ignored_modules: set[str],
) -> list[tuple[str, Path, str]]:
    references: list[tuple[str, Path, str]] = []
    package_name = package_root.name
    test_roots = [
        project_root / "tests" / "integration",
        project_root / "tests" / "unit",
    ]

    for test_root in test_roots:
        if not test_root.is_dir():
            continue
        for path in sorted(test_root.glob("test_*.py")):
            module_name = _module_name_from_generated_test_path(path)
            if module_name is None or module_name in ignored_modules:
                continue
            if _test_file_references_module(path, package_name, module_name):
                references.append((module_name, path, "generated test"))

    return references


def _module_name_from_generated_test_path(path: Path) -> str | None:
    name = path.name
    unit_suffixes = (
        "_api_service.py",
        "_orchestrator.py",
        "_service.py",
    )

    if not name.startswith("test_") or not name.endswith(".py"):
        return None

    stem = name[len("test_") : -len(".py")]
    for suffix in unit_suffixes:
        if stem.endswith(suffix[: -len(".py")]):
            stem = stem[: -len(suffix[: -len(".py")])]
            break
    if stem.endswith("_crud"):
        stem = stem[: -len("_crud")]

    return stem if stem.isidentifier() else None


def _test_file_references_module(
    path: Path, package_name: str, module_name: str
) -> bool:
    content = _read_file_text(path)
    if content is None:
        return False

    return (
        f"{package_name}.modules.{module_name}" in content
        or f"/api/v1/{module_name}" in content
        or f"test_{module_name}" in content
    )


def _safe_marker_index(lines: list[str], marker: str) -> int:
    try:
        return lines.index(marker)
    except ValueError:
        return len(lines)


def _check_auth_workflow(
    *,
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    uses_database: bool,
) -> None:
    pyproject_content = _read_file_text(
        project_root / "pyproject.toml", problems
    )
    if not _should_check_auth_workflow(
        project_root=project_root,
        package_root=package_root,
        manifest=manifest,
        pyproject_content=pyproject_content,
    ):
        return

    if not uses_database:
        problems.append(
            "Auth workflow requires generated database wiring but the "
            "project is "
            "configured without a database."
        )
        return

    _check_auth_files(problems, package_root)
    _check_auth_tests(problems, project_root)
    _check_auth_dependency(
        problems=problems,
        project_root=project_root,
        pyproject_content=pyproject_content,
    )
    _check_auth_router_wiring(problems, package_root)
    _check_auth_model_wiring(problems, package_root)


def _should_check_auth_workflow(
    *,
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    pyproject_content: str | None,
) -> bool:
    if manifest.exists and manifest.enabled_integrations.get("auth"):
        return True

    if any(
        (package_root / relative_path).exists()
        for relative_path in AUTH_WORKFLOW_PACKAGE_PATHS
    ):
        return True

    if any(
        (project_root / relative_path).exists()
        for relative_path in AUTH_WORKFLOW_TEST_PATHS
    ):
        return True

    router_content = _read_file_text(package_root / "api" / "router.py") or ""
    if (
        f"{package_root.name}.auth.router" in router_content
        or "/auth" in router_content
    ):
        return True

    models_content = _read_file_text(package_root / "db" / "models.py") or ""
    if f"{package_root.name}.auth import model" in models_content:
        return True

    return pyproject_content is not None and _pyproject_has_dependency(
        pyproject_content, AUTH_DEPENDENCY
    )


def _check_auth_files(problems: list[str], package_root: Path) -> None:
    for relative_path in AUTH_WORKFLOW_PACKAGE_PATHS:
        path = package_root / relative_path
        if not path.exists():
            problems.append(f"Auth workflow is missing generated file: {path}")


def _check_auth_tests(problems: list[str], project_root: Path) -> None:
    integration_test = project_root / "tests" / "integration" / "test_auth.py"
    unit_test = project_root / "tests" / "unit" / "test_auth_service.py"

    if not integration_test.exists():
        problems.append(
            f"Auth workflow is missing integration test: {integration_test}"
        )

    if not unit_test.exists():
        problems.append(f"Auth workflow is missing unit test: {unit_test}")


def _check_auth_dependency(
    *,
    problems: list[str],
    project_root: Path,
    pyproject_content: str | None,
) -> None:
    if pyproject_content is None:
        return

    if not _pyproject_has_dependency(pyproject_content, AUTH_DEPENDENCY):
        problems.append(
            f"Auth workflow is missing dependency in "
            f"{project_root / 'pyproject.toml'}: {AUTH_DEPENDENCY}"
        )


def _check_auth_router_wiring(problems: list[str], package_root: Path) -> None:
    router_path = package_root / "api" / "router.py"
    content = _read_file_text(router_path, problems)
    if content is None:
        return

    tree = _parse_python_source(content, router_path, problems)
    if tree is None:
        return

    package_name = package_root.name
    router_module = f"{package_name}.auth.router"
    import_line = (
        f"from {package_name}.auth.router import router as auth_router"
    )
    include_line = (
        'api_router.include_router(auth_router, prefix="/auth", tags=["auth"])'
    )

    if not has_router_import(tree, router_module, "auth_router"):
        problems.append(
            f"Auth workflow is missing router import in {router_path}: "
            f"{import_line}"
        )

    if not has_router_include(tree, "auth_router", "auth"):
        problems.append(
            f"Auth workflow is missing API router include in "
            f"{router_path}: {include_line}"
        )


def _check_auth_model_wiring(problems: list[str], package_root: Path) -> None:
    models_path = package_root / "db" / "models.py"
    content = _read_file_text(models_path, problems)
    if content is None:
        return

    if _has_reported_parse_error(problems, models_path):
        return

    tree = _parse_python_source(content, models_path, problems)
    if tree is None:
        return

    import_line = (
        f"    from {package_root.name}.auth import model as auth_model  # "
        f"noqa: F401"
    )
    if import_line not in content.splitlines():
        problems.append(
            f"Auth workflow is missing model import in {models_path}: "
            f"{import_line}"
        )


def _check_integration_wiring(
    problems: list[str],
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest | None = None,
) -> None:
    manifest = manifest or read_project_manifest(project_root)
    settings_content = _read_file_text(package_root / "settings.py", problems)
    env_content = _read_file_text(project_root / ".env.example", problems)
    pyproject_content = _read_file_text(
        project_root / "pyproject.toml", problems
    )

    for contract in CHECKED_INTEGRATION_CONTRACTS:
        if not _should_check_integration(
            contract=contract,
            project_root=project_root,
            package_root=package_root,
            manifest=manifest,
            settings_content=settings_content,
            env_content=env_content,
            pyproject_content=pyproject_content,
        ):
            continue

        _check_integration_files(
            problems=problems,
            package_root=package_root,
            contract=contract,
        )
        _check_integration_dependency(
            problems=problems,
            project_root=project_root,
            contract=contract,
            pyproject_content=pyproject_content,
        )
        _check_integration_settings(
            problems=problems,
            package_root=package_root,
            contract=contract,
            settings_content=settings_content,
        )
        _check_integration_env(
            problems=problems,
            project_root=project_root,
            contract=contract,
            env_content=env_content,
        )


def _should_check_integration(
    *,
    contract: IntegrationContract,
    project_root: Path,
    package_root: Path,
    manifest: ProjectManifest,
    settings_content: str | None,
    env_content: str | None,
    pyproject_content: str | None,
) -> bool:
    if manifest.exists:
        integrations = manifest.enabled_integrations
        if integrations.get(contract.name):
            return True
        if contract.name == "llm" and _has_ai_prompt_module(
            project_root,
            package_root,
        ):
            return True
        return _has_integration_signal(
            contract=contract,
            project_root=project_root,
            package_root=package_root,
            settings_content=settings_content,
            env_content=env_content,
            pyproject_content=pyproject_content,
        )

    return _has_integration_signal(
        contract=contract,
        project_root=project_root,
        package_root=package_root,
        settings_content=settings_content,
        env_content=env_content,
        pyproject_content=pyproject_content,
    )


def _has_integration_signal(
    *,
    contract: IntegrationContract,
    project_root: Path,
    package_root: Path,
    settings_content: str | None,
    env_content: str | None,
    pyproject_content: str | None,
) -> bool:
    if (package_root / "integrations" / contract.name).exists():
        return True

    dependency = contract.dependency
    if (
        isinstance(dependency, str)
        and pyproject_content is not None
        and _pyproject_has_dependency(pyproject_content, dependency)
    ):
        return True

    if settings_content is not None:
        settings_keys = _settings_keys(settings_content)
        if any(setting in settings_keys for setting in contract.settings):
            return True

    if env_content is not None:
        env_keys = _env_keys(env_content)
        integration_env = contract.env + contract.optional_env
        if any(env_name in env_keys for env_name in integration_env):
            return True

    if contract.name == "llm":
        return _has_ai_prompt_module(project_root, package_root)

    return False


def _has_ai_prompt_module(project_root: Path, package_root: Path) -> bool:
    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return False

    for module_root in modules_root.iterdir():
        if not module_root.is_dir():
            continue
        if _should_skip_lifecycle_module(project_root, module_root):
            continue
        if _detect_module_kind(project_root, module_root) == "ai-prompt":
            return True

    return False


def _check_integration_files(
    *,
    problems: list[str],
    package_root: Path,
    contract: IntegrationContract,
) -> None:
    for relative_path in contract.file_names:
        path = package_root / relative_path
        if not path.exists():
            problems.append(
                f"Integration '{contract.name}' is missing generated "
                f"file: {path}"
            )


def _check_integration_dependency(
    *,
    problems: list[str],
    project_root: Path,
    contract: IntegrationContract,
    pyproject_content: str | None,
) -> None:
    dependency = contract.dependency
    if not isinstance(dependency, str):
        return

    if pyproject_content is None:
        return

    if not _pyproject_has_dependency(pyproject_content, dependency):
        problems.append(
            f"Integration '{contract.name}' is missing dependency in "
            f"{project_root / 'pyproject.toml'}: {dependency}"
        )


def _pyproject_has_dependency(
    pyproject_content: str, required_dependency: str
) -> bool:
    return dependency_contract_satisfied(
        _project_dependency_specs(pyproject_content),
        required_dependency,
    )


def _project_dependency_specs(pyproject_content: str) -> tuple[str, ...]:
    if tomllib is not None:
        try:
            pyproject = tomllib.loads(pyproject_content)
        except tomllib.TOMLDecodeError:
            return ()

        project = pyproject.get("project")
        if not isinstance(project, dict):
            return ()

        dependencies = project.get("dependencies")
        if not isinstance(dependencies, list):
            return ()

        return tuple(
            dependency
            for dependency in dependencies
            if isinstance(dependency, str)
        )

    return _fallback_project_dependency_specs(pyproject_content)


def _fallback_project_dependency_specs(
    pyproject_content: str,
) -> tuple[str, ...]:
    project_match = re.search(
        r"(?ms)^\s*\[project\]\s*$"
        r"(?P<section>.*?)"
        r"^\s*\[[^\]]+\]\s*$",
        f"{pyproject_content}\n[__poleposition_end__]\n",
    )
    if project_match is None:
        return ()

    dependencies_match = re.search(
        r"(?ms)^\s*dependencies\s*=\s*\[(?P<dependencies>.*?)\]\s*(?:#.*)?$",
        project_match.group("section"),
    )
    if dependencies_match is None:
        return ()

    return quoted_dependency_values(dependencies_match.group("dependencies"))


def _check_integration_settings(
    *,
    problems: list[str],
    package_root: Path,
    contract: IntegrationContract,
    settings_content: str | None,
) -> None:
    if settings_content is None:
        return

    settings_path = package_root / "settings.py"
    settings_keys = _settings_keys(settings_content)
    for setting in contract.settings:
        if setting not in settings_keys:
            problems.append(
                f"Integration '{contract.name}' is missing setting in "
                f"{settings_path}: {setting}"
            )


def _check_integration_env(
    *,
    problems: list[str],
    project_root: Path,
    contract: IntegrationContract,
    env_content: str | None,
) -> None:
    if env_content is None:
        return

    env_path = project_root / ".env.example"
    env_keys = _env_keys(env_content)
    for env_name in contract.env:
        if env_name not in env_keys:
            problems.append(
                f"Integration '{contract.name}' is missing env value in "
                f"{env_path}: {env_name}"
            )


def _settings_keys(settings_content: str) -> set[str]:
    keys: set[str] = set()
    for line in settings_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key = stripped.split(":", 1)[0]
        if key.isidentifier():
            keys.add(key)

    return keys


def _env_keys(env_content: str) -> set[str]:
    keys: set[str] = set()
    for line in env_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0]
        if key:
            keys.add(key)

    return keys


def _read_file_lines(
    path: Path,
    problems: list[str] | None = None,
) -> list[str] | None:
    content = _read_file_text(path, problems)
    if content is None:
        return None

    return content.splitlines()


def _read_file_text(
    path: Path,
    problems: list[str] | None = None,
) -> str | None:
    if not path.is_file():
        return None

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        if problems is not None:
            problem = _unreadable_text_file_problem(path, exc)
            if problem not in problems:
                problems.append(problem)
        return None


def _unreadable_text_file_problem(path: Path, exc: UnicodeDecodeError) -> str:
    return f"Could not read generated text file as UTF-8: {path}: {exc.reason}"
