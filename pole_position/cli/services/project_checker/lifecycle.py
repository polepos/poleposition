"""Lifecycle wiring checks: status router, added modules, orphans."""

import ast
import re
from pathlib import Path

from pole_position.cli.services.module_templates import (
    DEFAULT_MODULE_TEMPLATE,
    SUPPORTED_MODULE_TEMPLATES,
    ModuleTemplateContract,
    get_module_template_contract,
    module_template_detection_contracts,
)
from pole_position.cli.services.project_checker.constants import (
    IGNORED_MODULE_DIRECTORIES,
    IGNORED_ORPHAN_MODULE_REFERENCES,
    LEGACY_PROFILE_MODULE_FILES,
    LEGACY_RACES_UNIT_TEST,
    STARTER_MODULES,
)
from pole_position.cli.services.project_checker.io import (
    _parse_python_source,
    _read_file_lines,
    _read_file_text,
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
    if template_contract.update_api_router:
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

        if _contract_detection_files_match(contract, module_root, module_name):
            return contract.name

    return DEFAULT_MODULE_TEMPLATE


def _contract_detection_files_match(
    contract: ModuleTemplateContract,
    module_root: Path,
    module_name: str,
) -> bool:
    blocking = contract.requires_absent_file_names_for(module_name)
    if any((module_root / file_name).exists() for file_name in blocking):
        return False

    return any(
        (module_root / file_name).exists()
        for file_name in contract.detection_file_names_for(module_name)
    )


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
