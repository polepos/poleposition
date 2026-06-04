from __future__ import annotations

from bisect import bisect_left as _bisect_left
from bisect import bisect_right as _bisect_right
from bisect import insort_right
from collections.abc import Iterable, Iterator, MutableMapping, MutableSet
from typing import Generic, TypeVar, overload

K = TypeVar("K")
T = TypeVar("T")
V = TypeVar("V")


def _irange_bounds(
    items: list,
    minimum: object | None,
    maximum: object | None,
    inclusive: tuple[bool, bool],
) -> tuple[int, int]:
    """Resolve the slice bounds for a half-open range over a sorted list."""
    start = 0
    stop = len(items)
    if minimum is not None:
        start = (
            _bisect_left(items, minimum)
            if inclusive[0]
            else _bisect_right(items, minimum)
        )
    if maximum is not None:
        stop = (
            _bisect_right(items, maximum)
            if inclusive[1]
            else _bisect_left(items, maximum)
        )
    return start, stop


class SortedList(Generic[T]):
    """A list that keeps values in sorted order."""

    def __init__(self, values: Iterable[T] = ()) -> None:
        self._items = sorted(values)

    def __contains__(self, value: object) -> bool:
        index = _bisect_left(self._items, value)  # type: ignore[arg-type]
        return index < len(self._items) and self._items[index] == value

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index: int | slice) -> T | list[T]:
        return self._items[index]

    def add(self, value: T) -> None:
        insort_right(self._items, value)

    def discard(self, value: T) -> bool:
        index = self.bisect_left(value)
        if index >= len(self._items) or self._items[index] != value:
            return False
        self._items.pop(index)
        return True

    def remove(self, value: T) -> None:
        if not self.discard(value):
            raise ValueError(f"{value!r} is not in list")

    def pop(self, index: int = -1) -> T:
        return self._items.pop(index)

    def bisect_left(self, value: T) -> int:
        return _bisect_left(self._items, value)

    def bisect_right(self, value: T) -> int:
        return _bisect_right(self._items, value)

    def count(self, value: T) -> int:
        return self.bisect_right(value) - self.bisect_left(value)

    def irange(
        self,
        minimum: T | None = None,
        maximum: T | None = None,
        *,
        inclusive: tuple[bool, bool] = (True, True),
    ) -> Iterator[T]:
        start, stop = _irange_bounds(self._items, minimum, maximum, inclusive)
        yield from self._items[start:stop]

    def to_list(self) -> list[T]:
        return list(self._items)


class SortedSet(MutableSet[T], Generic[T]):
    """A set that iterates in sorted order."""

    def __init__(self, values: Iterable[T] = ()) -> None:
        self._set: set[T] = set()
        self._items: list[T] = []
        for value in values:
            self.add(value)

    def __contains__(self, value: object) -> bool:
        return value in self._set

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._set)

    def add(self, value: T) -> None:
        if value in self._set:
            return
        self._set.add(value)
        insort_right(self._items, value)

    def discard(self, value: T) -> None:
        if value not in self._set:
            return
        self._set.remove(value)
        self._items.pop(_bisect_left(self._items, value))

    def pop(self, index: int = -1) -> T:  # type: ignore[override]
        value = self._items.pop(index)
        self._set.remove(value)
        return value

    def bisect_left(self, value: T) -> int:
        return _bisect_left(self._items, value)

    def bisect_right(self, value: T) -> int:
        return _bisect_right(self._items, value)

    def irange(
        self,
        minimum: T | None = None,
        maximum: T | None = None,
        *,
        inclusive: tuple[bool, bool] = (True, True),
    ) -> Iterator[T]:
        start, stop = _irange_bounds(self._items, minimum, maximum, inclusive)
        yield from self._items[start:stop]


class SortedDict(MutableMapping[K, V], Generic[K, V]):
    """A dictionary that iterates keys in sorted order."""

    def __init__(self, values: Iterable[tuple[K, V]] = ()) -> None:
        self._keys: list[K] = []
        self._values: dict[K, V] = {}
        for key, value in values:
            self[key] = value

    def __getitem__(self, key: K) -> V:
        return self._values[key]

    def __setitem__(self, key: K, value: V) -> None:
        if key not in self._values:
            insort_right(self._keys, key)
        self._values[key] = value

    def __delitem__(self, key: K) -> None:
        del self._values[key]
        self._keys.pop(_bisect_left(self._keys, key))

    def __iter__(self) -> Iterator[K]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._values)

    def bisect_left(self, key: K) -> int:
        return _bisect_left(self._keys, key)

    def bisect_right(self, key: K) -> int:
        return _bisect_right(self._keys, key)

    def peekitem(self, index: int = 0) -> tuple[K, V]:
        key = self._keys[index]
        return key, self._values[key]

    def irange(
        self,
        minimum: K | None = None,
        maximum: K | None = None,
        *,
        inclusive: tuple[bool, bool] = (True, True),
    ) -> Iterator[tuple[K, V]]:
        start, stop = _irange_bounds(self._keys, minimum, maximum, inclusive)
        for key in self._keys[start:stop]:
            yield key, self._values[key]
