import ast
from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.integration_specs import (
    CHECKED_INTEGRATION_CONTRACTS,
    IntegrationContract,
)
from pole_position.cli.services.module_templates import (
    DEFAULT_MODULE_TEMPLATE,
    ModuleTemplateContract,
    get_module_template_contract,
    module_template_detection_contracts,
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


STARTER_MODULES = {
    "profile",
    "races",
    "status",
}

PROJECT_IDENTITY_PATHS = [
    "pyproject.toml",
    "alembic.ini",
]

PACKAGE_IDENTITY_PATHS = [
    "app.py",
    "settings.py",
    "api",
    "bootstrap",
    "db",
    "modules",
]

CORE_PROJECT_PATHS = [
    ".env.example",
    "AGENTS.md",
    "README.md",
    "tests/conftest.py",
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
    "db/__init__.py",
    "db/base.py",
    "db/models.py",
    "db/session.py",
    "domain/__init__.py",
    "domain/exceptions.py",
    "modules/__init__.py",
    "modules/profile/__init__.py",
    "modules/profile/router.py",
    "modules/profile/schemas.py",
    "modules/races/__init__.py",
    "modules/races/model.py",
    "modules/races/repository.py",
    "modules/races/router.py",
    "modules/races/schemas.py",
    "modules/races/service.py",
    "modules/status/__init__.py",
    "modules/status/router.py",
    "modules/status/schemas.py",
    "modules/status/service.py",
]

ALEMBIC_PATHS = [
    "alembic.ini",
    "migrations/env.py",
    "migrations/script.py.mako",
    "migrations/versions",
]

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


def check_project(cwd: Path | None = None) -> ProjectCheckResult:
    return _run_project_checks(cwd, include_lifecycle=True, include_integrations=True)


def check_core_project(cwd: Path | None = None) -> ProjectCheckResult:
    return _run_project_checks(cwd, include_lifecycle=False, include_integrations=False)


def _run_project_checks(
    cwd: Path | None = None,
    *,
    include_lifecycle: bool,
    include_integrations: bool,
) -> ProjectCheckResult:
    project_root, package_root = _discover_core_project(cwd)
    problems: list[str] = []

    _check_project_identity(problems, project_root, package_root)
    _check_generated_structure(problems, project_root, package_root)
    _check_alembic_config(problems, project_root)
    _check_managed_markers(problems, package_root)
    if include_lifecycle:
        _check_lifecycle_wiring(problems, project_root, package_root)
    if include_integrations:
        _check_integration_wiring(problems, project_root, package_root)

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

    raise RuntimeError("Current directory does not look like a PolePosition project.")


def _find_core_package_root_in(project_root: Path) -> Path | None:
    src_root = project_root / "src"
    if not src_root.is_dir():
        return None

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


def _check_project_identity(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    src_root = project_root / "src"

    if not (project_root / "pyproject.toml").is_file():
        problems.append(
            f"Project identity file is missing: {project_root / 'pyproject.toml'}"
        )

    if not src_root.is_dir():
        problems.append(f"Project src directory is missing: {src_root}")

    if package_root.parent != src_root:
        problems.append(
            f"Application package is not under project src directory: {package_root}"
        )

    if not package_root.name.isidentifier():
        problems.append(
            f"Application package name is not a valid Python identifier: {package_root.name}"
        )


def _check_generated_structure(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    required_paths = [
        *[project_root / relative_path for relative_path in CORE_PROJECT_PATHS],
        *[package_root / relative_path for relative_path in CORE_PACKAGE_PATHS],
    ]

    for path in required_paths:
        if not path.exists():
            problems.append(f"Required generated path is missing: {path}")


def _check_alembic_config(problems: list[str], project_root: Path) -> None:
    required_paths = [project_root / relative_path for relative_path in ALEMBIC_PATHS]

    for path in required_paths:
        if not path.exists():
            problems.append(f"Required Alembic path is missing: {path}")


def _check_managed_markers(problems: list[str], package_root: Path) -> None:
    for relative_path, markers in MANAGED_MARKERS.items():
        path = (package_root / relative_path).resolve()

        if not path.is_file():
            problems.append(f"Managed file is missing: {path}")
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        for marker in markers:
            if marker not in lines:
                problems.append(f"Managed marker '{marker}' is missing in {path}")


def _check_lifecycle_wiring(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return

    for module_root in sorted(modules_root.iterdir()):
        if not module_root.is_dir() or module_root.name in STARTER_MODULES:
            continue

        _check_added_module_wiring(
            problems=problems,
            project_root=project_root,
            package_root=package_root,
            module_root=module_root,
        )


def _check_added_module_wiring(
    *,
    problems: list[str],
    project_root: Path,
    package_root: Path,
    module_root: Path,
) -> None:
    module_name = module_root.name

    if not module_name.isidentifier():
        problems.append(
            f"Lifecycle module directory is not a valid Python identifier: {module_root}"
        )
        return

    module_kind = _detect_module_kind(project_root, module_root)
    template_contract = get_module_template_contract(module_kind)

    for relative_path in template_contract.file_names:
        path = module_root / relative_path
        if not path.exists():
            problems.append(
                f"Lifecycle module '{module_name}' is missing generated path: {path}"
            )

    _check_module_export(problems, package_root, module_name)
    _check_module_router_wiring(problems, package_root, module_name)
    if template_contract.update_db_models:
        _check_module_model_wiring(problems, package_root, module_name)
    _check_module_tests(problems, project_root, module_name, template_contract)


def _detect_module_kind(project_root: Path, module_root: Path) -> str:
    module_name = module_root.name

    for contract in module_template_detection_contracts():
        unit_test = project_root / "tests" / "unit" / contract.unit_test_name(module_name)
        if unit_test.exists():
            return contract.name

        if any(
            (module_root / file_name).exists()
            for file_name in contract.detection_file_names
        ):
            return contract.name

    return DEFAULT_MODULE_TEMPLATE


def _check_module_export(
    problems: list[str],
    package_root: Path,
    module_name: str,
) -> None:
    modules_init_path = package_root / "modules" / "__init__.py"
    lines = _read_file_lines(modules_init_path)
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
    content = _read_file_text(router_path)
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

    if not _has_router_import(tree, router_module, router_alias):
        problems.append(
            f"Lifecycle module '{module_name}' is missing router import in "
            f"{router_path}: {import_line}"
        )

    if not _has_router_include(tree, router_alias, module_name):
        problems.append(
            f"Lifecycle module '{module_name}' is missing API router include in "
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
        problems.append(f"Could not parse Python file for lifecycle checks: {path}: {exc}")
        return None


def _has_router_import(tree: ast.Module, router_module: str, router_alias: str) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        for alias in node.names:
            if alias.name == "router" and alias.asname == router_alias:
                return True

    return False


def _has_router_include(
    tree: ast.Module,
    router_alias: str,
    module_name: str,
) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_api_router_include_call(node):
            continue
        if not node.args or not _is_name(node.args[0], router_alias):
            continue
        if _include_router_keywords_match(node, module_name):
            return True

    return False


def _is_api_router_include_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "api_router"
    )


def _is_name(node: ast.AST, expected_name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected_name


def _include_router_keywords_match(node: ast.Call, module_name: str) -> bool:
    prefix = _literal_keyword_value(node, "prefix")
    tags = _literal_keyword_value(node, "tags")

    return prefix == f"/{module_name}" and tags in ([module_name], (module_name,))


def _literal_keyword_value(node: ast.Call, keyword_name: str) -> object:
    for keyword in node.keywords:
        if keyword.arg == keyword_name:
            return _literal_value(keyword.value)

    return None


def _literal_value(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _check_module_model_wiring(
    problems: list[str],
    package_root: Path,
    module_name: str,
) -> None:
    models_path = package_root / "db" / "models.py"
    lines = _read_file_lines(models_path)
    if lines is None:
        return

    package_name = package_root.name
    import_line = (
        f"    from {package_name}.modules.{module_name} import model  # noqa: F401"
    )
    if import_line not in lines:
        problems.append(
            f"Lifecycle module '{module_name}' is missing model import in "
            f"{models_path}: {import_line}"
        )


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
        project_root / "tests" / "unit" / template_contract.unit_test_name(module_name)
    )

    if not integration_test.exists():
        problems.append(
            f"Lifecycle module '{module_name}' is missing integration test: "
            f"{integration_test}"
        )

    if not unit_test.exists():
        problems.append(
            f"Lifecycle module '{module_name}' is missing unit test: {unit_test}"
        )


def _check_integration_wiring(
    problems: list[str],
    project_root: Path,
    package_root: Path,
) -> None:
    settings_content = _read_file_text(package_root / "settings.py")
    env_content = _read_file_text(project_root / ".env.example")
    pyproject_content = _read_file_text(project_root / "pyproject.toml")

    for contract in CHECKED_INTEGRATION_CONTRACTS:
        if not _has_integration_signal(
            contract=contract,
            project_root=project_root,
            package_root=package_root,
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
        and dependency in pyproject_content
    ):
        return True

    if settings_content is not None:
        for setting in contract.settings:
            if f"{setting}:" in settings_content:
                return True

    if env_content is not None:
        for env_name in contract.env:
            if f"{env_name}=" in env_content:
                return True

    if contract.name == "llm":
        return _has_ai_prompt_module(project_root, package_root)

    return False


def _has_ai_prompt_module(project_root: Path, package_root: Path) -> bool:
    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return False

    for module_root in modules_root.iterdir():
        if not module_root.is_dir() or module_root.name in STARTER_MODULES:
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
                f"Integration '{contract.name}' is missing generated file: {path}"
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

    if dependency not in pyproject_content:
        problems.append(
            f"Integration '{contract.name}' is missing dependency in "
            f"{project_root / 'pyproject.toml'}: {dependency}"
        )


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
    for setting in contract.settings:
        if f"{setting}:" not in settings_content:
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
    for env_name in contract.env:
        if f"{env_name}=" not in env_content:
            problems.append(
                f"Integration '{contract.name}' is missing env value in "
                f"{env_path}: {env_name}"
            )


def _read_file_lines(path: Path) -> list[str] | None:
    if not path.is_file():
        return None

    return path.read_text(encoding="utf-8").splitlines()


def _read_file_text(path: Path) -> str | None:
    if not path.is_file():
        return None

    return path.read_text(encoding="utf-8")
