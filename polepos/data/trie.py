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
        if not self._delete(self._root, key, 0):
            raise KeyError(key)
        self._size -= 1

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
        if node.value is not _MISSING:
            items.append((prefix, node.value))  # type: ignore[arg-type]
        for char in sorted(node.children):
            self._collect(prefix + char, node.children[char], items)

    def _delete(self, node: _TrieNode[V], key: str, index: int) -> bool:
        if index == len(key):
            if node.value is _MISSING:
                return False
            node.value = _MISSING
            return True

        char = key[index]
        child = node.children.get(char)
        if child is None:
            return False

        deleted = self._delete(child, key, index + 1)
        if deleted and child.value is _MISSING and not child.children:
            del node.children[char]
        return deleted
