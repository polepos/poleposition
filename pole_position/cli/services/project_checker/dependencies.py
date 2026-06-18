"""Architectural checks: circular dependencies between generated modules.

Builds the directed import graph between ``src/<package>/modules/<name>``
packages and reports any cycle (for example ``customers -> billing ->
notifications -> customers``). The graph itself is a ``polepos.data.Graph``,
dogfooding the data-structures library that ships with the package; the cycle
path is recovered with a small depth-first search since the graph exposes cycle
existence (via ``topological_sort``) but not the offending path.
"""

import ast
from pathlib import Path

from pole_position.cli.services.project_checker.constants import (
    IGNORED_MODULE_DIRECTORIES,
)
from pole_position.cli.services.project_checker.io import (
    _parse_python_source,
    _read_file_text,
)
from polepos.data import Graph


def _check_module_dependencies(problems: list[str], package_root: Path) -> None:
    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return

    module_names = _discover_module_names(modules_root)
    if len(module_names) < 2:
        return

    graph = _build_dependency_graph(
        modules_root=modules_root,
        module_names=module_names,
        package_name=package_root.name,
        problems=problems,
    )

    for cycle in _find_cycles(graph):
        path = " -> ".join([*cycle, cycle[0]])
        problems.append(f"Circular module dependency detected: {path}")


def _discover_module_names(modules_root: Path) -> set[str]:
    return {
        entry.name
        for entry in modules_root.iterdir()
        if entry.is_dir() and entry.name not in IGNORED_MODULE_DIRECTORIES
    }


def _build_dependency_graph(
    *,
    modules_root: Path,
    module_names: set[str],
    package_name: str,
    problems: list[str],
) -> Graph:
    graph = Graph(directed=True)
    for module_name in sorted(module_names):
        graph.add_node(module_name)

    prefix = f"{package_name}.modules."
    for module_name in sorted(module_names):
        imported = _imported_modules(
            module_root=modules_root / module_name,
            prefix=prefix,
            problems=problems,
        )
        for other in sorted(imported):
            if other != module_name and other in module_names:
                graph.add_edge(module_name, other)

    return graph


def _imported_modules(
    *,
    module_root: Path,
    prefix: str,
    problems: list[str],
) -> set[str]:
    imported: set[str] = set()
    for path in sorted(module_root.rglob("*.py")):
        content = _read_file_text(path, problems)
        if content is None:
            continue
        tree = _parse_python_source(content, path, problems)
        if tree is None:
            continue
        for node in ast.walk(tree):
            for dotted in _imported_dotted_names(node):
                name = _module_after_prefix(dotted, prefix)
                if name is not None:
                    imported.add(name)
    return imported


def _imported_dotted_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.ImportFrom):
        # Relative imports carry no usable absolute module prefix here.
        return (node.module,) if node.module and node.level == 0 else ()
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    return ()


def _module_after_prefix(dotted: str, prefix: str) -> str | None:
    if not dotted.startswith(prefix):
        return None
    rest = dotted[len(prefix) :]
    head = rest.split(".", 1)[0]
    return head or None


def _find_cycles(graph: Graph) -> list[tuple[str, ...]]:
    white, gray, black = 0, 1, 2
    color = dict.fromkeys(graph.nodes(), white)
    stack: list[str] = []
    seen: set[tuple[str, ...]] = set()
    cycles: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        color[node] = gray
        stack.append(node)
        for neighbor in graph.neighbors(node):
            if color.get(neighbor) == gray:
                start = stack.index(neighbor)
                key = _normalize_cycle(stack[start:])
                if key and key not in seen:
                    seen.add(key)
                    cycles.append(key)
            elif color.get(neighbor, white) == white:
                visit(neighbor)
        color[node] = black
        stack.pop()

    for node in sorted(graph.nodes()):
        if color[node] == white:
            visit(node)

    return sorted(cycles)


def _normalize_cycle(nodes: list[str]) -> tuple[str, ...]:
    """Rotate a cycle to start at its smallest node so the same loop found from
    different entry points collapses to one stable representation."""
    if not nodes:
        return ()
    pivot = nodes.index(min(nodes))
    return tuple(nodes[pivot:] + nodes[:pivot])
