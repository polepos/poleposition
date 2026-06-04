import pytest


def test_polepos_data_exports_runtime_structures() -> None:
    from polepos.data import (
        Graph,
        IndexedPriorityQueue,
        LRUCache,
        OrderedSet,
        SortedDict,
        SortedList,
        SortedSet,
        Trie,
        TTLCache,
        UnionFind,
    )

    assert Graph is not None
    assert IndexedPriorityQueue is not None
    assert LRUCache is not None
    assert OrderedSet is not None
    assert SortedDict is not None
    assert SortedList is not None
    assert SortedSet is not None
    assert TTLCache is not None
    assert Trie is not None
    assert UnionFind is not None


def test_lru_cache_evicts_least_recently_used_key() -> None:
    from polepos.data import LRUCache

    cache = LRUCache[str, int](max_size=2)
    cache["a"] = 1
    cache["b"] = 2
    assert cache["a"] == 1

    cache["c"] = 3

    assert "a" in cache
    assert "b" not in cache
    assert list(cache) == ["a", "c"]


def test_ttl_cache_expires_values_with_injected_timer() -> None:
    from polepos.data import TTLCache

    now = 100.0

    def timer() -> float:
        return now

    cache = TTLCache[str, int](ttl=5.0, timer=timer)
    cache["token"] = 1
    assert cache["token"] == 1

    now = 106.0

    assert "token" not in cache
    assert len(cache) == 0


def test_indexed_priority_queue_updates_and_removes_by_key() -> None:
    from polepos.data import IndexedPriorityQueue

    queue = IndexedPriorityQueue[str, int, str]()
    queue.push("slow", 10, "slow job")
    queue.push("fast", 1, "fast job")
    queue.update("slow", 0)
    queue.remove("fast")

    item = queue.pop()

    assert item.key == "slow"
    assert item.priority == 0
    assert item.value == "slow job"
    assert len(queue) == 0


def test_sorted_containers_keep_ordered_iteration() -> None:
    from polepos.data import SortedDict, SortedList, SortedSet

    values = SortedList([3, 1, 2, 2])
    values.add(0)
    assert values.to_list() == [0, 1, 2, 2, 3]
    assert list(values.irange(1, 2)) == [1, 2, 2]

    unique_values = SortedSet([3, 1, 2, 2])
    unique_values.add(0)
    assert list(unique_values) == [0, 1, 2, 3]

    mapping = SortedDict([("b", 2), ("a", 1)])
    mapping["c"] = 3
    assert list(mapping.items()) == [("a", 1), ("b", 2), ("c", 3)]
    assert list(mapping.irange("b", "c")) == [("b", 2), ("c", 3)]


def test_ordered_set_preserves_insertion_order() -> None:
    from polepos.data import OrderedSet

    values = OrderedSet(["b", "a", "b", "c"])
    values.add("a")

    assert list(values) == ["b", "a", "c"]
    assert values.pop(last=False) == "b"
    assert list(values) == ["a", "c"]


def test_trie_supports_prefix_lookup_and_delete() -> None:
    from polepos.data import Trie

    trie = Trie[int]()
    trie.insert("car", 1)
    trie.insert("cart", 2)
    trie.insert("cat", 3)

    assert "car" in trie
    assert trie.get("cart") == 2
    assert trie.keys("ca") == ["car", "cart", "cat"]
    assert trie.longest_prefix_of("cartwheel") == "cart"

    trie.delete("cart")

    assert "cart" not in trie
    assert trie.keys("car") == ["car"]


def test_union_find_groups_components() -> None:
    from polepos.data import UnionFind

    union_find = UnionFind(["a", "b", "c"])
    union_find.union("a", "b")

    assert union_find.connected("a", "b")
    assert not union_find.connected("a", "c")
    assert union_find.component_size("a") == 2
    assert {frozenset(component) for component in union_find.components()} == {
        frozenset({"a", "b"}),
        frozenset({"c"}),
    }


def test_graph_supports_paths_and_topological_sort() -> None:
    from polepos.data import Graph

    graph = Graph([("a", "b"), ("b", "c")])
    assert graph.shortest_path("a", "c") == ["a", "b", "c"]
    assert set(graph.bfs("a")) == {"a", "b", "c"}

    dag = Graph([("extract", "load"), ("load", "serve")], directed=True)
    ordered = dag.topological_sort()

    assert ordered.index("extract") < ordered.index("load")
    assert ordered.index("load") < ordered.index("serve")

    cyclic = Graph([("a", "b"), ("b", "a")], directed=True)
    with pytest.raises(ValueError, match="cycle"):
        cyclic.topological_sort()


def test_graph_remove_edge() -> None:
    from polepos.data import Graph

    undirected = Graph([("a", "b"), ("b", "c")])
    undirected.remove_edge("a", "b")
    assert "b" not in undirected.neighbors("a")
    assert "a" not in undirected.neighbors("b")
    assert "c" in undirected.neighbors("b")

    directed = Graph([("x", "y"), ("y", "z")], directed=True)
    directed.remove_edge("x", "y")
    assert "y" not in directed.neighbors("x")
    assert "x" not in directed.neighbors("y")

    with pytest.raises(KeyError):
        undirected.remove_edge("a", "b")


def test_sorted_containers_remove_elements() -> None:
    from polepos.data import SortedDict, SortedSet

    unique_values = SortedSet([1, 2, 3, 4])
    unique_values.discard(2)
    assert list(unique_values) == [1, 3, 4]
    assert len(unique_values) == 3
    unique_values.discard(99)
    assert list(unique_values) == [1, 3, 4]

    mapping = SortedDict([("a", 1), ("b", 2), ("c", 3)])
    del mapping["b"]
    assert list(mapping.items()) == [("a", 1), ("c", 3)]
    assert len(mapping) == 2
    with pytest.raises(KeyError):
        del mapping["b"]


def test_ttl_cache_evicts_when_max_size_exceeded() -> None:
    from polepos.data import TTLCache

    cache = TTLCache[str, int](ttl=60.0, max_size=2)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3

    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache
    assert len(cache) == 2


def test_graph_traversals_follow_edge_insertion_order() -> None:
    from polepos.data import Graph

    # Neighbour order must mirror edge insertion, not the hash order of a set,
    # so traversals are reproducible regardless of PYTHONHASHSEED.
    graph = Graph(
        [("root", "b"), ("root", "a"), ("root", "c")],
        directed=True,
    )

    assert list(graph.bfs("root")) == ["root", "b", "a", "c"]
    assert list(graph.dfs("root")) == ["root", "b", "a", "c"]

    dag = Graph([("root", "b"), ("root", "a")], directed=True)
    assert dag.topological_sort() == ["root", "b", "a"]


def test_graph_traversals_reject_unknown_start_node() -> None:
    from polepos.data import Graph

    graph = Graph([("a", "b")])

    with pytest.raises(ValueError, match="not in graph"):
        list(graph.bfs("missing"))
    with pytest.raises(ValueError, match="not in graph"):
        list(graph.dfs("missing"))
    with pytest.raises(ValueError, match="not in graph"):
        graph.shortest_path("missing", "a")
    with pytest.raises(ValueError, match="not in graph"):
        graph.shortest_path("a", "missing")


def test_union_find_handles_deep_chains_without_recursion_error() -> None:
    from polepos.data import UnionFind

    union_find = UnionFind(range(3000))
    # Force a degenerate linear parent chain deeper than the recursion limit;
    # an iterative find must resolve and compress it without RecursionError.
    for value in range(1, 3000):
        union_find._parent[value] = value - 1

    assert union_find.find(2999) == 0
    assert union_find._parent[2999] == 0


def test_sorted_irange_is_lazy_and_consistent_across_containers() -> None:
    import types

    from polepos.data import SortedDict, SortedList, SortedSet

    sorted_list = SortedList([5, 1, 3, 2, 4])
    result = sorted_list.irange(2, 4)
    assert isinstance(result, types.GeneratorType)
    assert list(result) == [2, 3, 4]

    sorted_set = SortedSet([5, 1, 3, 2, 4])
    assert list(sorted_set.irange(2, 4)) == [2, 3, 4]

    sorted_dict = SortedDict([(key, key * 10) for key in [5, 1, 3, 2, 4]])
    assert list(sorted_dict.irange(2, 4)) == [(2, 20), (3, 30), (4, 40)]

    assert list(sorted_list.irange(2, 4, inclusive=(False, False))) == [3]
    assert list(sorted_set.irange(2, 4, inclusive=(False, False))) == [3]
    assert list(sorted_dict.irange(2, 4, inclusive=(False, False))) == [(3, 30)]
