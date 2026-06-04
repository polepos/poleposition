from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable, Iterator, MutableMapping
from dataclasses import dataclass
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(MutableMapping[K, V], Generic[K, V]):
    """A small least-recently-used cache.

    The cache is in-memory and process-local. Reads through ``__getitem__`` and
    ``get`` mark keys as recently used.
    """

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self.max_size = max_size
        self._items: OrderedDict[K, V] = OrderedDict()

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __getitem__(self, key: K) -> V:
        value = self._items[key]
        self._items.move_to_end(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        if key in self._items:
            self._items.move_to_end(key)
        self._items[key] = value
        while len(self._items) > self.max_size:
            self._items.popitem(last=False)

    def __delitem__(self, key: K) -> None:
        del self._items[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def set(self, key: K, value: V) -> None:
        self[key] = value

    def peek(self, key: K) -> V:
        return self._items[key]


@dataclass
class _TTLItem(Generic[V]):
    value: V
    expires_at: float


class TTLCache(MutableMapping[K, V], Generic[K, V]):
    """A lazy-expiring in-memory cache."""

    def __init__(
        self,
        ttl: float,
        *,
        max_size: int | None = None,
        timer: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl <= 0:
            raise ValueError("ttl must be greater than 0")
        if max_size is not None and max_size < 1:
            raise ValueError("max_size must be at least 1")
        self.ttl = ttl
        self.max_size = max_size
        self._timer = timer
        self._items: OrderedDict[K, _TTLItem[V]] = OrderedDict()

    def __contains__(self, key: object) -> bool:
        self._expire()
        return key in self._items

    def __getitem__(self, key: K) -> V:
        self._expire()
        item = self._items[key]
        self._items.move_to_end(key)
        return item.value

    def __setitem__(self, key: K, value: V) -> None:
        self._expire()
        if key in self._items:
            self._items.move_to_end(key)
        self._items[key] = _TTLItem(
            value=value, expires_at=self._timer() + self.ttl
        )
        self._evict_to_limit()

    def __delitem__(self, key: K) -> None:
        del self._items[key]

    def __iter__(self) -> Iterator[K]:
        self._expire()
        return iter(self._items)

    def __len__(self) -> int:
        self._expire()
        return len(self._items)

    def set(self, key: K, value: V) -> None:
        self[key] = value

    def expire(self) -> None:
        self._expire()

    def _expire(self) -> None:
        now = self._timer()
        expired_keys = [
            key for key, item in self._items.items() if item.expires_at <= now
        ]
        for key in expired_keys:
            self._items.pop(key, None)

    def _evict_to_limit(self) -> None:
        if self.max_size is None:
            return
        while len(self._items) > self.max_size:
            self._items.popitem(last=False)
