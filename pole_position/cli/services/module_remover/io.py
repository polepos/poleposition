from pathlib import Path


def _line_exists(path: Path, line: str) -> bool:
    if not path.is_file():
        return False

    try:
        return line in path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False


def _read_optional_text(path: Path) -> str:
    if not path.is_file():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _file_content_matches(path: Path, expected_content: str | None) -> bool:
    if expected_content is None:
        return False

    return _read_optional_text(path) == expected_content


def _would_remove_lines_by_prefix(path: Path, prefixes: list[str]) -> bool:
    if not path.is_file():
        return False

    return any(
        any(line.strip().startswith(prefix) for prefix in prefixes)
        for line in _read_optional_text(path).splitlines()
    )


def _module_export_line(module_name: str) -> str:
    return f'    "{module_name}",'


def _model_import_line(package_name: str, module_name: str) -> str:
    return (
        f"    from {package_name}.modules.{module_name} import model  # noqa: "
        f"F401"
    )


def _remove_line(path: Path, line: str) -> bool:
    return _remove_lines(path, [line])


def _remove_lines(path: Path, lines_to_remove: list[str]) -> bool:
    text = _read_optional_text(path)
    if not text:
        return False
    lines = text.splitlines()
    removals = set(lines_to_remove)
    updated_lines = [line for line in lines if line not in removals]

    if updated_lines == lines:
        return False

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return True


def _remove_lines_by_prefix(path: Path, prefixes: list[str]) -> bool:
    if not path.is_file():
        return False

    lines = _read_optional_text(path).splitlines()
    if not lines:
        return False

    updated_lines = [
        line
        for line in lines
        if not any(line.strip().startswith(prefix) for prefix in prefixes)
    ]

    if updated_lines == lines:
        return False

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return True
