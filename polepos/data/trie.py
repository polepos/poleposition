from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

V = TypeVar("V")
_MISSING = object()


@dataclass
class _TrieNode(Generic[V]):
    children: dict[str, _TrieNode[V]] = field(default_factory=dict)
    value: V | object = _MISSING


class Trie(Generic[V]):
    """A prefix tree for string keys."""

    def __init__(self) -> None:
        self._root: _TrieNode[V] = _TrieNode()
        self._size = 0

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self.get(key, _MISSING) is not _MISSING

    def __len__(self) -> int:
        return self._size

    def insert(self, key: str, value: V | object = _MISSING) -> None:
        node = self._root
        for char in key:
            node = node.children.setdefault(char, _TrieNode())
        if node.value is _MISSING:
            self._size += 1
        node.value = key if value is _MISSING else value

    def get(self, key: str, default: V | object = None) -> V | object:
        node = self._find_node(key)
        if node is None or node.value is _MISSING:
            return default
        return node.value

    def delete(self, key: str) -> None:
        # Walk down iteratively, recording the path, then prune now-empty nodes
        # on the way back up. Recursion would risk RecursionError on a long key
        # (stack depth grew with len(key)), the same class of bug that made
        # UnionFind.find iterative.
        path: list[tuple[_TrieNode[V], str]] = []
        node = self._root
        for char in key:
            child = node.children.get(char)
            if child is None:
                raise KeyError(key)
            path.append((node, char))
            node = child

        if node.value is _MISSING:
            raise KeyError(key)
        node.value = _MISSING
        self._size -= 1

        for parent, char in reversed(path):
            child = parent.children[char]
            if child.value is _MISSING and not child.children:
                del parent.children[char]
            else:
                break

    def starts_with(self, prefix: str) -> bool:
        return self._find_node(prefix) is not None

    def keys(self, prefix: str = "") -> list[str]:
        return [key for key, _ in self.items(prefix)]

    def items(self, prefix: str = "") -> list[tuple[str, V]]:
        node = self._find_node(prefix)
        if node is None:
            return []
        items: list[tuple[str, V]] = []
        self._collect(prefix, node, items)
        return items

    def longest_prefix_of(self, text: str) -> str:
        node = self._root
        longest = 0
        for index, char in enumerate(text, start=1):
            node = node.children.get(char)
            if node is None:
                break
            if node.value is not _MISSING:
                longest = index
        return text[:longest]

    def _find_node(self, key: str) -> _TrieNode[V] | None:
        node = self._root
        for char in key:
            node = node.children.get(char)
            if node is None:
                return None
        return node

    def _collect(
        self,
        prefix: str,
        node: _TrieNode[V],
        items: list[tuple[str, V]],
    ) -> None:
        # Iterative pre-order walk. Children are pushed in reverse-sorted order
        # so they pop in ascending order, keeping keys() lexicographically
        # sorted. Recursion would risk RecursionError on a deep trie (one frame
        # per character), so keys()/items() stay iterative like Graph.dfs.
        stack: list[tuple[str, _TrieNode[V]]] = [(prefix, node)]
        while stack:
            current_prefix, current = stack.pop()
            if current.value is not _MISSING:
                items.append((current_prefix, current.value))  # type: ignore[arg-type]
            for char in sorted(current.children, reverse=True):
                stack.append((current_prefix + char, current.children[char]))
