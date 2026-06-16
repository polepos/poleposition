from pathlib import Path

from pole_position.cli.services.module_creator.constants import (
    ENV_LLM_MARKER,
    SETTINGS_LLM_MARKER,
)
from pole_position.cli.services.module_creator.entries import (
    _missing_block_lines,
)
from pole_position.cli.services.module_creator.markers import (
    _find_insert_index,
)
from pole_position.cli.services.module_templates import (
    llm_env_block,
    llm_integration_files,
    llm_settings_block,
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
