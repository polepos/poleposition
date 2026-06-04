from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableSet
from typing import Generic, TypeVar

T = TypeVar("T")


class OrderedSet(MutableSet[T], Generic[T]):
    """A set that preserves insertion order."""

    def __init__(self, values: Iterable[T] = ()) -> None:
        self._items: dict[T, None] = {}
        for value in values:
            self.add(value)

    def __contains__(self, value: object) -> bool:
        return value in self._items

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def add(self, value: T) -> None:
        self._items[value] = None

    def discard(self, value: T) -> None:
        self._items.pop(value, None)

    def pop(self, *, last: bool = True) -> T:
        if not self._items:
            raise KeyError("set is empty")
        key = next(reversed(self._items)) if last else next(iter(self._items))
        del self._items[key]
        return key
