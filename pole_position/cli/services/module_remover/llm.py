import shutil
from pathlib import Path

from pole_position.cli.services.module_remover.io import (
    _file_content_matches,
    _read_optional_text,
    _remove_lines_by_prefix,
    _would_remove_lines_by_prefix,
)
from pole_position.cli.services.module_remover.templates import (
    _detect_module_contract,
)
from pole_position.cli.services.module_templates import (
    llm_env_block,
    llm_integration_files,
    llm_settings_block,
)


def _planned_llm_settings_updates(
    project_root: Path, package_root: Path
) -> list[Path]:
    updated_files: list[Path] = []
    settings_path = package_root / "settings.py"
    env_path = project_root / ".env.example"

    if _would_remove_lines_by_prefix(settings_path, _llm_setting_prefixes()):
        updated_files.append(settings_path)
    if _would_remove_lines_by_prefix(env_path, _llm_env_prefixes()):
        updated_files.append(env_path)

    return updated_files


def _planned_llm_integration_paths(
    package_root: Path, package_name: str
) -> list[Path]:
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


def _has_remaining_ai_prompt_module(
    *,
    project_root: Path,
    modules_root: Path,
    removed_module_name: str,
) -> bool:
    for module_root in modules_root.iterdir():
        if not module_root.is_dir() or module_root.name == removed_module_name:
            continue
        contract = _detect_module_contract(
            project_root, module_root, module_root.name
        )
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
    return [
        line.strip().split(":", 1)[0] + ":" for line in llm_settings_block()
    ]


def _llm_env_prefixes() -> list[str]:
    env_prefixes = []
    for line in llm_env_block():
        env_prefixes.append(
            line.split("=", 1)[0] + "=" if "=" in line else line
        )
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


def _remove_llm_integration_files(
    package_root: Path, package_name: str
) -> list[Path]:
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
