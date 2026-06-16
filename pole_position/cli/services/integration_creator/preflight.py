from pathlib import Path

from pole_position.cli.services.integration_creator.blocks import (
    _active_env_line_key,
    _settings_line_key,
)
from pole_position.cli.services.integration_creator.constants import (
    ENV_INTEGRATION_MARKER,
    SETTINGS_INTEGRATION_MARKER,
)
from pole_position.cli.services.integration_specs import IntegrationContract
from pole_position.cli.services.project_manifest import read_project_manifest
from pole_position.cli.services.pyproject_editor import (
    ensure_project_dependency_text,
)


def _validate_add_integration_preflight(
    *,
    project_root: Path,
    package_root: Path,
    integration_root: Path,
    contract: IntegrationContract,
) -> None:
    problems: list[str] = []
    pyproject_path = project_root / "pyproject.toml"

    _collect_manifest_read_error(problems, project_root)

    if integration_root.exists():
        problems.append(f"Integration already exists: {contract.name}")

    _collect_required_file(problems, pyproject_path)
    _collect_patchable_project_dependency(
        problems, pyproject_path, contract.dependency
    )
    _collect_missing_marker_unless_entries_exist(
        problems,
        package_root / "settings.py",
        SETTINGS_INTEGRATION_MARKER,
        entries=contract.settings,
        entry_type="setting",
    )
    _collect_missing_marker_unless_entries_exist(
        problems,
        project_root / ".env.example",
        ENV_INTEGRATION_MARKER,
        entries=contract.env,
        entry_type="env",
    )

    if problems:
        formatted_problems = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(
            "Cannot add integration because the project layout is not ready:\n"
            f"{formatted_problems}"
        )


def _collect_required_file(problems: list[str], path: Path) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")


def _collect_manifest_read_error(
    problems: list[str], project_root: Path
) -> None:
    manifest = read_project_manifest(project_root)
    if manifest.read_error is not None:
        problems.append(manifest.read_error)


def _collect_patchable_project_dependency(
    problems: list[str],
    path: Path,
    dependency: str | None,
) -> None:
    if dependency is None or not path.is_file():
        return

    try:
        content = path.read_text(encoding="utf-8")
        ensure_project_dependency_text(
            content,
            dependency,
            path_label=str(path),
        )
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for integration add: "
            f"{path}: {exc.reason}"
        )
    except RuntimeError as exc:
        problems.append(str(exc))


def _collect_missing_marker(
    problems: list[str], path: Path, marker: str
) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for integration add: "
            f"{path}: {exc.reason}"
        )
        return

    if marker not in lines:
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _collect_missing_marker_unless_entries_exist(
    problems: list[str],
    path: Path,
    marker: str,
    *,
    entries: tuple[str, ...],
    entry_type: str,
) -> None:
    if not path.is_file():
        problems.append(f"Required managed file is missing: {path}")
        return

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        problems.append(
            f"Could not read managed text file for integration add: "
            f"{path}: {exc.reason}"
        )
        return

    if all(
        _entry_exists(content, entry, entry_type=entry_type)
        for entry in entries
    ):
        return

    if marker not in content.splitlines():
        problems.append(
            f"Required managed marker '{marker}' is missing in {path}"
        )


def _entry_exists(content: str, entry: str, *, entry_type: str) -> bool:
    if entry_type == "setting":
        return any(
            _settings_line_key(line) == entry for line in content.splitlines()
        )

    return any(
        _active_env_line_key(line) == entry for line in content.splitlines()
    )
