from pathlib import Path


def _ensure_settings_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
) -> bool:
    return _ensure_block_entries_before_marker_or_anchor(
        path=path,
        block=block,
        markers=markers,
        anchor=anchor,
        key_for_line=_settings_line_key,
    )


def _ensure_env_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
) -> bool:
    return _ensure_block_entries_before_marker_or_anchor(
        path=path,
        block=block,
        markers=markers,
        anchor=anchor,
        key_for_line=_env_line_key,
    )


def _ensure_block_entries_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    markers: list[str],
    anchor: str | None,
    key_for_line,
) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    missing_lines = _missing_block_lines(
        lines=lines,
        block=block,
        key_for_line=key_for_line,
    )

    if not missing_lines:
        return False

    insert_at = _find_insert_index(lines, markers, anchor)
    lines[insert_at:insert_at] = missing_lines + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _settings_line_key(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("#"):
        return None
    if ":" not in stripped:
        return None
    key = stripped.split(":", 1)[0]
    return key if key.isidentifier() else None


def _env_line_key(line: str) -> str | None:
    return _active_env_line_key(line)


def _active_env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0]
    return key if key else None


def _commented_env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    stripped = stripped[1:].strip()
    if "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0]
    return key if key else None


def _missing_block_lines(
    *,
    lines: list[str],
    block: list[str],
    key_for_line,
) -> list[str]:
    if key_for_line is not _env_line_key:
        existing_keys = {
            key for line in lines if (key := key_for_line(line)) is not None
        }
        return [
            line
            for line in block
            if (key := key_for_line(line)) is not None
            and key not in existing_keys
        ]

    active_keys = {
        key for line in lines if (key := _active_env_line_key(line)) is not None
    }
    commented_keys = {
        key
        for line in lines
        if (key := _commented_env_line_key(line)) is not None
    }
    missing_lines: list[str] = []
    for line in block:
        active_key = _active_env_line_key(line)
        if active_key is not None:
            if active_key not in active_keys:
                missing_lines.append(line)
            continue

        commented_key = _commented_env_line_key(line)
        if commented_key is None:
            continue
        if (
            commented_key not in active_keys
            and commented_key not in commented_keys
        ):
            missing_lines.append(line)

    return missing_lines


def _find_insert_index(
    lines: list[str],
    markers: list[str],
    anchor: str | None,
) -> int:
    insert_at = None

    for marker in markers:
        if marker in lines:
            insert_at = lines.index(marker)
            break

    if insert_at is None and anchor and anchor in lines:
        insert_at = lines.index(anchor)

    if insert_at is None:
        insert_at = len(lines)

    return insert_at
