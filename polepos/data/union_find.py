from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar

T = TypeVar("T")


class UnionFind(Generic[T]):
    """Disjoint-set union with path compression and union by size."""

    def __init__(self, values: Iterable[T] = ()) -> None:
        self._parent: dict[T, T] = {}
        self._size: dict[T, int] = {}
        for value in values:
            self.add(value)

    def __contains__(self, value: object) -> bool:
        return value in self._parent

    def __len__(self) -> int:
        return len(self._parent)

    def add(self, value: T) -> None:
        if value in self._parent:
            return
        self._parent[value] = value
        self._size[value] = 1

    def find(self, value: T) -> T:
        self.add(value)
        # Iterative two-pass find: locate the root, then compress the path.
        # Recursion would risk RecursionError on long chains before compression.
        root = value
        while self._parent[root] != root:
            root = self._parent[root]

        node = value
        while self._parent[node] != root:
            self._parent[node], node = root, self._parent[node]
        return root

    def union(self, left: T, right: T) -> T:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return left_root

        if self._size[left_root] < self._size[right_root]:
            left_root, right_root = right_root, left_root

        self._parent[right_root] = left_root
        self._size[left_root] += self._size[right_root]
        del self._size[right_root]
        return left_root

    def connected(self, left: T, right: T) -> bool:
        return self.find(left) == self.find(right)

    def component_size(self, value: T) -> int:
        return self._size[self.find(value)]

    def components(self) -> list[set[T]]:
        grouped: dict[T, set[T]] = {}
        for value in list(self._parent):
            grouped.setdefault(self.find(value), set()).add(value)
        return list(grouped.values())
