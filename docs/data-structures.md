# Data Structures

PolePosition exposes a small runtime data-structure namespace:

```python
from polepos.data import LRUCache, SortedDict, Trie
```

This API is for application code that wants a few practical structures Python
does not provide as first-class built-in containers. It is intentionally small,
pure Python, and dependency-free.

## Import Boundary

`polepos.data` is a runtime package. It is separate from the internal
`pole_position` CLI implementation package.

Use it from generated applications like this:

```python
from polepos.data import IndexedPriorityQueue
```

Do not import from `pole_position.cli...` in generated app code. That package
is for the generator and command implementation.

## Available Structures

Current exports, with the operations you reach for most and their typical
cost. `n` is the number of stored items; `k` is a key's length.

| Structure | Purpose | Key operations | Typical cost |
| --- | --- | --- | --- |
| `LRUCache` | Bounded least-recently-used cache | `cache[key]`, `set`, `peek` | O(1) get/set |
| `TTLCache` | Lazy-expiring in-memory cache | `cache[key]`, `set`, `expire` | O(1) get/set, amortized expiry |
| `OrderedSet` | Insertion-ordered set | `add`, `discard`, `in`, iterate | O(1) add/lookup |
| `SortedList` | Sorted list with bisect helpers | `add`, `bisect_left`, `irange`, index | O(log n) search, O(n) insert |
| `SortedSet` | Unique values kept in sorted order | `add`, `discard`, `irange` | O(log n) search, O(n) insert |
| `SortedDict` | Mapping that iterates keys in sorted order | `d[key]`, `peekitem`, `irange` | O(log n) search, O(n) insert |
| `IndexedPriorityQueue` | Min-priority queue with update/remove by key | `push`, `pop`, `update`, `remove` | O(log n) push/pop |
| `Trie` | Prefix tree for string keys | `insert`, `get`, `keys(prefix)`, `longest_prefix_of` | O(k) lookup |
| `UnionFind` | Disjoint-set union | `union`, `find`, `connected`, `components` | near O(1) amortized |
| `Graph` | Adjacency-set graph | `bfs`, `dfs`, `shortest_path`, `topological_sort` | O(V + E) traversal |

All operations are iterative (no recursion depth limits), and traversals are
deterministic regardless of `PYTHONHASHSEED`.

## Examples

### LRU Cache

```python
from polepos.data import LRUCache

cache = LRUCache[str, dict](max_size=500)
cache["user:1"] = {"id": 1}
user = cache["user:1"]
```

### Indexed Priority Queue

```python
from polepos.data import IndexedPriorityQueue

jobs = IndexedPriorityQueue[str, int, dict]()
jobs.push("sync-users", priority=10, value={"kind": "sync"})
jobs.update("sync-users", priority=1)

next_job = jobs.pop()
```

### Trie

```python
from polepos.data import Trie

names = Trie[int]()
names.insert("customer", 1)
names.insert("customs", 2)

matches = names.keys("cust")
```

### Sorted Dict

```python
from polepos.data import SortedDict

scores = SortedDict[str, int]()
scores["alice"] = 10
scores["bob"] = 8

for name, score in scores.items():
    ...
```

## Runtime Caveat

These structures are in-memory and process-local. In a FastAPI app with
multiple Uvicorn workers, each worker has its own copy. Use them for local
indices, request-time algorithms, bounded caches, and test doubles.

For shared or persistent state, prefer infrastructure-backed structures:

- Redis sets, sorted sets, streams, and TTL keys
- PostgreSQL tables, indexes, materialized views, and full-text search
- Kafka or RabbitMQ for cross-process event streams

PolePosition may add higher-level module templates around these structures, but
the import surface remains explicit application code:

```python
from polepos.data import Graph
```
