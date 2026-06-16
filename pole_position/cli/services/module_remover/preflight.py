import ast
from pathlib import Path

from pole_position.cli.services.module_creator import (
    MODEL_IMPORTS_MARKER,
    MODULE_EXPORTS_MARKER,
    ROUTER_IMPORTS_MARKER,
    ROUTER_INCLUDES_MARKER,
)
from pole_position.cli.services.module_remover.constants import (
    STARTER_MODULES,
)
from pole_position.cli.services.module_remover.generated_tests import (
    _generated_test_paths,
)
from pole_position.cli.services.module_remover.io import (
    _line_exists,
    _model_import_line,
    _module_export_line,
)
from pole_position.cli.services.module_remover.references import (
    _has_generic_module_reference,
)
from pole_position.cli.services.module_remover.router import (
    _find_router_import_range,
    _find_router_include_range,
    _has_router_remnant,
    _router_aliases_from_imports,
    _router_import_reference_ranges,
    _router_include_reference_ranges,
)
from pole_position.cli.services.module_templates import (
    ModuleTemplateContract,
)
from pole_position.cli.services.project_manifest import (
    read_project_manifest,
)


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

    # The marker and managed-layout checks protect in-place edits of a module
    # that still exists. When the module directory is already gone we are
    # cleaning orphan references that `polepos check` reported, so we scrub them
    # generically instead of blocking on a missing marker or a hand-edited
    # reference shape.
    if module_exists:
        modules_init_path = package_root / "modules" / "__init__.py"
        router_path = package_root / "api" / "router.py"
        models_path = package_root / "db" / "models.py"

        _collect_missing_marker(
            problems, modules_init_path, MODULE_EXPORTS_MARKER
        )
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
        for path in _generated_test_paths(
            project_root, module_name, template_contract
        )
    ):
        return True

    if template_contract.update_db_models and _line_exists(
        models_path, _model_import_line(package_name, module_name)
    ):
        return True

    # Catch-all: mirror `polepos check` so any reference it flags as an orphan
    # is also seen here, even when the template was mis-detected or a reference
    # was hand-edited into a non-generated shape.
    return _has_generic_module_reference(
        project_root=project_root,
        package_root=package_root,
        module_name=module_name,
    )


def _collect_missing_marker(
    problems: list[str], path: Path, marker: str
) -> None:
    lines = _read_file_lines(problems, path)
    if lines is None:
        return

    if marker not in lines:
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


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
                f"Module {description} for removal is not in a managed "
                f"layout: {path}"
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
            f"Module router import for removal is not in a managed "
            f"layout: {path}"
        )

    router_aliases = _router_aliases_from_imports(tree, router_module) | {
        router_alias
    }
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
            f"Module router include for removal is not in a managed "
            f"layout: {path}"
        )


def _parse_python_source(
    problems: list[str],
    content: str,
    path: Path,
) -> ast.Module | None:
    try:
        return ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        problems.append(
            f"Could not parse managed Python file for removal: {path}: {exc}"
        )
        return None


def _read_file_text(problems: list[str], path: Path) -> str | None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for removal: {path}: "
            f"{exc.reason}"
        )
        return None


def _read_file_lines(problems: list[str], path: Path) -> list[str] | None:
    content = _read_file_text(problems, path)
    if content is None:
        return None

    return content.splitlines()
