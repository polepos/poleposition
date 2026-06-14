"""File and source helpers shared by the project-check modules."""

import ast
from pathlib import Path


def _parse_python_source(
    content: str,
    path: Path,
    problems: list[str],
) -> ast.Module | None:
    try:
        return ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        problems.append(
            f"Could not parse Python file for lifecycle checks: {path}: {exc}"
        )
        return None


def _safe_marker_index(lines: list[str], marker: str) -> int:
    try:
        return lines.index(marker)
    except ValueError:
        return len(lines)


def _settings_keys(settings_content: str) -> set[str]:
    keys: set[str] = set()
    for line in settings_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key = stripped.split(":", 1)[0]
        if key.isidentifier():
            keys.add(key)

    return keys


def _env_keys(env_content: str) -> set[str]:
    keys: set[str] = set()
    for line in env_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0]
        if key:
            keys.add(key)

    return keys


def _read_file_lines(
    path: Path,
    problems: list[str] | None = None,
) -> list[str] | None:
    content = _read_file_text(path, problems)
    if content is None:
        return None

    return content.splitlines()


def _read_file_text(
    path: Path,
    problems: list[str] | None = None,
) -> str | None:
    if not path.is_file():
        return None

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        if problems is not None:
            problem = _unreadable_text_file_problem(path, exc)
            if problem not in problems:
                problems.append(problem)
        return None


def _unreadable_text_file_problem(path: Path, exc: UnicodeDecodeError) -> str:
    return f"Could not read generated text file as UTF-8: {path}: {exc.reason}"
