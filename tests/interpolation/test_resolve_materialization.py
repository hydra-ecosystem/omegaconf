from dataclasses import dataclass, field
from typing import Any

from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf, TupleConfig
from omegaconf.errors import InterpolationResolutionError


@dataclass
class TypedDictResolverSchema:
    consumer: Any = None
    made: dict[str, int] = field(default_factory=dict)


@dataclass
class TypedListResolverSchema:
    consumer: Any = None
    made: list[int] = field(default_factory=list)


@dataclass
class TypedTupleResolverSchema:
    consumer: Any = None
    made: tuple[int, ...] = ()


@dataclass
class TypedAliasResolverSchema:
    consumer: Any = None
    alias: Any = None
    made: dict[str, int] = field(default_factory=dict)


@mark.parametrize(
    "value, path, container_type",
    [
        param({"n": 3}, "made.n", DictConfig, id="dict"),
        param([3], "made.0", ListConfig, id="list"),
        param((3,), "made.0", TupleConfig, id="tuple"),
        param(DictConfig({"n": 3}), "made.n", DictConfig, id="dict-config"),
        param(ListConfig([3]), "made.0", ListConfig, id="list-config"),
        param(TupleConfig((3,)), "made.0", TupleConfig, id="tuple-config"),
    ],
)
@mark.parametrize("consumer_first", [True, False])
def test_resolve_materializes_producer_before_traversal(
    restore_resolvers: Any,
    value: Any,
    path: str,
    container_type: type,
    consumer_first: bool,
) -> None:
    calls = 0

    def make() -> Any:
        nonlocal calls
        calls += 1
        return value

    OmegaConf.register_resolver("make", make)
    fields = [("consumer", f"${{{path}}}"), ("made", "${make:}")]
    cfg = OmegaConf.create(dict(fields if consumer_first else reversed(fields)))

    OmegaConf.resolve(cfg)

    assert cfg.consumer == 3
    assert isinstance(cfg.made, container_type)
    assert not OmegaConf.is_interpolation(cfg, "made")
    assert calls == 1


def test_resolve_new_container_children_in_one_pass(restore_resolvers: Any) -> None:
    original = {"child": "${..value}"}
    OmegaConf.register_resolver("make", lambda: original)
    cfg = OmegaConf.create(
        {"consumer": "${made.child}", "made": "${make:}", "value": 10}
    )

    OmegaConf.resolve(cfg)

    assert cfg.consumer == 10
    assert cfg.made.child == 10
    assert not OmegaConf.is_interpolation(cfg.made, "child")
    assert original == {"child": "${..value}"}


def test_resolve_copies_resolver_returned_config(restore_resolvers: Any) -> None:
    original = DictConfig({"child": "${..value}"})
    OmegaConf.register_resolver("make", lambda: original)
    cfg = OmegaConf.create(
        {"consumer": "${made.child}", "made": "${make:}", "value": 10}
    )

    OmegaConf.resolve(cfg)

    assert cfg.consumer == cfg.made.child == 10
    assert original._get_parent() is None
    assert OmegaConf.is_interpolation(original, "child")


def test_resolve_materializes_owned_resolver_result_once(
    restore_resolvers: Any,
) -> None:
    calls = 0
    cfg = OmegaConf.create(
        {"consumer": "${made.n}", "made": "${make:}", "source": {"n": 3}}
    )

    def make() -> DictConfig:
        nonlocal calls
        calls += 1
        return cfg.source

    OmegaConf.register_resolver("make", make)

    OmegaConf.resolve(cfg)

    assert calls == 1
    assert cfg.consumer == cfg.made.n == cfg.source.n == 3
    assert not OmegaConf.is_interpolation(cfg, "made")


def test_resolve_materializes_through_node_alias(restore_resolvers: Any) -> None:
    calls = 0

    def make() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"n": calls}

    OmegaConf.register_resolver("make", make)
    cfg = OmegaConf.create(
        {"consumer": "${alias.n}", "alias": "${made}", "made": "${make:}"}
    )

    OmegaConf.resolve(cfg)

    assert calls == 1
    assert cfg.consumer == cfg.alias.n == cfg.made.n == 1
    assert isinstance(cfg.made, DictConfig)


def test_resolve_direct_alias_materializes_producer_once(
    restore_resolvers: Any,
) -> None:
    calls = 0

    def make() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"n": calls}

    OmegaConf.register_resolver("make", make)
    cfg = OmegaConf.create({"alias": "${made}", "made": "${make:}"})

    OmegaConf.resolve(cfg)

    assert calls == 1
    assert cfg.alias.n == cfg.made.n == 1
    assert isinstance(cfg.made, DictConfig)
    assert not OmegaConf.is_interpolation(cfg, "alias")
    assert not OmegaConf.is_interpolation(cfg, "made")


@mark.parametrize(
    "schema, value, path, container_type",
    [
        (TypedDictResolverSchema, {"n": 1}, "made.n", DictConfig),
        (TypedListResolverSchema, [1], "made.0", ListConfig),
        (TypedTupleResolverSchema, (1,), "made.0", TupleConfig),
    ],
)
def test_resolve_typed_resolver_container_materializes_producer_once(
    restore_resolvers: Any,
    schema: type,
    value: Any,
    path: str,
    container_type: type,
) -> None:
    calls = 0

    def make() -> Any:
        nonlocal calls
        calls += 1
        return value

    OmegaConf.register_resolver("make", make)
    cfg = OmegaConf.structured(schema)
    cfg["consumer"] = f"${{{path}}}"
    cfg["made"] = "${make:}"

    OmegaConf.resolve(cfg)

    assert calls == 1
    assert cfg.consumer == 1
    assert isinstance(cfg.made, container_type)
    assert not OmegaConf.is_interpolation(cfg, "made")


def test_resolve_typed_resolver_container_through_alias_once(
    restore_resolvers: Any,
) -> None:
    calls = 0

    def make() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"n": 3}

    OmegaConf.register_resolver("make", make)
    cfg = OmegaConf.structured(TypedAliasResolverSchema)
    cfg["consumer"] = "${alias.n}"
    cfg["alias"] = "${made}"
    cfg["made"] = "${make:}"

    OmegaConf.resolve(cfg)

    assert calls == 1
    assert cfg.consumer == cfg.alias.n == cfg.made.n == 3
    assert not OmegaConf.is_interpolation(cfg, "made")


def test_resolve_tuple_element_from_container_interpolation() -> None:
    cfg = OmegaConf.create({"source": [1], "items": ("${source}",)})

    OmegaConf.resolve(cfg)

    assert isinstance(cfg["items"], TupleConfig)
    assert isinstance(cfg["items"][0], ListConfig)
    assert cfg["items"][0] == [1]


def test_resolve_keeps_cached_raw_result(restore_resolvers: Any) -> None:
    original = {"n": 3}
    OmegaConf.register_resolver("make", lambda: original, use_cache=True)
    cfg = OmegaConf.create({"consumer": "${made.n}", "made": "${make:}"})

    OmegaConf.resolve(cfg)

    assert cfg.consumer == 3
    assert original == {"n": 3}
    assert next(iter(OmegaConf.get_cache(cfg)["make"].values())) is original
    other = OmegaConf.create({"made": "${make:}"})
    OmegaConf.copy_cache(cfg, other)
    assert other.made == original


def test_lazy_resolver_container_stays_native(restore_resolvers: Any) -> None:
    original = [3]
    OmegaConf.register_resolver("make", lambda: original)
    cfg = OmegaConf.create({"consumer": "${made.0}", "made": "${make:}"})

    assert cfg.made is original
    with raises(InterpolationResolutionError):
        _ = cfg.consumer
    assert OmegaConf.is_interpolation(cfg, "made")


def test_resolver_callback_keeps_lazy_access(restore_resolvers: Any) -> None:
    original = [3]
    observed: list[Any] = []
    OmegaConf.register_resolver("make", lambda: original)

    def inspect(_root_: DictConfig) -> int:
        observed.append(_root_.made)
        return 10

    OmegaConf.register_resolver("inspect", inspect)
    cfg = OmegaConf.create({"consumer": "${inspect:}", "made": "${make:}"})

    OmegaConf.resolve(cfg)

    assert observed == [original]
    assert observed[0] is original


def test_resolve_recursive_materialized_container_fails(
    restore_resolvers: Any,
) -> None:
    OmegaConf.register_resolver("make", lambda: {"child": "${made.child}"})
    cfg = OmegaConf.create({"consumer": "${made.child}", "made": "${make:}"})

    with raises(InterpolationResolutionError):
        OmegaConf.resolve(cfg)
