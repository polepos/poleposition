import ast
from dataclasses import dataclass
from pathlib import Path
import shutil

from pole_position.cli.services.module_creator import MODEL_IMPORTS_MARKER
from pole_position.cli.services.module_creator import MODULE_EXPORTS_MARKER
from pole_position.cli.services.module_creator import ROUTER_IMPORTS_MARKER
from pole_position.cli.services.module_creator import ROUTER_INCLUDES_MARKER
from pole_position.cli.services.module_templates import DEFAULT_MODULE_TEMPLATE
from pole_position.cli.services.module_templates import DEFAULT_CRUD_FEATURES
from pole_position.cli.services.module_templates import CrudFeatureSet
from pole_position.cli.services.module_templates import ModuleTemplateContract
from pole_position.cli.services.module_templates import SUPPORTED_MODULE_TEMPLATES
from pole_position.cli.services.module_templates import build_module_template
from pole_position.cli.services.module_templates import get_module_template_contract
from pole_position.cli.services.module_templates import llm_env_block
from pole_position.cli.services.module_templates import llm_integration_files
from pole_position.cli.services.module_templates import llm_settings_block
from pole_position.cli.services.module_templates import module_template_detection_contracts
from pole_position.cli.services.project_checker import LEGACY_RACES_UNIT_TEST
from pole_position.cli.services.project_locator import find_package_root
from pole_position.cli.services.project_locator import find_project_root
from pole_position.cli.services.project_manifest import ManifestModuleTemplate
from pole_position.cli.services.project_manifest import manifest_path
from pole_position.cli.services.project_manifest import parse_manifest_module_template
from pole_position.cli.services.project_manifest import read_project_manifest
from pole_position.cli.services.project_manifest import remove_manifest_integration
from pole_position.cli.services.project_manifest import remove_manifest_module


STARTER_MODULES = {"status"}
PYTHON_CACHE_DIRECTORIES = {"__pycache__"}
PYTHON_BYTECODE_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class RemovedModuleResult:
    module_name: str
    template: str
    project_root: Path
    package_root: Path
    removed_paths: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]
    trace: bool = False
    force: bool = False
    wiring_only: bool = False
    custom_changes: tuple[str, ...] = ()
    blocked_by_custom_changes: bool = False

    @property
    def package_name(self) -> str:
        return self.package_root.name


@dataclass(frozen=True)
class DetectedModuleTemplate:
    contract: ModuleTemplateContract
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES


def remove_module(
    module_name: str,
    cwd: Path | None = None,
    *,
    force: bool = False,
    trace: bool = False,
    wiring_only: bool = False,
) -> RemovedModuleResult:
    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    modules_root = package_root / "modules"
    module_root = modules_root / module_name

    detected_template = _detect_module_template(project_root, module_root, module_name)
    template_contract = detected_template.contract
    _validate_remove_module_preflight(
        project_root=project_root,
        package_root=package_root,
        module_root=module_root,
        module_name=module_name,
        template_contract=template_contract,
    )

    custom_changes = (
        _detect_custom_test_changes(
            project_root=project_root,
            package_root=package_root,
            module_name=module_name,
            template_contract=template_contract,
            crud_features=detected_template.crud_features,
        )
        if wiring_only
        else _detect_custom_changes(
            project_root=project_root,
            package_root=package_root,
            module_root=module_root,
            module_name=module_name,
            template_contract=template_contract,
            crud_features=detected_template.crud_features,
        )
    )
    remove_llm_shared = (
        not wiring_only
        and template_contract.ensure_llm_settings
        and not _has_remaining_ai_prompt_module(
            project_root=project_root,
            modules_root=modules_root,
            removed_module_name=module_name,
        )
        and _is_generated_llm_scaffold_pristine(project_root, package_root, package_name)
    )
    include_migration_next_step = (
        template_contract.update_db_models and (package_root / "db").exists()
    )

    if custom_changes and not force and not trace:
        raise RuntimeError(
            _custom_changes_message(
                module_name,
                custom_changes,
                wiring_only=wiring_only,
            )
        )

    if trace:
        return RemovedModuleResult(
            module_name=module_name,
            template=template_contract.name,
            project_root=project_root,
            package_root=package_root,
            removed_paths=tuple(
                dict.fromkeys(
                    _planned_removed_paths(
                        project_root=project_root,
                        package_root=package_root,
                        module_root=module_root,
                        module_name=module_name,
                        template_contract=template_contract,
                        remove_llm_shared=remove_llm_shared,
                        include_module_directory=not wiring_only,
                    )
                )
            ),
            updated_files=tuple(
                dict.fromkeys(
                    _planned_updated_files(
                        project_root=project_root,
                        package_root=package_root,
                        package_name=package_name,
                        module_name=module_name,
                        template_contract=template_contract,
                        remove_llm_shared=remove_llm_shared,
                    )
                )
            ),
            next_steps=_remove_next_steps(
                include_migration_note=include_migration_next_step,
                wiring_only=wiring_only,
                module_directory_preserved=wiring_only and module_root.exists(),
            ),
            trace=True,
            force=force,
            wiring_only=wiring_only,
            custom_changes=tuple(custom_changes),
            blocked_by_custom_changes=bool(custom_changes and not force),
        )

    updated_files: list[Path] = []
    removed_paths: list[Path] = []
    manifest_would_change = _manifest_would_change(
        project_root=project_root,
        module_name=module_name,
        remove_llm_shared=remove_llm_shared,
    )

    modules_init_path = modules_root / "__init__.py"
    if _remove_line(modules_init_path, _module_export_line(module_name)):
        updated_files.append(modules_init_path)

    router_path = package_root / "api" / "router.py"
    if _remove_router_wiring(router_path, package_name, module_name):
        updated_files.append(router_path)

    if template_contract.update_db_models:
        models_path = package_root / "db" / "models.py"
        if _remove_line(models_path, _model_import_line(package_name, module_name)):
            updated_files.append(models_path)

    removed_paths.extend(
        _remove_generated_tests(project_root, module_name, template_contract)
    )

    if module_root.exists() and not wiring_only:
        shutil.rmtree(module_root)
        removed_paths.append(module_root)

    if remove_llm_shared:
        updated_files.extend(_remove_llm_settings(project_root, package_root))
        removed_paths.extend(_remove_llm_integration_files(package_root, package_name))
        remove_manifest_integration(project_root=project_root, integration_name="llm")

    remove_manifest_module(project_root=project_root, module_name=module_name)
    if manifest_would_change:
        updated_files.append(manifest_path(project_root))

    return RemovedModuleResult(
        module_name=module_name,
        template=template_contract.name,
        project_root=project_root,
        package_root=package_root,
        removed_paths=tuple(dict.fromkeys(removed_paths)),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=_remove_next_steps(
            include_migration_note=include_migration_next_step,
            wiring_only=wiring_only,
            module_directory_preserved=wiring_only and module_root.exists(),
        ),
        force=force,
        wiring_only=wiring_only,
        custom_changes=tuple(custom_changes),
    )


def _detect_custom_changes(
    *,
    project_root: Path,
    package_root: Path,
    module_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES,
) -> list[str]:
    template = build_module_template(
        template=template_contract.name,
        package_name=package_root.name,
        module_name=module_name,
        crud_features=crud_features,
    )
    changes: list[str] = []

    if module_root.is_dir():
        expected_module_files = template.files
        for path in sorted(module_root.rglob("*")):
            if not path.is_file():
                continue

            relative_path = path.relative_to(module_root).as_posix()
            if _is_ignored_generated_artifact(path.relative_to(module_root)):
                continue

            expected_content = expected_module_files.get(relative_path)
            if expected_content is None:
                changes.append(f"Unexpected module file: {path}")
                continue

            if not _generated_file_matches(path, expected_content):
                changes.append(f"Modified generated module file: {path}")

    integration_test_path = (
        project_root / "tests" / "integration" / template.integration_test_name
    )
    unit_test_path = project_root / "tests" / "unit" / template.unit_test_name
    expected_tests = {
        integration_test_path: template.integration_test_content,
        unit_test_path: template.unit_test_content,
    }
    for path, expected_content in expected_tests.items():
        if path.is_file() and not _generated_file_matches(path, expected_content):
            changes.append(f"Modified generated test file: {path}")

    return changes


def _detect_custom_test_changes(
    *,
    project_root: Path,
    package_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES,
) -> list[str]:
    template = build_module_template(
        template=template_contract.name,
        package_name=package_root.name,
        module_name=module_name,
        crud_features=crud_features,
    )
    changes: list[str] = []
    integration_test_path = (
        project_root / "tests" / "integration" / template.integration_test_name
    )
    unit_test_path = project_root / "tests" / "unit" / template.unit_test_name
    expected_tests = {
        integration_test_path: template.integration_test_content,
        unit_test_path: template.unit_test_content,
    }

    for path, expected_content in expected_tests.items():
        if path.is_file() and not _generated_file_matches(path, expected_content):
            changes.append(f"Modified generated test file: {path}")

    return changes


def _generated_file_matches(path: Path, expected_content: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == expected_content
    except UnicodeDecodeError:
        return False


def _is_ignored_generated_artifact(relative_path: Path) -> bool:
    return (
        any(part in PYTHON_CACHE_DIRECTORIES for part in relative_path.parts)
        or relative_path.suffix in PYTHON_BYTECODE_SUFFIXES
    )


def _custom_changes_message(
    module_name: str,
    custom_changes: list[str],
    *,
    wiring_only: bool = False,
) -> str:
    formatted_changes = "\n".join(f"- {change}" for change in custom_changes)
    if wiring_only:
        return (
            "Cannot clean module wiring because generated tests appear to contain "
            "custom changes:\n"
            f"{formatted_changes}\n"
            f"Use `polepos remove module {module_name} --wiring-only --force` "
            "to remove those tests anyway."
        )

    return (
        "Cannot remove module because it appears to contain custom changes:\n"
        f"{formatted_changes}\n"
        f"Use `polepos remove module {module_name} --force` to remove it anyway."
    )


def _planned_removed_paths(
    *,
    project_root: Path,
    package_root: Path,
    module_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
    remove_llm_shared: bool,
    include_module_directory: bool = True,
) -> list[Path]:
    removed_paths = [
        path
        for path in _generated_test_paths(project_root, module_name, template_contract)
        if path.exists()
    ]

    if module_root.exists() and include_module_directory:
        removed_paths.append(module_root)

    if remove_llm_shared:
        removed_paths.extend(
            _planned_llm_integration_paths(package_root, package_root.name)
        )

    return removed_paths


def _planned_updated_files(
    *,
    project_root: Path,
    package_root: Path,
    package_name: str,
    module_name: str,
    template_contract: ModuleTemplateContract,
    remove_llm_shared: bool,
) -> list[Path]:
    updated_files: list[Path] = []
    modules_init_path = package_root / "modules" / "__init__.py"
    router_path = package_root / "api" / "router.py"

    if _line_exists(modules_init_path, _module_export_line(module_name)):
        updated_files.append(modules_init_path)

    if _router_wiring_ranges(router_path, package_name, module_name):
        updated_files.append(router_path)

    if template_contract.update_db_models:
        models_path = package_root / "db" / "models.py"
        if _line_exists(models_path, _model_import_line(package_name, module_name)):
            updated_files.append(models_path)

    if remove_llm_shared:
        updated_files.extend(_planned_llm_settings_updates(project_root, package_root))

    if _manifest_would_change(
        project_root=project_root,
        module_name=module_name,
        remove_llm_shared=remove_llm_shared,
    ):
        updated_files.append(manifest_path(project_root))

    return updated_files


def _line_exists(path: Path, line: str) -> bool:
    if not path.is_file():
        return False

    try:
        return line in path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False


def _read_optional_text(path: Path) -> str:
    if not path.is_file():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _file_content_matches(path: Path, expected_content: str | None) -> bool:
    if expected_content is None:
        return False

    return _read_optional_text(path) == expected_content


def _router_wiring_ranges(
    path: Path,
    package_name: str,
    module_name: str,
) -> list[tuple[int, int]]:
    if not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return []
    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    ranges = [
        _find_router_import_range(tree, router_module, router_alias),
        _find_router_include_range(tree, router_alias, module_name),
    ]
    return [line_range for line_range in ranges if line_range is not None]


def _planned_llm_settings_updates(project_root: Path, package_root: Path) -> list[Path]:
    updated_files: list[Path] = []
    settings_path = package_root / "settings.py"
    env_path = project_root / ".env.example"

    if _would_remove_lines_by_prefix(settings_path, _llm_setting_prefixes()):
        updated_files.append(settings_path)
    if _would_remove_lines_by_prefix(env_path, _llm_env_prefixes()):
        updated_files.append(env_path)

    return updated_files


def _planned_llm_integration_paths(package_root: Path, package_name: str) -> list[Path]:
    removed_paths: list[Path] = []
    integrations_root = package_root / "integrations"
    llm_root = integrations_root / "llm"
    integrations_init = integrations_root / "__init__.py"

    if llm_root.exists():
        removed_paths.append(llm_root)

    expected_integrations_init = llm_integration_files(package_name).get(
        "integrations/__init__.py"
    )
    remove_integrations_init = (
        integrations_init.is_file()
        and not _has_other_integrations(integrations_root)
        and _file_content_matches(integrations_init, expected_integrations_init)
    )
    if remove_integrations_init:
        removed_paths.append(integrations_init)

    if integrations_root.is_dir():
        remaining_names = {path.name for path in integrations_root.iterdir()}
        if llm_root.exists():
            remaining_names.discard("llm")
        if remove_integrations_init:
            remaining_names.discard("__init__.py")
        if not remaining_names:
            removed_paths.append(integrations_root)

    return removed_paths


def _would_remove_lines_by_prefix(path: Path, prefixes: list[str]) -> bool:
    if not path.is_file():
        return False

    return any(
        any(line.strip().startswith(prefix) for prefix in prefixes)
        for line in _read_optional_text(path).splitlines()
    )


def _remove_next_steps(
    *,
    include_migration_note: bool,
    wiring_only: bool = False,
    module_directory_preserved: bool = False,
) -> tuple[str, ...]:
    steps: list[str] = []
    if wiring_only and module_directory_preserved:
        steps.append(
            "Move, delete, or rewire the preserved module directory before "
            "expecting `polepos check` to pass"
        )
    steps.append("Run `polepos check`")
    if include_migration_note:
        steps.append(
            "Create a migration if removing the module also removes database tables"
        )
    return tuple(steps)


def _detect_module_template(
    project_root: Path,
    module_root: Path,
    module_name: str,
) -> DetectedModuleTemplate:
    manifest = read_project_manifest(project_root)
    if manifest.exists:
        template = manifest.module_templates.get(module_name)
        parsed_template = _supported_manifest_module_template(template)
        if parsed_template is not None and parsed_template.name != "starter":
            return DetectedModuleTemplate(
                contract=get_module_template_contract(parsed_template.name),
                crud_features=parsed_template.crud_features,
            )

    for contract in module_template_detection_contracts():
        unit_test = project_root / "tests" / "unit" / contract.unit_test_name(module_name)
        if unit_test.exists():
            return DetectedModuleTemplate(contract=contract)

        if any(
            (module_root / file_name).exists()
            for file_name in contract.detection_file_names_for(module_name)
        ):
            return DetectedModuleTemplate(contract=contract)

    return DetectedModuleTemplate(
        contract=get_module_template_contract(DEFAULT_MODULE_TEMPLATE),
    )


def _detect_module_contract(
    project_root: Path,
    module_root: Path,
    module_name: str,
) -> ModuleTemplateContract:
    return _detect_module_template(project_root, module_root, module_name).contract


def _supported_manifest_module_template(
    template: str | None,
) -> ManifestModuleTemplate | None:
    if not template:
        return None

    try:
        parsed_template = parse_manifest_module_template(template)
    except ValueError:
        return None

    if parsed_template.name not in SUPPORTED_MODULE_TEMPLATES:
        return None

    return parsed_template


def _validate_remove_module_preflight(
    *,
    project_root: Path,
    package_root: Path,
    module_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> None:
    problems: list[str] = []

    if module_name in STARTER_MODULES:
        problems.append(f"Starter module cannot be removed: {module_name}")

    manifest = read_project_manifest(project_root)
    if manifest.read_error is not None:
        problems.append(manifest.read_error)

    module_exists = module_root.is_dir()
    has_remnants = _has_removable_module_remnants(
        project_root=project_root,
        package_root=package_root,
        module_name=module_name,
        template_contract=template_contract,
    )

    if not module_exists and not has_remnants:
        problems.append(f"Module does not exist: {module_name}")

    modules_init_path = package_root / "modules" / "__init__.py"
    router_path = package_root / "api" / "router.py"
    models_path = package_root / "db" / "models.py"

    _collect_missing_marker(problems, modules_init_path, MODULE_EXPORTS_MARKER)
    _collect_missing_marker(problems, router_path, ROUTER_IMPORTS_MARKER)
    _collect_missing_marker(problems, router_path, ROUTER_INCLUDES_MARKER)

    package_name = package_root.name
    _collect_unsupported_reference(
        problems=problems,
        path=modules_init_path,
        exact_lines=[_module_export_line(module_name)],
        reference_tokens=[f'"{module_name}"', f"'{module_name}'"],
        description="module export",
    )
    _collect_unsupported_router_wiring(
        problems=problems,
        path=router_path,
        package_name=package_name,
        module_name=module_name,
    )

    if template_contract.update_db_models and (module_exists or models_path.is_file()):
        _collect_missing_marker(problems, models_path, MODEL_IMPORTS_MARKER)
        _collect_unsupported_reference(
            problems=problems,
            path=models_path,
            exact_lines=[_model_import_line(package_name, module_name)],
            reference_tokens=[f"{package_name}.modules.{module_name}"],
            description="model import",
        )

    if problems:
        formatted_problems = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(
            "Cannot remove module because the project layout is not ready:\n"
            f"{formatted_problems}"
        )


def _has_removable_module_remnants(
    *,
    project_root: Path,
    package_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> bool:
    package_name = package_root.name
    modules_init_path = package_root / "modules" / "__init__.py"
    router_path = package_root / "api" / "router.py"
    models_path = package_root / "db" / "models.py"

    if _line_exists(modules_init_path, _module_export_line(module_name)):
        return True

    if _has_router_remnant(router_path, package_name, module_name):
        return True

    manifest = read_project_manifest(project_root)
    if manifest.exists and module_name in manifest.module_templates:
        return True

    if any(
        path.exists()
        for path in _generated_test_paths(project_root, module_name, template_contract)
    ):
        return True

    return (
        template_contract.update_db_models
        and _line_exists(models_path, _model_import_line(package_name, module_name))
    )


def _manifest_would_change(
    *,
    project_root: Path,
    module_name: str,
    remove_llm_shared: bool,
) -> bool:
    manifest = read_project_manifest(project_root)
    if not manifest.exists:
        return False

    if module_name in manifest.module_templates:
        return True

    return remove_llm_shared and (
        "llm" in manifest.enabled_integrations
        or "llm" in manifest.invalid_integration_values
    )


def _has_router_remnant(path: Path, package_name: str, module_name: str) -> bool:
    if not path.is_file():
        return False

    content = _read_optional_text(path)
    if not content:
        return False

    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"

    return (
        router_module in content
        or router_alias in content
        or f'prefix="/{module_name}"' in content
        or f"prefix='/{module_name}'" in content
    )


def _collect_missing_marker(problems: list[str], path: Path, marker: str) -> None:
    lines = _read_file_lines(problems, path)
    if lines is None:
        return

    if marker not in lines:
        problems.append(f"Required managed marker '{marker}' is missing in {path}")


def _collect_unsupported_reference(
    *,
    problems: list[str],
    path: Path,
    exact_lines: list[str],
    reference_tokens: list[str],
    description: str,
) -> None:
    content = _read_file_text(problems, path)
    if content is None:
        return

    lines = content.splitlines()
    for line in lines:
        if line in exact_lines:
            continue
        if line.strip().startswith("#"):
            continue
        if any(token in line for token in reference_tokens):
            problems.append(
                f"Module {description} for removal is not in a managed layout: {path}"
            )
            return


def _collect_unsupported_router_wiring(
    *,
    problems: list[str],
    path: Path,
    package_name: str,
    module_name: str,
) -> None:
    content = _read_file_text(problems, path)
    if content is None:
        return

    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    tree = _parse_python_source(problems, content, path)
    if tree is None:
        return

    managed_import_range = _find_router_import_range(
        tree,
        router_module,
        router_alias,
    )
    if any(
        line_range != managed_import_range
        for line_range in _router_import_reference_ranges(tree, router_module)
    ):
        problems.append(
            f"Module router import for removal is not in a managed layout: {path}"
        )

    router_aliases = _router_aliases_from_imports(tree, router_module) | {router_alias}
    managed_include_range = _find_router_include_range(
        tree,
        router_alias,
        module_name,
    )
    if any(
        line_range != managed_include_range
        for line_range in _router_include_reference_ranges(
            tree,
            router_aliases,
            module_name,
        )
    ):
        problems.append(
            f"Module router include for removal is not in a managed layout: {path}"
        )


def _parse_python_source(
    problems: list[str],
    content: str,
    path: Path,
) -> ast.Module | None:
    try:
        return ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        problems.append(f"Could not parse managed Python file for removal: {path}: {exc}")
        return None


def _read_file_text(problems: list[str], path: Path) -> str | None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for removal: {path}: {exc.reason}"
        )
        return None


def _read_file_lines(problems: list[str], path: Path) -> list[str] | None:
    content = _read_file_text(problems, path)
    if content is None:
        return None

    return content.splitlines()


def _module_export_line(module_name: str) -> str:
    return f'    "{module_name}",'


def _model_import_line(package_name: str, module_name: str) -> str:
    return f"    from {package_name}.modules.{module_name} import model  # noqa: F401"


def _remove_line(path: Path, line: str) -> bool:
    return _remove_lines(path, [line])


def _remove_lines(path: Path, lines_to_remove: list[str]) -> bool:
    text = _read_optional_text(path)
    if not text:
        return False
    lines = text.splitlines()
    removals = set(lines_to_remove)
    updated_lines = [line for line in lines if line not in removals]

    if updated_lines == lines:
        return False

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return True


def _remove_router_wiring(path: Path, package_name: str, module_name: str) -> bool:
    content = _read_optional_text(path)
    if not content:
        return False
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return False
    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    ranges = [
        _find_router_import_range(tree, router_module, router_alias),
        _find_router_include_range(tree, router_alias, module_name),
    ]
    ranges_to_remove = [line_range for line_range in ranges if line_range is not None]

    if not ranges_to_remove:
        return False

    lines = content.splitlines()
    for start, end in sorted(ranges_to_remove, reverse=True):
        del lines[start - 1 : end]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _find_router_import_range(
    tree: ast.Module,
    router_module: str,
    router_alias: str,
) -> tuple[int, int] | None:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        if len(node.names) != 1:
            return None
        alias = node.names[0]
        if alias.name == "router" and alias.asname == router_alias:
            return _node_line_range(node)

    return None


def _router_import_reference_ranges(
    tree: ast.Module,
    router_module: str,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        line_range = _node_line_range(node)
        if line_range is not None:
            ranges.append(line_range)

    return ranges


def _router_aliases_from_imports(tree: ast.Module, router_module: str) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        for alias in node.names:
            if alias.name == "router":
                aliases.add(alias.asname or alias.name)

    return aliases


def _find_router_include_range(
    tree: ast.Module,
    router_alias: str,
    module_name: str,
) -> tuple[int, int] | None:
    for node in tree.body:
        if not isinstance(node, ast.Expr):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not _is_api_router_include_call(node.value):
            continue
        if not node.value.args or not _is_name(node.value.args[0], router_alias):
            continue
        if _include_router_keywords_match(node.value, module_name):
            return _node_line_range(node)

    return None


def _router_include_reference_ranges(
    tree: ast.Module,
    router_aliases: set[str],
    module_name: str,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _router_include_references_module(
            node,
            router_aliases,
            module_name,
        ):
            continue
        line_range = _node_line_range(node)
        if line_range is not None:
            ranges.append(line_range)

    return ranges


def _router_include_references_module(
    node: ast.Call,
    router_aliases: set[str],
    module_name: str,
) -> bool:
    if not _is_api_router_include_call(node):
        return False
    if node.args and isinstance(node.args[0], ast.Name):
        if node.args[0].id in router_aliases:
            return True
    if _literal_keyword_value(node, "prefix") == f"/{module_name}":
        return True
    return _literal_keyword_value(node, "tags") in ([module_name], (module_name,))


def _node_line_range(node: ast.AST) -> tuple[int, int] | None:
    end_lineno = getattr(node, "end_lineno", None)
    if getattr(node, "lineno", None) is None or end_lineno is None:
        return None

    return node.lineno, end_lineno


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


def _remove_generated_tests(
    project_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> list[Path]:
    removed_paths: list[Path] = []

    for path in _generated_test_paths(project_root, module_name, template_contract):
        if path.exists():
            path.unlink()
            removed_paths.append(path)

    return removed_paths


def _generated_test_paths(
    project_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> list[Path]:
    test_paths = [
        (
            project_root
            / "tests"
            / "integration"
            / template_contract.integration_test_name(module_name)
        ),
        project_root / "tests" / "unit" / template_contract.unit_test_name(module_name),
    ]
    # Legacy: older scaffolds shipped a "races" starter whose unit test used the
    # singular name (test_race_service.py). Clean it up only when that legacy
    # file is actually present, matching project_checker._is_legacy_starter_module.
    if module_name == "races":
        legacy_unit_test = project_root / LEGACY_RACES_UNIT_TEST
        if legacy_unit_test.is_file():
            test_paths.append(legacy_unit_test)

    return test_paths


def _has_remaining_ai_prompt_module(
    *,
    project_root: Path,
    modules_root: Path,
    removed_module_name: str,
) -> bool:
    for module_root in modules_root.iterdir():
        if not module_root.is_dir() or module_root.name == removed_module_name:
            continue
        contract = _detect_module_contract(project_root, module_root, module_root.name)
        if contract.name == "ai-prompt":
            return True

    return False


def _remove_llm_settings(project_root: Path, package_root: Path) -> list[Path]:
    updated_files: list[Path] = []
    settings_path = package_root / "settings.py"
    env_path = project_root / ".env.example"

    if _remove_lines_by_prefix(settings_path, _llm_setting_prefixes()):
        updated_files.append(settings_path)

    if _remove_lines_by_prefix(env_path, _llm_env_prefixes()):
        updated_files.append(env_path)

    return updated_files


def _llm_setting_prefixes() -> list[str]:
    return [line.strip().split(":", 1)[0] + ":" for line in llm_settings_block()]


def _llm_env_prefixes() -> list[str]:
    env_prefixes = []
    for line in llm_env_block():
        env_prefixes.append(line.split("=", 1)[0] + "=" if "=" in line else line)
        if line.startswith("# ") and "=" in line:
            env_prefixes.append(line[2:].split("=", 1)[0] + "=")
    return env_prefixes


def _is_generated_llm_scaffold_pristine(
    project_root: Path,
    package_root: Path,
    package_name: str,
) -> bool:
    expected_files = llm_integration_files(package_name)
    llm_root = package_root / "integrations" / "llm"
    if not llm_root.is_dir():
        return False

    for relative_path, expected_content in expected_files.items():
        if relative_path == "integrations/__init__.py":
            continue
        path = package_root / relative_path
        if not path.is_file():
            return False
        if not _file_content_matches(path, expected_content):
            return False

    expected_llm_paths = {
        package_root / relative_path
        for relative_path in expected_files
        if relative_path.startswith("integrations/llm/")
    }
    actual_llm_paths = {path for path in llm_root.rglob("*") if path.is_file()}
    if actual_llm_paths != expected_llm_paths:
        return False

    settings_path = package_root / "settings.py"
    env_path = project_root / ".env.example"
    if not settings_path.is_file() or not env_path.is_file():
        return False

    settings_lines = _read_optional_text(settings_path).splitlines()
    env_lines = _read_optional_text(env_path).splitlines()

    return all(line in settings_lines for line in llm_settings_block()) and all(
        line in env_lines for line in llm_env_block()
    )


def _remove_lines_by_prefix(path: Path, prefixes: list[str]) -> bool:
    if not path.is_file():
        return False

    lines = _read_optional_text(path).splitlines()
    if not lines:
        return False

    updated_lines = [
        line
        for line in lines
        if not any(line.strip().startswith(prefix) for prefix in prefixes)
    ]

    if updated_lines == lines:
        return False

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return True


def _remove_llm_integration_files(package_root: Path, package_name: str) -> list[Path]:
    removed_paths: list[Path] = []
    integrations_root = package_root / "integrations"
    llm_root = integrations_root / "llm"

    if llm_root.exists():
        shutil.rmtree(llm_root)
        removed_paths.append(llm_root)

    integrations_init = package_root / "integrations" / "__init__.py"
    expected_integrations_init = llm_integration_files(package_name).get(
        "integrations/__init__.py"
    )
    if (
        integrations_init.is_file()
        and not _has_other_integrations(integrations_root)
        and _file_content_matches(integrations_init, expected_integrations_init)
    ):
        integrations_init.unlink()
        removed_paths.append(integrations_init)

    if integrations_root.is_dir() and not any(integrations_root.iterdir()):
        integrations_root.rmdir()
        removed_paths.append(integrations_root)

    return removed_paths


def _has_other_integrations(integrations_root: Path) -> bool:
    if not integrations_root.is_dir():
        return False

    return any(
        path.name != "llm" and path.name != "__init__.py"
        for path in integrations_root.iterdir()
    )
