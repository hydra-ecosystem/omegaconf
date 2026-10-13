import copy
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any

import attr
import pytest

from omegaconf import (
    MISSING,
    BooleanNode,
    DictConfig,
    ListConfig,
    OmegaConf,
    TupleConfig,
    experimental,
)
from omegaconf.base import Node
from omegaconf.errors import (
    ConfigKeyError,
    KeyValidationError,
    ValidationError,
)
from omegaconf.experimental import _validate

FACTORIES: list[str] = []


def factory() -> int:
    FACTORIES.append("called")
    return 10


@dataclass
class Child:
    count: int = MISSING
    generated: int = field(default_factory=factory)


@attr.define
class AttrChild:
    count: int = MISSING
    generated: int = attr.field(factory=factory)


class Color(Enum):
    RED = 1


class Number(IntEnum):
    TWO = 2


class Text(str, Enum):
    TWO = "two"


@dataclass
class Schema:
    count: int = 0
    child: Child | None = None
    children: list[Child] = field(default_factory=list)
    mapping: dict[str, Child] = field(default_factory=dict)
    pair: tuple[int, Any] = (0, None)
    numbers: list[int] | None = None
    keyed: dict[Color, int] = field(default_factory=dict)
    payload: Any = None
    union: Child | list[int] | tuple[int, ...] = field(default_factory=Child)


class ExplodingEquality:
    __hash__ = object.__hash__

    def __eq__(self, other: Any) -> bool:
        raise AssertionError("omitted default was inspected")

    def __ne__(self, other: Any) -> bool:
        raise AssertionError("omitted default was inspected")


@dataclass
class OmittedDefaultSchema:
    count: int = 0
    untouched: Any = ExplodingEquality()


@dataclass
class SourceHolder:
    items: list[dict[str, Any]] = field(default_factory=list)


@attr.define
class AttrSourceHolder:
    items: list[dict[str, Any]] = attr.field(factory=list)


def snapshot(node: Node) -> list[Any]:
    content = node.__dict__.get("_content", node.__dict__.get("_val"))
    children = (
        list(content.values())
        if isinstance(content, dict)
        else content
        if isinstance(content, list)
        else [content]
        if isinstance(content, Node)
        else []
    )
    result = [
        (
            id(node),
            id(node._get_parent()),
            copy.deepcopy(node._metadata),
            copy.deepcopy(node.__dict__["_flags_cache"]),
            content if not children else tuple(id(child) for child in children),
        )
    ]
    for child in children:
        result.extend(snapshot(child))
    return result


def recursive_container(kind: str) -> Any:
    if kind == "dict":
        value: dict[str, Any] = {}
        value["self"] = value
        return value
    if kind == "list":
        value_list: list[Any] = []
        value_list.append(value_list)
        return value_list
    value_list = []
    value_tuple = (value_list,)
    value_list.append(value_tuple)
    return value_tuple


@pytest.mark.parametrize("schema", [Child, AttrChild, Schema])
@pytest.mark.parametrize("content", [MISSING, None, "${absent}"])
@pytest.mark.parametrize("in_place", [False, True])
def test_absent_schema_never_reads_defaults(
    schema: Any, content: Any, in_place: bool
) -> None:
    cfg = DictConfig(content, ref_type=schema)
    before = snapshot(cfg)
    FACTORIES.clear()
    assert _validate(cfg, {"count": 2}, in_place=in_place) is None
    assert not FACTORIES
    if not in_place:
        assert snapshot(cfg) == before
    else:
        assert cfg.count == 2


def test_omitted_dataclass_default_is_not_inspected() -> None:
    cfg = DictConfig(MISSING, ref_type=OmittedDefaultSchema)
    _validate(cfg, {"count": 2})


def test_supplied_dataclass_instance_does_not_inspect_defaults() -> None:
    cfg = DictConfig(MISSING, ref_type=OmittedDefaultSchema)
    supplied = OmittedDefaultSchema(count=2, untouched=None)
    before = snapshot(cfg)
    assert _validate(cfg, supplied) is None
    assert supplied.count == 2
    assert supplied.untouched is None
    assert snapshot(cfg) == before


def test_normal_instance_default_comparison_is_preserved() -> None:
    with pytest.raises(AssertionError, match="omitted default was inspected"):
        OmegaConf.structured(OmittedDefaultSchema(untouched=None))


@pytest.mark.parametrize(
    "overrides",
    [
        {"child": {"count": 2}},
        {"children": [{"count": 2}]},
        {"mapping": {"a": {"count": 2}}},
        {"union": {"count": 2}},
        {"union": [2]},
        {"union": (2,)},
        {},
        {"child": {}},
    ],
)
@pytest.mark.parametrize("in_place", [False, True])
def test_partial_nested_schema_without_factories(
    overrides: Any, in_place: bool
) -> None:
    cfg = DictConfig(MISSING, ref_type=Schema)
    FACTORIES.clear()
    _validate(cfg, overrides, in_place=in_place)
    assert not FACTORIES


@pytest.mark.parametrize(
    "overrides",
    [
        {"count": "2"},
        {"count": True},
        {"count": 2.0},
        {"count": None},
        {"child": {"count": "2"}},
        {"children": [{"count": "2"}]},
        {"mapping": {"a": {"count": "2"}}},
        {"union": {"count": "2"}},
        {"union": ["2"]},
        {"union": ("2",)},
        {"pair": ("2", None)},
        {"numbers": (2,)},
        {"pair": [2, None]},
        {"keyed": {"RED": 2}},
        {"keyed": {1: 2}},
    ],
)
@pytest.mark.parametrize("in_place", [False, True])
def test_strict_rejection(overrides: Any, in_place: bool) -> None:
    cfg = DictConfig(MISSING, ref_type=Schema)
    FACTORIES.clear()
    with pytest.raises((ValidationError, KeyValidationError)):
        _validate(cfg, overrides, in_place=in_place)
    assert not FACTORIES


@pytest.mark.parametrize(
    "overrides",
    [
        {"count": MISSING},
        {"pair": (2, "x")},
        {"pair": (2, None)},
        {"numbers": None},
        {"numbers": TupleConfig(None)},
        {"keyed": {Color.RED: 2}},
        {"payload": {"anything": (True, [2])}},
    ],
)
def test_any_optional_and_missing(overrides: Any) -> None:
    _validate(DictConfig(MISSING, ref_type=Schema), overrides)


@pytest.mark.parametrize("field_name", ["payload", "pair"])
@pytest.mark.parametrize("allow_objects", [False, True])
def test_any_obeys_destination_object_policy(
    field_name: str, allow_objects: bool
) -> None:
    obj = object()
    overrides = {field_name: obj if field_name == "payload" else (2, obj)}
    cfg = DictConfig(MISSING, ref_type=Schema, flags={"allow_objects": allow_objects})
    if allow_objects:
        _validate(cfg, overrides)
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, overrides)


@pytest.mark.parametrize("root_allow,child_allow", [(True, False), (False, True)])
@pytest.mark.parametrize("source_config", [False, True])
@pytest.mark.parametrize("in_place", [False, True])
def test_any_uses_destination_object_policy(
    root_allow: bool, child_allow: bool, source_config: bool, in_place: bool
) -> None:
    obj = object()
    cfg = OmegaConf.structured(Schema, flags={"allow_objects": root_allow})
    cfg._get_node("payload")._set_flag("allow_objects", child_allow)
    overrides: Any = {"payload": obj}
    before = None
    if source_config:
        overrides = OmegaConf.create(
            overrides, flags={"allow_objects": True, "convert": True}
        )
        before = snapshot(overrides)

    if child_allow:
        _validate(cfg, overrides, in_place=in_place)
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, overrides, in_place=in_place)
    if source_config:
        assert snapshot(overrides) == before


@pytest.mark.parametrize("allow_objects", [False, True])
def test_raw_source_root_policy_cannot_relax_empty_destination(
    allow_objects: bool,
) -> None:
    cfg = DictConfig({}, flags={"allow_objects": allow_objects})
    if allow_objects:
        _validate(cfg, {"payload": object()})
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, {"payload": object()})


def test_raw_source_policy_is_inherited_by_new_nested_keys() -> None:
    cfg = DictConfig({"branch": {}}, flags={"allow_objects": False})
    with pytest.raises(ValidationError):
        _validate(cfg, {"branch": {"payload": object()}})


@pytest.mark.parametrize("key_type,key", [(int, True), (float, 2), (bool, 1)])
@pytest.mark.parametrize("in_place", [False, True])
def test_no_key_kind_conversion(key_type: Any, key: Any, in_place: bool) -> None:
    cfg = OmegaConf.typed_dict({}, key_type=key_type, element_type=int)
    with pytest.raises(KeyValidationError):
        _validate(cfg, {key: 2}, in_place=in_place)


def test_source_flags_cannot_weaken_validation() -> None:
    cfg = DictConfig(MISSING, ref_type=Schema)
    overrides = OmegaConf.create(
        {"children": [{"count": "2"}]},
        flags={"convert": True, "struct": False, "readonly": True},
    )
    before = snapshot(overrides)
    with pytest.raises(ValidationError):
        _validate(cfg, overrides)
    assert snapshot(overrides) == before


def test_unknown_structured_field() -> None:
    with pytest.raises(ConfigKeyError):
        _validate(DictConfig(MISSING, ref_type=Child), {"extra": 2})


def test_omitted_interpolation_is_not_evaluated() -> None:
    cfg = OmegaConf.structured(Child)
    cfg.generated = "${absent}"
    _validate(cfg, {"count": 2})


@pytest.mark.parametrize("schema,value", [(list[int], [2]), (tuple[int, ...], (2,))])
def test_root_sequences(schema: Any, value: Any) -> None:
    cfg = (
        ListConfig(MISSING, element_type=int, ref_type=schema)
        if isinstance(value, list)
        else TupleConfig(MISSING, ref_type=schema)
    )
    _validate(cfg, value)
    with pytest.raises(ValidationError):
        _validate(cfg, tuple(value) if isinstance(value, list) else list(value))


def test_normal_operations_still_materialize_defaults_and_convert() -> None:
    FACTORIES.clear()
    cfg = OmegaConf.structured(Child)
    assert len(FACTORIES) == 1
    assert OmegaConf.merge(cfg, {"count": "2"}).count == 2


def test_overwritten_interpolation_does_not_run_resolver(
    restore_resolvers: Any,
) -> None:
    calls: list[int] = []
    OmegaConf.register_resolver(
        "unused_validation", lambda: calls.append(1), annotation_validation="off"
    )
    cfg = OmegaConf.structured(Schema)
    cfg.child = "${unused_validation:}"
    before = snapshot(cfg)
    _validate(cfg, {"child": {"count": 2}})
    assert not calls
    assert snapshot(cfg) == before


@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
def test_recursive_direct_container_is_rejected(kind: str) -> None:
    with pytest.raises(ValidationError, match="recursive input container"):
        _validate(DictConfig({}), recursive_container(kind))


def test_shared_acyclic_container_is_accepted() -> None:
    shared = {"count": 2}
    _validate(
        DictConfig({}),
        {"left": shared, "right": shared},
    )


def test_normal_resolution_rejects_resolver_objects(
    restore_resolvers: Any,
) -> None:
    OmegaConf.register_resolver(
        "public_object_container_validation",
        lambda: {"x": object()},
        replace=True,
        annotation_validation="off",
    )
    cfg = OmegaConf.create({"payload": "${public_object_container_validation:}"})
    with pytest.raises(ValidationError):
        OmegaConf.resolve(cfg)


@pytest.mark.parametrize("value", [None, MISSING])
@pytest.mark.parametrize("kind", ["list", "tuple", "dict"])
def test_root_special_values(kind: str, value: Any) -> None:
    cfg = {
        "list": ListConfig(None, element_type=int),
        "tuple": TupleConfig(None, ref_type=tuple[int, ...]),
        "dict": DictConfig(None, ref_type=Child),
    }[kind]
    before = snapshot(cfg)
    _validate(cfg, value)
    assert snapshot(cfg) == before


def test_supplied_nodes_have_isolated_parents() -> None:
    source = OmegaConf.create({"other": 1, "patch": {"count": "${answer}"}})
    root = OmegaConf.create({"answer": 2, "schema": Child})
    cfg = root.schema
    patch = source.patch
    before = snapshot(root), snapshot(source)
    _validate(cfg, patch)
    assert (snapshot(root), snapshot(source)) == before


def test_failure_does_not_leak_private_context() -> None:
    with pytest.raises(ValidationError):
        _validate(DictConfig(MISSING, ref_type=Child), {"count": "2"})
    FACTORIES.clear()
    cfg = OmegaConf.structured(Child)
    assert FACTORIES == ["called"]
    assert OmegaConf.merge(cfg, {"count": "2"}).count == 2


@pytest.mark.parametrize("where", ["count", "numbers", "keyed", "pair", "union"])
def test_typed_scalar_nodes_cannot_bypass_strictness(where: str) -> None:
    boolean = BooleanNode(True)
    patch = {
        "count": boolean,
        "numbers": [boolean],
        "keyed": {Color.RED: boolean},
        "pair": (boolean, None),
        "union": [boolean],
    }
    cfg = DictConfig(MISSING, ref_type=Schema)
    with pytest.raises(ValidationError):
        _validate(cfg, {where: patch[where]})


@pytest.mark.parametrize("element_type,value", [(int, Number.TWO), (str, Text.TWO)])
@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
@pytest.mark.parametrize("typed", [False, True])
def test_enum_values_cannot_bypass_primitive_strictness(
    element_type: Any, value: Any, kind: str, typed: bool
) -> None:
    if kind == "dict":
        cfg = OmegaConf.typed_dict({}, element_type=element_type)
        supplied = {"a": value}
        if typed:
            supplied = OmegaConf.typed_dict(supplied, element_type=type(value))
    elif kind == "list":
        cfg = OmegaConf.typed_list([], element_type=element_type)
        supplied = [value]
        if typed:
            supplied = OmegaConf.typed_list(supplied, element_type=type(value))
    else:
        cfg = TupleConfig(MISSING, ref_type=tuple[element_type, ...])
        supplied = (value,)
        if typed:
            supplied = TupleConfig(supplied, ref_type=tuple[type(value), ...])
    before = snapshot(cfg)
    with pytest.raises(ValidationError):
        _validate(cfg, supplied)
    assert snapshot(cfg) == before


@pytest.mark.parametrize(
    "element_type,value",
    [(int, 2), (str, "two"), (Number, Number.TWO), (Text, Text.TWO)],
)
def test_typed_dict_compatible_primitive_and_enum_values(
    element_type: Any, value: Any
) -> None:
    cfg = OmegaConf.typed_dict({}, element_type=element_type)
    supplied = OmegaConf.typed_dict({"a": value}, element_type=element_type)
    before = snapshot(cfg), snapshot(supplied)
    _validate(cfg, supplied)
    assert (snapshot(cfg), snapshot(supplied)) == before


def test_normal_typed_dict_merge_keeps_enum_subclass_behavior() -> None:
    cfg = OmegaConf.typed_dict({}, element_type=int)
    supplied = OmegaConf.typed_dict({"a": Number.TWO}, element_type=Number)
    assert OmegaConf.merge(cfg, supplied).a is Number.TWO


@pytest.mark.parametrize("field_name", ["payload", "pair"])
@pytest.mark.parametrize("allow_objects", [False, True])
def test_supplied_object_flag_cannot_relax_supported_value_policy(
    field_name: str, allow_objects: bool
) -> None:
    obj = object()
    value = obj if field_name == "payload" else (2, {"nested": [obj]})
    supplied = OmegaConf.create(
        {field_name: value}, flags={"allow_objects": True, "convert": True}
    )
    cfg = DictConfig(MISSING, ref_type=Schema, flags={"allow_objects": allow_objects})
    before = snapshot(supplied)
    if allow_objects:
        _validate(cfg, supplied)
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, supplied)
    assert snapshot(supplied) == before


@dataclass(frozen=True)
class FrozenChild:
    count: int = MISSING
    generated: int = field(default_factory=factory)


@dataclass
class FrozenSchema:
    child: FrozenChild | None = None
    children: list[FrozenChild] = field(default_factory=list)


@pytest.mark.parametrize(
    "schema,patch",
    [
        (FrozenChild, {"count": 2}),
        (FrozenSchema, {"child": {"count": 2}, "children": [{"count": 2}]}),
    ],
)
@pytest.mark.parametrize("in_place", [False, True])
def test_frozen_structured_schemas(schema: Any, patch: Any, in_place: bool) -> None:
    cfg = DictConfig(MISSING, ref_type=schema)
    FACTORIES.clear()
    before = snapshot(cfg)
    _validate(cfg, patch, in_place=in_place)
    assert not FACTORIES
    if not in_place:
        assert snapshot(cfg) == before


@dataclass
class TupleSchema:
    child: tuple[Child, ...] = ()
    union: dict[str, Child] | list[Child] = field(default_factory=dict)


@pytest.mark.parametrize(
    "patch",
    [
        {"child": ({"count": 2},)},
        {"union": {"a": {"count": 2}}},
        {"union": [{"count": 2}]},
    ],
)
def test_structured_tuple_and_container_unions_are_defaults_free(patch: Any) -> None:
    FACTORIES.clear()
    cfg = DictConfig(MISSING, ref_type=TupleSchema)
    _validate(cfg, patch)
    assert not FACTORIES


@pytest.mark.parametrize(
    "ref_type,source,valid",
    [
        (tuple[dict[int, int], ...], {1: 2}, True),
        (tuple[dict[int, int], ...], {True: 2}, False),
        (tuple[list[int], ...], [2], True),
        (tuple[list[int], ...], ["bad"], False),
        (tuple[Child, ...], {"count": 2}, True),
        (tuple[Child, ...], {"count": "bad"}, False),
    ],
)
def test_tuple_elements_use_destination_container_schema(
    ref_type: Any, source: Any, valid: bool
) -> None:
    if ref_type == tuple[dict[int, int], ...] and isinstance(source, dict):
        typed_source = OmegaConf.typed_dict(
            source, key_type=type(next(iter(source))), element_type=int
        )
    elif ref_type == tuple[list[int], ...] and isinstance(source, list):
        typed_source = OmegaConf.typed_list(
            source, element_type=type(next(iter(source)))
        )
    else:
        typed_source = source
    source_snapshot = snapshot(typed_source) if isinstance(typed_source, Node) else None
    cfg = TupleConfig(MISSING, ref_type=ref_type)
    if valid:
        _validate(cfg, (typed_source,))
    else:
        with pytest.raises((ValidationError, KeyValidationError)):
            _validate(cfg, (typed_source,))
    if source_snapshot is not None:
        assert snapshot(typed_source) == source_snapshot


def test_empty_container_union_uses_source_metadata() -> None:
    @dataclass
    class Containers:
        value: list[int] | list[str] = field(default_factory=list)

    cfg = DictConfig(MISSING, ref_type=Containers)
    _validate(cfg, {"value": OmegaConf.typed_list([], element_type=int)})


def test_structured_source_union_preserves_inputs() -> None:
    cfg = OmegaConf.structured(Schema)
    source = OmegaConf.structured(Schema)
    source.union.count = 2
    before_cfg = snapshot(cfg)
    before_source = snapshot(source)
    FACTORIES.clear()
    _validate(cfg, source)
    assert not FACTORIES
    assert snapshot(cfg) == before_cfg
    assert snapshot(source) == before_source


@pytest.mark.parametrize("kind", ["list", "tuple"])
def test_union_source_preserves_tuple_kind(kind: str) -> None:
    @dataclass
    class Source:
        pair: list[int] | tuple[int, ...] = field(default_factory=list)

    @dataclass
    class Destination:
        pair: tuple[int, ...] = ()

    source = OmegaConf.structured(Source)
    source.pair = [1, 2] if kind == "list" else (1, 2)
    cfg = OmegaConf.structured(Destination)
    before_source = snapshot(source)
    before_cfg = snapshot(cfg)
    overrides = {"pair": source._get_node("pair")}
    if kind == "list":
        with pytest.raises(ValidationError, match="list as a tuple"):
            _validate(cfg, overrides)
    else:
        _validate(cfg, overrides)
    assert snapshot(source) == before_source
    assert snapshot(cfg) == before_cfg
    if kind == "list":
        with pytest.warns(FutureWarning, match="list to tuple"):
            cfg.pair = source._get_node("pair")
    else:
        cfg.pair = source._get_node("pair")
    assert OmegaConf.to_object(cfg.pair) == (1, 2)


def test_nullable_union_accepts_explicit_none() -> None:
    @dataclass
    class Nullable:
        value: int | str | None = None

    cfg = OmegaConf.structured(Nullable)
    before = snapshot(cfg)
    _validate(cfg, {"value": None})
    assert snapshot(cfg) == before


@dataclass
class ContainerUnionSource:
    value: list[Any] | tuple[Any, ...] | dict[Any, Any] | None = None


@dataclass
class ConcreteListDestination:
    value: list[int] | None = None


@dataclass
class ConcreteTupleDestination:
    value: tuple[int, ...] | None = None


@dataclass
class ConcreteDictDestination:
    value: dict[str, int] | None = None


def container_union_source(kind: str, content: Any) -> DictConfig:
    source = OmegaConf.structured(ContainerUnionSource)
    # Construct permissive Any sources; validation must enforce destination types.
    source._get_node("value")._set_flag("convert", True)
    if kind == "list":
        value = OmegaConf.typed_list(content, element_type=Any)
    elif kind == "tuple":
        value = TupleConfig(content, ref_type=tuple[Any, ...])
    elif kind == "dict":
        value = OmegaConf.typed_dict(content, key_type=Any, element_type=Any)
    else:
        value = None
    source.value = value
    return source


@pytest.mark.parametrize("source_kind", ["list", "tuple", "dict", "none"])
@pytest.mark.parametrize("destination_kind", ["list", "tuple", "dict"])
def test_union_source_preserves_concrete_container_kind(
    source_kind: str, destination_kind: str
) -> None:
    source = container_union_source(
        source_kind,
        {"list": [1, 2], "tuple": (1, 2), "dict": {"a": 1}, "none": None}[source_kind],
    )
    schema = {
        "list": ConcreteListDestination,
        "tuple": ConcreteTupleDestination,
        "dict": ConcreteDictDestination,
    }[destination_kind]
    cfg = DictConfig(MISSING, ref_type=schema)
    before_source = snapshot(source)
    before_cfg = snapshot(cfg)
    overrides = {"value": source._get_node("value")}
    if source_kind == destination_kind or source_kind == "none":
        _validate(cfg, overrides)
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, overrides)
    assert snapshot(source) == before_source
    assert snapshot(cfg) == before_cfg


@pytest.mark.parametrize("kind", ["list", "tuple", "dict"])
def test_union_source_retains_destination_element_type(kind: str) -> None:
    source = container_union_source(
        kind, {"list": ["bad"], "tuple": ("bad",), "dict": {"a": "bad"}}[kind]
    )
    schema = {
        "list": ConcreteListDestination,
        "tuple": ConcreteTupleDestination,
        "dict": ConcreteDictDestination,
    }[kind]
    cfg = DictConfig(MISSING, ref_type=schema)
    before_source = snapshot(source)
    before_cfg = snapshot(cfg)
    with pytest.raises(ValidationError):
        _validate(cfg, {"value": source._get_node("value")})
    assert snapshot(source) == before_source
    assert snapshot(cfg) == before_cfg


def test_union_source_retains_destination_key_type() -> None:
    source = container_union_source("dict", {False: 1})
    cfg = DictConfig(MISSING, ref_type=ConcreteDictDestination)
    before_source = snapshot(source)
    before_cfg = snapshot(cfg)
    with pytest.raises(KeyValidationError):
        _validate(cfg, {"value": source._get_node("value")})
    assert snapshot(source) == before_source
    assert snapshot(cfg) == before_cfg


def test_missing_field_patch_preserves_existing_destination() -> None:
    cfg = OmegaConf.structured(Schema)
    before = snapshot(cfg)
    FACTORIES.clear()
    _validate(cfg, {"count": MISSING})
    assert not FACTORIES
    assert snapshot(cfg) == before


@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
def test_missing_root_patch_preserves_destination(kind: str) -> None:
    cfg = {
        "dict": DictConfig({"value": 1}),
        "list": ListConfig([1]),
        "tuple": TupleConfig((1,), ref_type=tuple[int, ...]),
    }[kind]
    before = snapshot(cfg)
    _validate(cfg, MISSING)
    assert snapshot(cfg) == before


@pytest.mark.parametrize(
    "patch", [{"count": 2}, {"count": "bad"}, MISSING, None, "${absent}"]
)
def test_unresolved_validation_does_not_copy_destination_snapshot(
    patch: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = OmegaConf.create({"schema": Child, "unrelated": list(range(100))})
    cfg = root.schema
    before = snapshot(root)
    copy_with_parent = experimental._copy_with_parent
    target: Node | None = None

    def copy_without_snapshot(node: Node) -> Node:
        nonlocal target
        assert node is not target, "unresolved validation copied its destination again"
        result = copy_with_parent(node)
        if node is cfg:
            target = result
        return result

    monkeypatch.setattr(experimental, "_copy_with_parent", copy_without_snapshot)
    if patch == {"count": "bad"}:
        with pytest.raises(ValidationError):
            _validate(cfg, patch)
    else:
        _validate(cfg, patch)
    assert snapshot(root) == before


def test_cfg_must_be_an_omegaconf_container() -> None:
    invalid: Any = {}
    with pytest.raises(TypeError, match="OmegaConf container"):
        _validate(invalid, {})


def test_in_place_reuses_destination_and_preserves_supplied_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = OmegaConf.create({"schema": Schema, "unrelated": list(range(100))})
    cfg = root.schema
    OmegaConf.set_readonly(root, True)
    source = OmegaConf.create({"patch": {"count": 2, "child": {"count": 3}}})
    supplied = source.patch
    before_source = snapshot(source)
    copy_with_parent = experimental._copy_with_parent

    def copy_source_only(node: Node) -> Node:
        assert node._get_root() is not root, "owned destination graph was copied"
        return copy_with_parent(node)

    monkeypatch.setattr(experimental, "_copy_with_parent", copy_source_only)
    FACTORIES.clear()
    assert _validate(cfg, supplied, in_place=True) is None
    assert root._get_node("schema") is cfg
    assert cfg.count == 2
    assert cfg.child.count == 3
    assert cfg._get_parent() is root
    assert not FACTORIES
    assert snapshot(source) == before_source


@pytest.mark.parametrize("in_place", [False, True])
def test_failure_mutates_only_an_opted_in_destination(in_place: bool) -> None:
    cfg = OmegaConf.structured(Schema)
    source = OmegaConf.create({"patch": {"count": 2, "child": {"count": "bad"}}})
    supplied = source.patch
    before_cfg = snapshot(cfg)
    before_source = snapshot(source)
    with pytest.raises(ValidationError):
        _validate(cfg, supplied, in_place=in_place)
    assert snapshot(source) == before_source
    if in_place:
        assert cfg.count == 2
    else:
        assert snapshot(cfg) == before_cfg
    # Strict validation context must not leak into ordinary OmegaConf operations.
    assert OmegaConf.merge(OmegaConf.structured(Child), {"count": "2"}).count == 2


@pytest.mark.parametrize("in_place", [False, True])
@pytest.mark.parametrize(
    "patch", [{"count": "${deferred_validation:}"}, "${deferred_validation:}"]
)
def test_validation_never_calls_resolvers(
    restore_resolvers: Any, in_place: bool, patch: Any
) -> None:
    def fail_if_called() -> Any:
        raise AssertionError("validation evaluated an interpolation")

    OmegaConf.register_resolver("deferred_validation", fail_if_called, use_cache=True)
    cfg = DictConfig(MISSING, ref_type=Child)
    before = snapshot(cfg)
    assert _validate(cfg, patch, in_place=in_place) is None
    assert not OmegaConf.get_cache(cfg)
    if not in_place:
        assert snapshot(cfg) == before
    elif isinstance(patch, dict):
        node = cfg._get_node("count")
        assert node is not None
        assert node._value() == "${deferred_validation:}"
    else:
        assert cfg._value() == "${deferred_validation:}"


@pytest.mark.parametrize("value", [MISSING, None, "${absent}"])
def test_in_place_root_special_values(value: Any) -> None:
    cfg = OmegaConf.structured(Child)
    OmegaConf.set_readonly(cfg, True)
    _validate(cfg, value, in_place=True)
    assert cfg._value() == value


@pytest.mark.parametrize(
    "cfg,patch", [(ListConfig([]), {}), (DictConfig({}), [1]), (TupleConfig(()), {})]
)
def test_incompatible_root_kind_raises_validation_error(cfg: Any, patch: Any) -> None:
    with pytest.raises(ValidationError, match="incompatible container"):
        _validate(cfg, patch)


def test_unchanged_omitted_fields_are_not_validated() -> None:
    cfg = OmegaConf.structured(Schema)
    cfg.child = Child(count=2, generated="${absent}")  # type: ignore[arg-type]
    cfg.union = {"count": 2, "generated": "${absent}"}
    _validate(cfg, {"child": {"count": 3}, "union": {"count": 3}})


def test_untyped_fields_remain_any() -> None:
    cfg = OmegaConf.create({"count": 2})
    _validate(cfg, {"count": "2"})
    _validate(cfg, {"count": [None, {"arbitrary": (True,)}]})


def test_nested_selected_union_can_be_the_validation_root() -> None:
    root = OmegaConf.structured(Schema)
    cfg = root.union
    before = snapshot(root)
    FACTORIES.clear()
    _validate(cfg, {"count": 2})
    assert not FACTORIES
    assert snapshot(root) == before


@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
def test_non_optional_root_null(kind: str) -> None:
    cfg = {
        "dict": DictConfig(MISSING, ref_type=Child, is_optional=False),
        "list": ListConfig(MISSING, element_type=int, is_optional=False),
        "tuple": TupleConfig(MISSING, ref_type=tuple[int, ...], is_optional=False),
    }[kind]
    before = snapshot(cfg)
    with pytest.raises(ValidationError):
        _validate(cfg, None)
    assert snapshot(cfg) == before


def test_cached_opaque_object_does_not_require_copying(restore_resolvers: Any) -> None:
    class RuntimeObject:
        def __deepcopy__(self, memo: Any) -> Any:
            raise RuntimeError("runtime object cannot be copied")

    obj = RuntimeObject()
    calls: list[int] = []
    OmegaConf.register_resolver(
        "opaque_validation",
        lambda: calls.append(1) or obj,
        use_cache=True,
        annotation_validation="off",
    )
    cfg = OmegaConf.structured(Schema, flags={"allow_objects": True})
    cfg.payload = "${opaque_validation:}"
    assert cfg.payload is obj
    before_cache = {
        name: dict(entries) for name, entries in OmegaConf.get_cache(cfg).items()
    }
    _validate(cfg, {"payload": "${opaque_validation:}"})
    assert calls == [1]
    assert OmegaConf.get_cache(cfg) == before_cache
    assert cfg._get_node("payload")._value() == "${opaque_validation:}"


@pytest.mark.parametrize("schema", [Child, AttrChild])
def test_supplied_structured_instances_are_not_reconstructed(schema: Any) -> None:
    supplied = schema(count=2)
    cfg = DictConfig(MISSING, ref_type=schema)
    FACTORIES.clear()
    _validate(cfg, supplied)
    assert not FACTORIES
    assert supplied.count == 2
    assert supplied.generated == 10


@pytest.mark.parametrize("schema", [SourceHolder, AttrSourceHolder])
def test_structured_instance_source_flags_cannot_weaken_destination(
    schema: Any,
) -> None:
    source_node = OmegaConf.create({"x": object()}, flags={"allow_objects": True})
    source_value = source_node._get_node("x")
    assert isinstance(source_value, Node)
    source_value._set_flag("allow_objects", True)
    supplied = schema(items=[source_node])
    source_before = snapshot(source_node)
    cfg = DictConfig(MISSING, ref_type=schema, flags={"allow_objects": False})
    with pytest.raises(ValidationError):
        _validate(cfg, supplied)
    assert supplied.items[0] is source_node
    assert snapshot(source_node) == source_before
