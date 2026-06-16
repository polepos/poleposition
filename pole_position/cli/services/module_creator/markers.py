from pathlib import Path


def _insert_line_before_marker(path: Path, line: str, marker: str) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        ) from exc
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
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        ) from exc
    marker_index = _find_marker_index(lines, marker, path)

    managed_ranges = _collect_managed_block_ranges(
        lines=lines,
        marker_index=marker_index,
        match_prefix=match_prefix,
    )

    managed_blocks = [lines[start : end + 1] for start, end in managed_ranges]
    if any(block == [line] for block in managed_blocks):
        return

    managed_blocks.append([line])
    managed_blocks.sort(key=lambda block: block[0].lower())

    managed_indexes = {
        index
        for start, end in managed_ranges
        for index in range(start, end + 1)
    }
    preserved_prefix = [
        existing
        for index, existing in enumerate(lines[:marker_index])
        if index not in managed_indexes
    ]

    while preserved_prefix and preserved_prefix[0] == "":
        preserved_prefix.pop(0)

    updated_lines = (
        preserved_prefix
        + [entry for block in managed_blocks for entry in block]
        + lines[marker_index:]
    )
    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def _collect_managed_block_ranges(
    *,
    lines: list[str],
    marker_index: int,
    match_prefix: str,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    index = 0

    while index < marker_index:
        line = lines[index]
        if not line.startswith(match_prefix):
            index += 1
            continue

        end = index
        balance = _line_bracket_delta(lines[end])
        continued = lines[end].rstrip().endswith("\\")

        while end + 1 < marker_index and (balance > 0 or continued):
            end += 1
            balance += _line_bracket_delta(lines[end])
            continued = lines[end].rstrip().endswith("\\")

        ranges.append((index, end))
        index = end + 1

    return ranges


def _line_bracket_delta(line: str) -> int:
    return line.count("(") - line.count(")")


def _insert_block_before_marker_or_anchor(
    *,
    path: Path,
    block: list[str],
    marker: str,
    anchor: str | None,
) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Could not read managed text file for module add: {path}: "
            f"{exc.reason}"
        ) from exc
    insert_at = _find_insert_index(lines=lines, marker=marker, anchor=anchor)

    lines[insert_at:insert_at] = block + [""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_insert_index(
    *,
    lines: list[str],
    marker: str,
    anchor: str | None,
) -> int:
    if marker in lines:
        return lines.index(marker)
    if anchor and anchor in lines:
        return lines.index(anchor)
    return len(lines)


def _find_marker_index(lines: list[str], marker: str, path: Path) -> int:
    try:
        return lines.index(marker)
    except ValueError as exc:
        raise RuntimeError(f"Unsupported managed block layout: {path}") from exc
