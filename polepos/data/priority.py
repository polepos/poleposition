from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Generic, TypeVar

K = TypeVar("K")
P = TypeVar("P")
V = TypeVar("V")

_MISSING = object()


@dataclass(frozen=True)
class PriorityItem(Generic[K, P, V]):
    key: K
    priority: P
    value: V


@dataclass
class _Record(Generic[P, V]):
    priority: P
    sequence: int
    value: V


class IndexedPriorityQueue(Generic[K, P, V]):
    """A min-priority queue with update and remove by key."""

    def __init__(self) -> None:
        self._heap: list[tuple[P, int, K]] = []
        self._records: dict[K, _Record[P, V]] = {}
        self._sequence = 0

    def __contains__(self, key: object) -> bool:
        return key in self._records

    def __len__(self) -> int:
        return len(self._records)

    def push(self, key: K, priority: P, value: V | object = _MISSING) -> None:
        stored_value = key if value is _MISSING else value
        self._sequence += 1
        record = _Record(
            priority=priority,
            sequence=self._sequence,
            value=stored_value,  # type: ignore[arg-type]
        )
        self._records[key] = record
        heapq.heappush(self._heap, (priority, record.sequence, key))

    def update(self, key: K, priority: P, value: V | object = _MISSING) -> None:
        if value is _MISSING and key in self._records:
            value = self._records[key].value
        self.push(key, priority, value)

    def remove(self, key: K) -> None:
        del self._records[key]

    def discard(self, key: K) -> bool:
        if key not in self._records:
            return False
        self.remove(key)
        return True

    def peek(self) -> PriorityItem[K, P, V]:
        priority, sequence, key = self._peek_heap_entry()
        record = self._records[key]
        return PriorityItem(key=key, priority=priority, value=record.value)

    def pop(self) -> PriorityItem[K, P, V]:
        priority, sequence, key = self._peek_heap_entry()
        heapq.heappop(self._heap)
        record = self._records.pop(key)
        return PriorityItem(key=key, priority=priority, value=record.value)

    def _peek_heap_entry(self) -> tuple[P, int, K]:
        while self._heap:
            priority, sequence, key = self._heap[0]
            record = self._records.get(key)
            if (
                record is not None
                and record.priority == priority
                and record.sequence == sequence
            ):
                return priority, sequence, key
            heapq.heappop(self._heap)
        raise IndexError("priority queue is empty")
