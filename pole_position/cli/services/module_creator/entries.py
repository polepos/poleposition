def _line_key(line: str, *, entry_type: str) -> str | None:
    stripped = line.strip()
    if entry_type == "setting":
        if stripped.startswith("#"):
            return None
        if ":" not in stripped:
            return None
        key = stripped.split(":", 1)[0]
        return key if key.isidentifier() else None

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


def _expected_block_keys(block: list[str], *, entry_type: str) -> list[str]:
    if entry_type != "env":
        return [
            key
            for line in block
            if (key := _line_key(line, entry_type=entry_type)) is not None
        ]

    return [
        key
        for line in block
        if (key := _line_key(line, entry_type=entry_type)) is not None
    ]


def _existing_entry_keys(lines: list[str], *, entry_type: str) -> set[str]:
    return {
        key
        for line in lines
        if (key := _line_key(line, entry_type=entry_type)) is not None
    }


def _missing_block_lines(
    *,
    lines: list[str],
    block: list[str],
    entry_type: str,
) -> list[str]:
    if entry_type != "env":
        existing_keys = _existing_entry_keys(lines, entry_type=entry_type)
        return [
            line
            for line in block
            if (key := _line_key(line, entry_type=entry_type)) is not None
            and key not in existing_keys
        ]

    active_keys = _existing_entry_keys(lines, entry_type=entry_type)
    commented_keys = {
        key
        for line in lines
        if (key := _commented_env_line_key(line)) is not None
    }
    missing_lines: list[str] = []
    for line in block:
        active_key = _line_key(line, entry_type=entry_type)
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
