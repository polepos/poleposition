import ast
from pathlib import Path

from pole_position.cli.services.module_remover.io import _read_optional_text


def _router_wiring_ranges(
    path: Path,
    package_name: str,
    module_name: str,
) -> list[tuple[int, int]]:
    if not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return []
    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    ranges = [
        _find_router_import_range(tree, router_module, router_alias),
        _find_router_include_range(tree, router_alias, module_name),
    ]
    return [line_range for line_range in ranges if line_range is not None]


def _has_router_remnant(
    path: Path, package_name: str, module_name: str
) -> bool:
    if not path.is_file():
        return False

    content = _read_optional_text(path)
    if not content:
        return False

    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"

    return (
        router_module in content
        or router_alias in content
        or f'prefix="/{module_name}"' in content
        or f"prefix='/{module_name}'" in content
    )


def _remove_router_wiring(
    path: Path, package_name: str, module_name: str
) -> bool:
    content = _read_optional_text(path)
    if not content:
        return False
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return False
    router_alias = f"{module_name}_router"
    router_module = f"{package_name}.modules.{module_name}.router"
    ranges = [
        _find_router_import_range(tree, router_module, router_alias),
        _find_router_include_range(tree, router_alias, module_name),
    ]
    ranges_to_remove = [
        line_range for line_range in ranges if line_range is not None
    ]

    if not ranges_to_remove:
        return False

    lines = content.splitlines()
    for start, end in sorted(ranges_to_remove, reverse=True):
        del lines[start - 1 : end]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _find_router_import_range(
    tree: ast.Module,
    router_module: str,
    router_alias: str,
) -> tuple[int, int] | None:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        if len(node.names) != 1:
            return None
        alias = node.names[0]
        if alias.name == "router" and alias.asname == router_alias:
            return _node_line_range(node)

    return None


def _router_import_reference_ranges(
    tree: ast.Module,
    router_module: str,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        line_range = _node_line_range(node)
        if line_range is not None:
            ranges.append(line_range)

    return ranges


def _router_aliases_from_imports(
    tree: ast.Module, router_module: str
) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        for alias in node.names:
            if alias.name == "router":
                aliases.add(alias.asname or alias.name)

    return aliases


def _find_router_include_range(
    tree: ast.Module,
    router_alias: str,
    module_name: str,
) -> tuple[int, int] | None:
    for node in tree.body:
        if not isinstance(node, ast.Expr):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not _is_api_router_include_call(node.value):
            continue
        if not node.value.args or not _is_name(
            node.value.args[0], router_alias
        ):
            continue
        if _include_router_keywords_match(node.value, module_name):
            return _node_line_range(node)

    return None


def _router_include_reference_ranges(
    tree: ast.Module,
    router_aliases: set[str],
    module_name: str,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _router_include_references_module(
            node,
            router_aliases,
            module_name,
        ):
            continue
        line_range = _node_line_range(node)
        if line_range is not None:
            ranges.append(line_range)

    return ranges


def _router_include_references_module(
    node: ast.Call,
    router_aliases: set[str],
    module_name: str,
) -> bool:
    if not _is_api_router_include_call(node):
        return False
    if node.args and isinstance(node.args[0], ast.Name):
        if node.args[0].id in router_aliases:
            return True
    if _literal_keyword_value(node, "prefix") == f"/{module_name}":
        return True
    return _literal_keyword_value(node, "tags") in (
        [module_name],
        (module_name,),
    )


def _node_line_range(node: ast.AST) -> tuple[int, int] | None:
    end_lineno = getattr(node, "end_lineno", None)
    if getattr(node, "lineno", None) is None or end_lineno is None:
        return None

    return node.lineno, end_lineno


def _is_api_router_include_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "api_router"
    )


def _is_name(node: ast.AST, expected_name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected_name


def _include_router_keywords_match(node: ast.Call, module_name: str) -> bool:
    prefix = _literal_keyword_value(node, "prefix")
    tags = _literal_keyword_value(node, "tags")

    return prefix == f"/{module_name}" and tags in (
        [module_name],
        (module_name,),
    )


def _literal_keyword_value(node: ast.Call, keyword_name: str) -> object:
    for keyword in node.keywords:
        if keyword.arg == keyword_name:
            return _literal_value(keyword.value)

    return None


def _literal_value(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
