import ast
from pathlib import Path

from pole_position.cli.services.project_wiring import (
    is_api_router_include_call,
    is_name,
    literal_keyword_value,
)


def _line_exists(path: Path, line: str) -> bool:
    if not path.is_file():
        return False

    try:
        return line in path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False


def _has_router_reference(
    path: Path, package_name: str, module_name: str
) -> bool:
    if not path.is_file():
        return False

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return False

    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == router_module:
            return True
        if not isinstance(node, ast.Call):
            continue
        if not is_api_router_include_call(node):
            continue
        if node.args and is_name(node.args[0], router_alias):
            return True
        if literal_keyword_value(node, "prefix") == f"/{module_name}":
            return True

    return False
