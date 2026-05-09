from dataclasses import dataclass
from pathlib import Path

from pole_position.cli.services.project_locator import find_package_root, find_project_root
from pole_position.cli.services.module_templates import (
    ModuleTemplate,
    SUPPORTED_MODULE_TEMPLATES,
    build_module_template,
    llm_env_block,
    llm_integration_files,
    llm_settings_block,
)

ROUTER_IMPORTS_MARKER = "# polepos:router-imports"
ROUTER_INCLUDES_MARKER = "# polepos:router-includes"
MODEL_IMPORTS_MARKER = "    # polepos:model-imports"
MODULE_EXPORTS_MARKER = "    # polepos:module-exports"
SETTINGS_LLM_MARKER = "    # polepos:llm-settings"
ENV_LLM_MARKER = "# polepos:llm-env"


@dataclass(frozen=True)
class AddedModuleResult:
    module_name: str
    template: str
    project_root: Path
    package_root: Path
    module_files: tuple[Path, ...]
    test_files: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]

    @property
    def package_name(self) -> str:
        return self.package_root.name


def add_module(
    module_name: str,
    template: str = "standard",
    cwd: Path | None = None,
) -> AddedModuleResult:
    if template not in SUPPORTED_MODULE_TEMPLATES:
        supported = ", ".join(SUPPORTED_MODULE_TEMPLATES)
        raise ValueError(
            f"Unsupported module template '{template}'. Expected one of: {supported}."
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
    _update_api_router(package_root / "api" / "router.py", package_name, module_name)
    updated_files.append(package_root / "api" / "router.py")
    if template_spec.update_db_models:
        _update_db_models(package_root / "db" / "models.py", package_name, module_name)
        updated_files.append(package_root / "db" / "models.py")
    if template_spec.ensure_llm_integrations:
        updated_files.extend(_ensure_llm_integrations(package_root, package_name))
    if template_spec.ensure_llm_settings:
        if _ensure_llm_settings(package_root / "settings.py"):
            updated_files.append(package_root / "settings.py")
        if _ensure_llm_env(project_root / ".env.example"):
            updated_files.append(project_root / ".env.example")

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

    _collect_missing_marker(
        problems,
        modules_root / "__init__.py",
        MODULE_EXPORTS_MARKER,
    )
    _collect_missing_marker(
        problems,
        package_root / "api" / "router.py",
        ROUTER_IMPORTS_MARKER,
    )
    _collect_missing_marker(
        problems,
        package_root / "api" / "router.py",
        ROUTER_INCLUDES_MARKER,
    )

    if template_spec.update_db_models:
        _collect_missing_marker(
            problems,
            package_root / "db" / "models.py",
            MODEL_IMPORTS_MARKER,
        )

    if template_spec.ensure_llm_settings:
        _collect_missing_marker_unless_content_exists(
            problems,
            package_root / "settings.py",
            marker=SETTINGS_LLM_MARKER,
            existing_content="llm_provider:",
        )
        _collect_missing_marker_unless_content_exists(
            problems,
            project_root / ".env.example",
            marker=ENV_LLM_MARKER,
            existing_content="LLM_PROVIDER=",
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


def _collect_missing_marker(problems: list[str], path: Path, marker: str) -> None:
    lines = _read_managed_file_lines(problems, path)
    if lines is None:
        return

    if marker not in lines:
        problems.append(f"Required managed marker '{marker}' is missing in {path}")


def _collect_missing_marker_unless_content_exists(
    problems: list[str],
    path: Path,
    *,
    marker: str,
    existing_content: str,
) -> None:
    content = _read_managed_file_text(problems, path)
    if content is None or existing_content in content:
        return

    if marker not in content.splitlines():
        problems.append(f"Required managed marker '{marker}' is missing in {path}")


def _read_managed_file_text(problems: list[str], path: Path) -> str | None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return None

    return path.read_text(encoding="utf-8")


def _read_managed_file_lines(problems: list[str], path: Path) -> list[str] | None:
    content = _read_managed_file_text(problems, path)
    if content is None:
        return None

    return content.splitlines()


def _write_module_files(module_root: Path, files: dict[str, str]) -> list[Path]:
    module_root.mkdir(parents=True)
    written: list[Path] = []

    for file_name, content in files.items():
        path = module_root / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return written


def _write_module_tests(tests_root: Path, template_spec: ModuleTemplate) -> list[Path]:
    integration_root = tests_root / "integration"
    unit_root = tests_root / "unit"
    integration_root.mkdir(parents=True, exist_ok=True)
    unit_root.mkdir(parents=True, exist_ok=True)

    integration_test = integration_root / template_spec.integration_test_name
    unit_test = unit_root / template_spec.unit_test_name

    integration_test.write_text(
        template_spec.integration_test_content,
        encoding="utf-8",
    )
    unit_test.write_text(
        template_spec.unit_test_content,
        encoding="utf-8",
    )
    return [integration_test, unit_test]


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
        f"from {package_name}.modules.{module_name}.router import router as {module_name}_router"
    )
    include_line = (
        f'api_router.include_router({module_name}_router, prefix="/{module_name}", '
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
    import_line = f"    from {package_name}.modules.{module_name} import model  # noqa: F401"
    _insert_sorted_line_before_marker(
        path=path,
        line=import_line,
        marker=MODEL_IMPORTS_MARKER,
        match_prefix="    from ",
    )


def _ensure_llm_integrations(package_root: Path, package_name: str) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in llm_integration_files(package_name).items():
        path = package_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written


def _ensure_llm_settings(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if "llm_provider:" in content:
        return False

    block = llm_settings_block()
    _insert_block_before_marker_or_anchor(
        path=path,
        block=block,
        marker=SETTINGS_LLM_MARKER,
        anchor="    model_config = SettingsConfigDict(",
    )
    return True


def _ensure_llm_env(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if "LLM_PROVIDER=" in content:
        return False

    block = llm_env_block()
    _insert_block_before_marker_or_anchor(
        path=path,
        block=block,
        marker=ENV_LLM_MARKER,
        anchor=None,
    )
    return True


def _insert_line_before_marker(path: Path, line: str, marker: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_index = _find_marker_index(lines, marker, path)

    if line in lines:
        return

    lines.insert(marker_index, line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _insert_sorted_line_before_marker(
    *,
    path: Path,
    line: str,
    marker: str,
    match_prefix: str,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_index = _find_marker_index(lines, marker, path)

    managed_lines = [
        existing
        for existing in lines[:marker_index]
        if existing.startswith(match_prefix)
    ]
    if line in managed_lines:
        return

    managed_lines.append(line)
    managed_lines.sort()
    preserved_prefix = [
        existing
        for existing in lines[:marker_index]
        if not existing.startswith(match_prefix)
    ]

    while preserved_prefix and preserved_prefix[0] == "":
        preserved_prefix.pop(0)

    updated_lines = preserved_prefix + managed_lines + lines[marker_index:]
    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def _insert_block_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    marker: str,
    anchor: str | None,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()

    if marker in lines:
        insert_at = lines.index(marker)
    elif anchor and anchor in lines:
        insert_at = lines.index(anchor)
    else:
        insert_at = len(lines)

    lines[insert_at:insert_at] = block + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_marker_index(lines: list[str], marker: str, path: Path) -> int:
    try:
        return lines.index(marker)
    except ValueError as exc:
        raise RuntimeError(f"Unsupported managed block layout: {path}") from exc


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

    if template_spec.update_db_models:
        steps.append(
            f'After model changes, run `polepos db revision -m "add {module_name} table"`'
        )

    if template_spec.ensure_llm_settings:
        steps.append("Set LLM_API_KEY in .env before calling the generated endpoint")

    return tuple(steps)
