import ast
from pathlib import Path

from pole_position.cli.services.module_creator.constants import (
    ENV_LLM_MARKER,
    MODEL_IMPORTS_MARKER,
    MODULE_EXPORTS_MARKER,
    ROUTER_IMPORTS_MARKER,
    ROUTER_INCLUDES_MARKER,
    SETTINGS_LLM_MARKER,
)
from pole_position.cli.services.module_creator.entries import (
    _existing_entry_keys,
    _expected_block_keys,
    _missing_block_lines,
)
from pole_position.cli.services.module_creator.files import (
    _write_module_files,
    _write_module_tests,
)
from pole_position.cli.services.module_creator.markers import (
    _find_insert_index,
    _insert_block_before_marker_or_anchor,
    _insert_line_before_marker,
    _insert_sorted_line_before_marker,
)
from pole_position.cli.services.module_creator.references import (
    _has_router_reference,
    _line_exists,
)
from pole_position.cli.services.module_creator.result import (
    AddedModuleResult,
)
from pole_position.cli.services.module_templates import (
    DEFAULT_CRUD_FEATURES,
    SUPPORTED_MODULE_TEMPLATES,
    CrudFeatureSet,
    ModuleTemplate,
    build_module_template,
    llm_env_block,
    llm_integration_files,
    llm_settings_block,
)
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import (
    manifest_path,
    read_project_manifest,
    record_manifest_integration,
    record_manifest_module,
)

__all__ = [
    "add_module",
    "AddedModuleResult",
    "MODEL_IMPORTS_MARKER",
    "MODULE_EXPORTS_MARKER",
    "ROUTER_IMPORTS_MARKER",
    "ROUTER_INCLUDES_MARKER",
    "_validate_add_module_preflight",
    "_insert_block_before_marker_or_anchor",
    "_insert_line_before_marker",
    "_insert_sorted_line_before_marker",
]


def add_module(
    module_name: str,
    template: str = "standard",
    cwd: Path | None = None,
    crud_features: CrudFeatureSet = DEFAULT_CRUD_FEATURES,
) -> AddedModuleResult:
    if template not in SUPPORTED_MODULE_TEMPLATES:
        supported = ", ".join(SUPPORTED_MODULE_TEMPLATES)
        raise ValueError(
            f"Unsupported module template '{template}'. Expected one of: "
            f"{supported}."
        )

    project_root = find_project_root(cwd)
    package_root = find_package_root(cwd)
    package_name = package_root.name
    modules_root = package_root / "modules"
    module_root = modules_root / module_name
    template_spec = build_module_template(
        template=template,
        package_name=package_name,
        module_name=module_name,
        crud_features=crud_features,
    )

    _validate_add_module_preflight(
        project_root=project_root,
        package_root=package_root,
        modules_root=modules_root,
        module_root=module_root,
        module_name=module_name,
        template_spec=template_spec,
    )

    module_files = _write_module_files(module_root, template_spec.files)
    test_files = _write_module_tests(project_root / "tests", template_spec)
    updated_files: list[Path] = []

    _update_modules_init(modules_root / "__init__.py", module_name)
    updated_files.append(modules_root / "__init__.py")
    _update_api_router(
        package_root / "api" / "router.py", package_name, module_name
    )
    updated_files.append(package_root / "api" / "router.py")
    if template_spec.update_db_models:
        _update_db_models(
            package_root / "db" / "models.py", package_name, module_name
        )
        updated_files.append(package_root / "db" / "models.py")
    if template_spec.ensure_llm_integrations:
        updated_files.extend(
            _ensure_llm_integrations(package_root, package_name)
        )
    if template_spec.ensure_llm_settings:
        if _ensure_llm_settings(package_root / "settings.py"):
            updated_files.append(package_root / "settings.py")
        if _ensure_llm_env(project_root / ".env.example"):
            updated_files.append(project_root / ".env.example")
        record_manifest_integration(
            project_root=project_root,
            integration_name="llm",
        )

    record_manifest_module(
        project_root=project_root,
        module_name=module_name,
        template=template,
        features=template_spec.features,
    )
    project_manifest_path = manifest_path(project_root)
    if project_manifest_path.is_file():
        updated_files.append(project_manifest_path)

    return AddedModuleResult(
        module_name=module_name,
        template=template,
        project_root=project_root,
        package_root=package_root,
        module_files=tuple(module_files),
        test_files=tuple(test_files),
        updated_files=tuple(dict.fromkeys(updated_files)),
        next_steps=_module_next_steps(
            package_name=package_name,
            module_name=module_name,
            template_spec=template_spec,
        ),
        features=template_spec.features,
    )


def _validate_add_module_preflight(
    *,
    project_root: Path,
    package_root: Path,
    modules_root: Path,
    module_root: Path,
    module_name: str,
    template_spec: ModuleTemplate,
) -> None:
    problems: list[str] = []
    tests_root = project_root / "tests"

    _collect_manifest_read_error(problems, project_root)

    if module_root.exists():
        problems.append(f"Module already exists: {module_name}")

    _collect_existing_generated_file(
        problems,
        tests_root / "integration" / template_spec.integration_test_name,
    )
    _collect_existing_generated_file(
        problems,
        tests_root / "unit" / template_spec.unit_test_name,
    )

    modules_init_path = modules_root / "__init__.py"
    router_path = package_root / "api" / "router.py"
    _collect_missing_marker(
        problems,
        modules_init_path,
        MODULE_EXPORTS_MARKER,
    )
    _collect_python_parse_error(problems, modules_init_path)
    _collect_missing_marker(
        problems,
        router_path,
        ROUTER_IMPORTS_MARKER,
    )
    _collect_missing_marker(
        problems,
        router_path,
        ROUTER_INCLUDES_MARKER,
    )
    _collect_python_parse_error(problems, router_path)
    _collect_existing_managed_module_references(
        problems=problems,
        package_root=package_root,
        module_name=module_name,
        template_spec=template_spec,
    )

    if template_spec.update_db_models:
        db_models_path = package_root / "db" / "models.py"
        if not db_models_path.is_file() and not (package_root / "db").exists():
            problems.append(
                "Database-backed module templates require generated db/ "
                "wiring. "
                "Use `polepos add module <name> --api-only` in a "
                "database-free project."
            )
        else:
            _collect_missing_marker(
                problems,
                db_models_path,
                MODEL_IMPORTS_MARKER,
            )
            _collect_python_parse_error(problems, db_models_path)

    if template_spec.ensure_llm_settings:
        settings_path = package_root / "settings.py"
        _collect_missing_marker_unless_entries_exist(
            problems,
            settings_path,
            marker=SETTINGS_LLM_MARKER,
            block=llm_settings_block(),
            entry_type="setting",
        )
        _collect_python_parse_error(problems, settings_path)
        _collect_missing_marker_unless_entries_exist(
            problems,
            project_root / ".env.example",
            marker=ENV_LLM_MARKER,
            block=llm_env_block(),
            entry_type="env",
        )

    if problems:
        formatted_problems = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(
            "Cannot add module because the project layout is not ready:\n"
            f"{formatted_problems}"
        )


def _collect_existing_generated_file(problems: list[str], path: Path) -> None:
    if path.exists():
        problems.append(f"Generated file already exists: {path}")


def _collect_manifest_read_error(
    problems: list[str], project_root: Path
) -> None:
    manifest = read_project_manifest(project_root)
    if manifest.read_error is not None:
        problems.append(manifest.read_error)


def _collect_missing_marker(
    problems: list[str], path: Path, marker: str
) -> None:
    lines = _read_managed_file_lines(problems, path)
    if lines is None:
        return

    if marker not in lines:
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _collect_python_parse_error(problems: list[str], path: Path) -> None:
    if not path.is_file():
        return

    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed Python file for module add: {path}: "
            f"{exc.reason}"
        )
    except SyntaxError as exc:
        problems.append(
            f"Could not parse managed Python file for module add: {path}: {exc}"
        )


def _collect_existing_managed_module_references(
    *,
    problems: list[str],
    package_root: Path,
    module_name: str,
    template_spec: ModuleTemplate,
) -> None:
    package_name = package_root.name
    modules_init_path = package_root / "modules" / "__init__.py"
    router_path = package_root / "api" / "router.py"
    models_path = package_root / "db" / "models.py"

    stale_references: list[str] = []
    if _line_exists(modules_init_path, f'    "{module_name}",'):
        stale_references.append(f"module export in {modules_init_path}")

    if _has_router_reference(router_path, package_name, module_name):
        stale_references.append(f"router wiring in {router_path}")

    if template_spec.update_db_models and _line_exists(
        models_path,
        f"    from {package_name}.modules.{module_name} import model  # "
        f"noqa: F401",
    ):
        stale_references.append(f"model import in {models_path}")

    if stale_references:
        formatted = ", ".join(stale_references)
        problems.append(
            f"Managed references already exist for module '{module_name}': "
            f"{formatted}. Run `polepos remove module {module_name}` before "
            "adding it again."
        )


def _collect_missing_marker_unless_entries_exist(
    problems: list[str],
    path: Path,
    *,
    marker: str,
    block: list[str],
    entry_type: str,
) -> None:
    content = _read_managed_file_text(problems, path)
    if content is None:
        return

    expected_keys = _expected_block_keys(block, entry_type=entry_type)
    existing_keys = _existing_entry_keys(
        content.splitlines(),
        entry_type=entry_type,
    )
    if all(key in existing_keys for key in expected_keys):
        return

    if marker not in content.splitlines():
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _read_managed_file_text(problems: list[str], path: Path) -> str | None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        )
        return None


def _read_managed_file_lines(
    problems: list[str], path: Path
) -> list[str] | None:
    content = _read_managed_file_text(problems, path)
    if content is None:
        return None

    return content.splitlines()


def _update_modules_init(path: Path, module_name: str) -> None:
    export_line = f'    "{module_name}",'
    _insert_sorted_line_before_marker(
        path=path,
        line=export_line,
        marker=MODULE_EXPORTS_MARKER,
        match_prefix='    "',
    )


def _update_api_router(path: Path, package_name: str, module_name: str) -> None:
    import_line = (
        f"from {package_name}.modules.{module_name}.router import router as "
        f"{module_name}_router"
    )
    include_line = (
        f"api_router.include_router({module_name}_router, "
        f'prefix="/{module_name}", '
        f'tags=["{module_name}"])'
    )

    _insert_sorted_line_before_marker(
        path=path,
        line=import_line,
        marker=ROUTER_IMPORTS_MARKER,
        match_prefix="from ",
    )
    _insert_line_before_marker(
        path=path,
        line=include_line,
        marker=ROUTER_INCLUDES_MARKER,
    )


def _update_db_models(path: Path, package_name: str, module_name: str) -> None:
    import_line = (
        f"    from {package_name}.modules.{module_name} import model  # noqa: "
        f"F401"
    )
    _insert_sorted_line_before_marker(
        path=path,
        line=import_line,
        marker=MODEL_IMPORTS_MARKER,
        match_prefix="    from ",
    )


def _ensure_llm_integrations(
    package_root: Path, package_name: str
) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in llm_integration_files(package_name).items():
        path = package_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written


def _ensure_llm_settings(path: Path) -> bool:
    block = llm_settings_block()
    return _ensure_block_entries_before_marker_or_anchor(
        path=path,
        block=block,
        marker=SETTINGS_LLM_MARKER,
        anchor="    model_config = SettingsConfigDict(",
        entry_type="setting",
    )


def _ensure_llm_env(path: Path) -> bool:
    block = llm_env_block()
    return _ensure_block_entries_before_marker_or_anchor(
        path=path,
        block=block,
        marker=ENV_LLM_MARKER,
        anchor=None,
        entry_type="env",
    )


def _ensure_block_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    marker: str,
    anchor: str | None,
    entry_type: str,
) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        ) from exc
    missing_lines = _missing_block_lines(
        lines=lines,
        block=block,
        entry_type=entry_type,
    )

    if not missing_lines:
        return False

    insert_at = _find_insert_index(lines=lines, marker=marker, anchor=anchor)
    lines[insert_at:insert_at] = missing_lines + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _module_next_steps(
    *,
    package_name: str,
    module_name: str,
    template_spec: ModuleTemplate,
) -> tuple[str, ...]:
    steps = [
        f"Review src/{package_name}/modules/{module_name}/",
        "Run `polepos check`",
    ]

    if template_spec.features:
        features = ", ".join(template_spec.features)
        steps.append(f"Review generated CRUD options: {features}")

    if template_spec.update_db_models:
        steps.append(
            f'After model changes, run `polepos db revision -m "add '
            f'{module_name} table"`'
        )

    if template_spec.ensure_llm_settings:
        steps.append(
            "Set LLM_API_KEY in .env before calling the generated endpoint"
        )

    return tuple(steps)
