import gc
import io
import threading
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pytest import MonkeyPatch, fixture, mark, raises

from omegaconf import OmegaConf, _control, grammar_parser
from omegaconf.errors import GrammarParseError


@fixture(autouse=True)
def restore_syntax_cache_policy() -> Any:
    old = OmegaConf.control.get_syntax_cache_max_bytes()
    OmegaConf.control.set_syntax_cache_max_bytes(4 * 1024 * 1024)
    grammar_parser._grammar_cache.parse_trees = None
    yield
    OmegaConf.control.set_syntax_cache_max_bytes(old)
    grammar_parser._grammar_cache.parse_trees = None


@mark.parametrize("value", [True, False, 1.5, "1024", None])
def test_invalid_budget_type(value: Any) -> None:
    with raises(TypeError, match="integer"):
        OmegaConf.control.set_syntax_cache_max_bytes(value)
    assert OmegaConf.control.get_syntax_cache_max_bytes() == 4 * 1024 * 1024


def test_negative_budget() -> None:
    with raises(ValueError, match="nonnegative"):
        OmegaConf.control.set_syntax_cache_max_bytes(-1)


def test_budget_updates_disable_and_reenable() -> None:
    parse = grammar_parser._parse_cached
    first = parse("${x}-first")
    second = parse("${x}-second")
    cache = grammar_parser._grammar_cache.parse_trees
    limit = cache.entries[("${x}-second", "configValue", "DEFAULT_MODE")][1]
    OmegaConf.control.set_syntax_cache_max_bytes(limit)
    assert parse("${x}-second") is second
    assert len(cache.entries) == 1
    assert cache.weight <= limit

    OmegaConf.control.set_syntax_cache_max_bytes(0)
    assert parse("${x}-second") is not second
    assert not cache.entries
    assert cache.weight == 0
    OmegaConf.control.set_syntax_cache_max_bytes(4 * 1024 * 1024)
    assert parse("${x}-first") is not first
    assert parse("${x}-first") is parse("${x}-first")


def test_disabled_before_first_parse() -> None:
    OmegaConf.control.set_syntax_cache_max_bytes(0)
    grammar_parser._parse_cached("${x}")
    assert grammar_parser._grammar_cache.parse_trees is None


def test_admission_uses_memory_not_characters() -> None:
    parse = grammar_parser._parse_cached
    long_literal = "${x}" + "a" * 9996
    first = parse(long_literal)
    assert parse(long_literal) is first
    dense = "${x}" * 1023 + "000"
    parse(dense)
    cache = grammar_parser._grammar_cache.parse_trees
    assert len(cache.entries) == 1
    assert parse(long_literal) is first


def test_lru_hits_and_entry_ceiling() -> None:
    parse = grammar_parser._parse_cached
    first = parse("${x}-000")
    for i in range(1, 256):
        parse(f"${{x}}-{i:03}")
    assert parse("${x}-000") is first
    parse("${x}-256")
    cache = grammar_parser._grammar_cache.parse_trees
    assert len(cache.entries) == 256
    assert ("${x}-000", "configValue", "DEFAULT_MODE") in cache.entries
    assert ("${x}-001", "configValue", "DEFAULT_MODE") not in cache.entries


def test_saturation_respects_memory_budget() -> None:
    for i in range(400):
        grammar_parser._parse_cached("${x}" * 15 + f"{i:03}")
        cache = grammar_parser._grammar_cache.parse_trees
        assert cache.weight <= OmegaConf.control.get_syntax_cache_max_bytes()
        assert sum(weight for _, weight in cache.entries.values()) == cache.weight
    assert len(cache.entries) < 256


def test_malformed_syntax_is_not_cached() -> None:
    for _ in range(2):
        with raises(GrammarParseError):
            grammar_parser._parse_cached("${")
    assert not grammar_parser._grammar_cache.parse_trees.entries


def test_unknown_tree_allocation_is_not_cached() -> None:
    tree = grammar_parser.parse("${x}")
    tree.exception = object()
    assert grammar_parser._tree_cache_weight(tree, 256 * 1024) is None


def test_small_budget_cannot_admit_tree() -> None:
    OmegaConf.control.set_syntax_cache_max_bytes(1)
    grammar_parser._parse_cached("${x}")
    assert not grammar_parser._grammar_cache.parse_trees.entries


def test_unavailable_object_sizes_disable_admission(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        grammar_parser.sys, "getsizeof", lambda obj, default=None: default
    )
    assert grammar_parser._parse_cached("${x}").getText() == "${x}<EOF>"
    assert not grammar_parser._grammar_cache.parse_trees.entries


def test_dense_yaml_does_not_accumulate_cached_trees() -> None:
    # A small, alias-free reproduction of the memory amplification. Avoid the
    # original half-gigabyte payload, including when this test fails.
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    try:
        before = tracemalloc.get_traced_memory()[0]
        payload = "x: 1\n" + "".join(
            f'v{i}: "' + "${x}" * 1023 + f'{i:03}"\n' for i in range(8)
        )
        cfg = OmegaConf.load(io.StringIO(payload))
        resolved = OmegaConf.to_container(cfg, resolve=True)
        assert isinstance(resolved, dict)
        assert resolved["v7"] == "1" * 1023 + "007"
        del cfg, resolved
        gc.collect()
        retained = tracemalloc.get_traced_memory()[0] - before
        assert not grammar_parser._grammar_cache.parse_trees.entries
        assert retained < 4 * 1024 * 1024
    finally:
        if not was_tracing:
            tracemalloc.stop()


def test_existing_threads_apply_updates_lazily() -> None:
    barrier = threading.Barrier(3)

    def work() -> int:
        first = grammar_parser._parse_cached("${x}")
        cache = grammar_parser._grammar_cache.parse_trees
        barrier.wait(timeout=10)
        barrier.wait(timeout=10)
        # Idle caches have not been touched by the global setter.
        assert cache.entries
        assert grammar_parser._parse_cached("${x}") is not first
        assert cache.max_bytes == 0
        assert not cache.entries
        return id(cache)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(work) for _ in range(2)]
        barrier.wait(timeout=10)
        OmegaConf.control.set_syntax_cache_max_bytes(0)
        barrier.wait(timeout=10)
        assert len({future.result(timeout=10) for future in futures}) == 2


def test_concurrent_setters_publish_complete_policies() -> None:
    barrier = threading.Barrier(4)
    generation = _control._syntax_cache_policy[1]

    def work(budget: int) -> None:
        barrier.wait(timeout=10)
        for _ in range(50):
            OmegaConf.control.set_syntax_cache_max_bytes(budget)
            observed, version = _control._syntax_cache_policy
            assert observed in (0, 1024, 4096, 16384)
            assert version > generation
            grammar_parser._parse_cached("${x}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(work, (0, 1024, 4096, 16384)))
    assert _control._syntax_cache_policy[1] == generation + 200


def test_concurrent_eviction_and_reentrant_resolvers(restore_resolvers: Any) -> None:
    barrier = threading.Barrier(4)

    def recursive(value: int) -> Any:
        return OmegaConf.create({"source": value, "ref": "${source}"}).ref

    OmegaConf.register_resolver("cache.recursive", recursive)

    def work(seed: int) -> tuple[int, int]:
        cfg = OmegaConf.create({"x": seed, "v": "${cache.recursive:${x}}"})
        barrier.wait(timeout=10)
        for i in range(350):
            cfg.x = seed + i
            cfg.v = "${x}" * 15 + f"-{i}"
            assert cfg.v == str(seed + i) * 15 + f"-{i}"
            cfg.v = "${cache.recursive:${x}}"
            assert cfg.v == seed + i
            cache = grammar_parser._grammar_cache.parse_trees
            assert cache.weight <= cache.max_bytes
            assert sum(weight for _, weight in cache.entries.values()) == cache.weight
        barrier.wait(timeout=10)
        return id(cache), len(cache.entries)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(work, range(4)))
    assert len({identity for identity, _ in results}) == 4
    assert all(count < 256 for _, count in results)
