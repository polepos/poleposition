import ast
from dataclasses import dataclass
from pathlib import Path
import shutil

from pole_position.cli.services.module_creator import MODEL_IMPORTS_MARKER
from pole_position.cli.services.module_creator import MODULE_EXPORTS_MARKER
from pole_position.cli.services.module_creator import ROUTER_IMPORTS_MARKER
from pole_position.cli.services.module_creator import ROUTER_INCLUDES_MARKER
from pole_position.cli.services.module_templates import DEFAULT_MODULE_TEMPLATE
from pole_position.cli.services.module_templates import ModuleTemplateContract
from pole_position.cli.services.module_templates import build_module_template
from pole_position.cli.services.module_templates import get_module_template_contract
from pole_position.cli.services.module_templates import llm_env_block
from pole_position.cli.services.module_templates import llm_integration_files
from pole_position.cli.services.module_templates import llm_settings_block
from pole_position.cli.services.module_templates import module_template_detection_contracts
from pole_position.cli.services.project_locator import find_package_root
from pole_position.cli.services.project_locator import find_project_root


STARTER_MODULES = {"status"}


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
    custom_changes: tuple[str, ...] = ()
    blocked_by_custom_changes: bool = False

    @property
    def package_name(self) -> str:
        return self.package_root.name


def remove_module(
    module_name: str,
    cwd: Path | None = None,
    *,
    force: bool = False,
    trace: bool = False,
) -> RemovedModuleResult:
    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    modules_root = package_root / "modules"
    module_root = modules_root / module_name

    template_contract = _detect_module_contract(project_root, module_root, module_name)
    _validate_remove_module_preflight(
        project_root=project_root,
        package_root=package_root,
        module_root=module_root,
        module_name=module_name,
        template_contract=template_contract,
    )

    custom_changes = _detect_custom_changes(
        project_root=project_root,
        package_root=package_root,
        module_root=module_root,
        module_name=module_name,
        template_contract=template_contract,
    )
    remove_llm_shared = (
        template_contract.ensure_llm_settings
        and not _has_remaining_ai_prompt_module(
            project_root=project_root,
            modules_root=modules_root,
            removed_module_name=module_name,
        )
        and _is_generated_llm_scaffold_pristine(project_root, package_root, package_name)
    )

    if custom_changes and not force and not trace:
        raise RuntimeError(_custom_changes_message(module_name, custom_changes))

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
            next_steps=_remove_next_steps(),
            trace=True,
            force=force,
            custom_changes=tuple(custom_changes),
            blocked_by_custom_changes=bool(custom_changes and not force),
        )

    updated_files: list[Path] = []
    removed_paths: list[Path] = []

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

    removed_paths.extend(_remove_generated_tests(project_root, module_name, template_contract))

    if module_root.exists():
        shutil.rmtree(module_root)
        removed_paths.append(module_root)

    if remove_llm_shared:
        updated_files.extend(_remove_llm_settings(project_root, package_root))
        removed_paths.extend(_remove_llm_integration_files(package_root, package_name))

    return RemovedModuleResult(
        module_name=module_name,
        template=template_contract.name,
        project_root=project_root,
        package_root=package_root,
        removed_paths=tuple(dict.fromkeys(removed_paths)),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=_remove_next_steps(),
        force=force,
        custom_changes=tuple(custom_changes),
    )


def _detect_custom_changes(
    *,
    project_root: Path,
    package_root: Path,
    module_root: Path,
    module_name: str,
    template_contract: ModuleTemplateContract,
) -> list[str]:
    template = build_module_template(
        template=template_contract.name,
        package_name=package_root.name,
        module_name=module_name,
    )
    changes: list[str] = []

    if module_root.is_dir():
        expected_module_files = template.files
        for path in sorted(module_root.rglob("*")):
            if not path.is_file():
                continue

            relative_path = path.relative_to(module_root).as_posix()
            expected_content = expected_module_files.get(relative_path)
            if expected_content is None:
                changes.append(f"Unexpected module file: {path}")
                continue

            if path.read_text(encoding="utf-8") != expected_content:
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
        if path.is_file() and path.read_text(encoding="utf-8") != expected_content:
            changes.append(f"Modified generated test file: {path}")

    return changes


def _custom_changes_message(module_name: str, custom_changes: list[str]) -> str:
    formatted_changes = "\n".join(f"- {change}" for change in custom_changes)
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
) -> list[Path]:
    removed_paths = [
        path
        for path in _generated_test_paths(project_root, module_name, template_contract)
        if path.exists()
    ]

    if module_root.exists():
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

    return updated_files


def _line_exists(path: Path, line: str) -> bool:
    if not path.is_file():
        return False

    return line in path.read_text(encoding="utf-8").splitlines()


def _router_wiring_ranges(
    path: Path,
    package_name: str,
    module_name: str,
) -> list[tuple[int, int]]:
    if not path.is_file():
        return []

    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(path))
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
        and integrations_init.read_text(encoding="utf-8") == expected_integrations_init
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
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def _remove_next_steps() -> tuple[str, ...]:
    return (
        "Run `polepos check`",
        "Create a migration if removing the module also removes database tables",
    )


def _detect_module_contract(
    project_root: Path,
    module_root: Path,
    module_name: str,
) -> ModuleTemplateContract:
    for contract in module_template_detection_contracts():
        unit_test = project_root / "tests" / "unit" / contract.unit_test_name(module_name)
        if unit_test.exists():
            return contract

        if any(
            (module_root / file_name).exists()
            for file_name in contract.detection_file_names_for(module_name)
        ):
            return contract

    return get_module_template_contract(DEFAULT_MODULE_TEMPLATE)


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

    if not module_root.is_dir():
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

    if template_contract.update_db_models:
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
    if any(line in lines for line in exact_lines):
        return

    if any(token in content for token in reference_tokens):
        problems.append(
            f"Module {description} for removal is not in a managed layout: {path}"
        )


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

    if _has_router_import_reference(tree, router_module) and _find_router_import_range(
        tree,
        router_module,
        router_alias,
    ) is None:
        problems.append(
            f"Module router import for removal is not in a managed layout: {path}"
        )

    if _has_router_include_reference(
        tree,
        router_alias,
        module_name,
    ) and _find_router_include_range(
        tree,
        router_alias,
        module_name,
    ) is None:
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

    return path.read_text(encoding="utf-8")


def _read_file_lines(problems: list[str], path: Path) -> list[str] | None:
    content = _read_file_text(problems, path)
    if content is None:
        return None

    return content.splitlines()


def _module_export_line(module_name: str) -> str:
    return f'    "{module_name}",'


def _router_lines(package_name: str, module_name: str) -> list[str]:
    return [
        (
            f"from {package_name}.modules.{module_name}.router import router as "
            f"{module_name}_router"
        ),
        (
            f'api_router.include_router({module_name}_router, prefix="/{module_name}", '
            f'tags=["{module_name}"])'
        ),
    ]


def _model_import_line(package_name: str, module_name: str) -> str:
    return f"    from {package_name}.modules.{module_name} import model  # noqa: F401"


def _remove_line(path: Path, line: str) -> bool:
    return _remove_lines(path, [line])


def _remove_lines(path: Path, lines_to_remove: list[str]) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    removals = set(lines_to_remove)
    updated_lines = [line for line in lines if line not in removals]

    if updated_lines == lines:
        return False

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return True


def _remove_router_wiring(path: Path, package_name: str, module_name: str) -> bool:
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(path))
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


def _has_router_import_reference(tree: ast.Module, router_module: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom) and node.module == router_module
        for node in tree.body
    )


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


def _has_router_include_reference(
    tree: ast.Module,
    router_alias: str,
    module_name: str,
) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_api_router_include_call(node):
            continue
        if node.args and _is_name(node.args[0], router_alias):
            return True
        if _literal_keyword_value(node, "prefix") == f"/{module_name}":
            return True
        if _literal_keyword_value(node, "tags") in ([module_name], (module_name,)):
            return True

    return False


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
    if module_name == "races":
        test_paths.append(project_root / "tests" / "unit" / "test_race_service.py")

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
        path = package_root / relative_path
        if not path.is_file():
            return False
        if path.read_text(encoding="utf-8") != expected_content:
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

    settings_lines = settings_path.read_text(
        encoding="utf-8",
    ).splitlines()
    env_lines = env_path.read_text(
        encoding="utf-8",
    ).splitlines()

    return all(line in settings_lines for line in llm_settings_block()) and all(
        line in env_lines for line in llm_env_block()
    )


def _remove_lines_by_prefix(path: Path, prefixes: list[str]) -> bool:
    if not path.is_file():
        return False

    lines = path.read_text(encoding="utf-8").splitlines()
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
        and integrations_init.read_text(encoding="utf-8") == expected_integrations_init
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
