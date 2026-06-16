import re
from pathlib import Path

from pole_position.cli.services.module_remover.io import _read_optional_text


def _module_reference_matchers(
    package_name: str, module_name: str
) -> tuple[re.Pattern[str], ...]:
    name = re.escape(module_name)
    pkg = re.escape(package_name)
    return (
        # `<pkg>.modules.<name>` not followed by another identifier char, so
        # removing `user` never touches `users`.
        re.compile(rf"\b{pkg}\.modules\.{name}(?!\w)"),
        re.compile(rf"\b{name}_router\b"),
        re.compile(rf"""prefix=(['"])/{name}\1"""),
    )


def _line_references_module(
    line: str, matchers: tuple[re.Pattern[str], ...]
) -> bool:
    return any(matcher.search(line) for matcher in matchers)


def _module_test_files(project_root: Path, module_name: str) -> list[Path]:
    tests_root = project_root / "tests"
    if not tests_root.is_dir():
        return []

    found: list[Path] = []
    for pattern in (f"test_{module_name}.py", f"test_{module_name}_*.py"):
        found.extend(tests_root.rglob(pattern))
    return list(dict.fromkeys(sorted(found)))


def _has_generic_module_reference(
    *,
    project_root: Path,
    package_root: Path,
    module_name: str,
) -> bool:
    matchers = _module_reference_matchers(package_root.name, module_name)
    managed_files = (
        package_root / "modules" / "__init__.py",
        package_root / "api" / "router.py",
        package_root / "db" / "models.py",
    )
    for path in managed_files:
        text = _read_optional_text(path)
        if any(matcher.search(text) for matcher in matchers):
            return True

    return bool(_module_test_files(project_root, module_name))


def _remove_module_reference_lines(
    path: Path, package_name: str, module_name: str
) -> bool:
    if not path.is_file():
        return False

    matchers = _module_reference_matchers(package_name, module_name)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False

    kept = [
        line for line in lines if not _line_references_module(line, matchers)
    ]
    if len(kept) == len(lines):
        return False

    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return True


def _remove_module_test_files(
    project_root: Path, module_name: str
) -> list[Path]:
    removed: list[Path] = []
    for path in _module_test_files(project_root, module_name):
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed
