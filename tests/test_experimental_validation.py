import copy
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any

import attr
import pytest

from omegaconf import (
    MISSING,
    BooleanNode,
    Container,
    DictConfig,
    ListConfig,
    OmegaConf,
    TupleConfig,
)
from omegaconf.base import Node
from omegaconf.errors import (
    ConfigKeyError,
    InterpolationResolutionError,
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


@dataclass
class NestedAny:
    payload: Any = None


@dataclass
class NestedAnySchema:
    child: NestedAny | None = None
    mapping: dict[str, Any] = field(default_factory=dict)
    values: list[Any] = field(default_factory=list)
    pair: tuple[Any, ...] = ()


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
def test_absent_schema_never_reads_defaults(schema: Any, content: Any) -> None:
    cfg = DictConfig(content, ref_type=schema)
    before = snapshot(cfg)
    FACTORIES.clear()
    assert _validate(cfg, {"count": 2}) is None
    assert not FACTORIES
    assert snapshot(cfg) == before


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
def test_partial_nested_schema_without_factories(overrides: Any) -> None:
    cfg = DictConfig(MISSING, ref_type=Schema)
    FACTORIES.clear()
    _validate(cfg, overrides)
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
def test_strict_rejection(overrides: Any) -> None:
    cfg = DictConfig(MISSING, ref_type=Schema)
    FACTORIES.clear()
    with pytest.raises((ValidationError, KeyValidationError)):
        _validate(cfg, overrides)
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
def test_any_uses_destination_object_policy(
    root_allow: bool, child_allow: bool, source_config: bool
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
        _validate(cfg, overrides)
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, overrides)
    if source_config:
        assert snapshot(overrides) == before


@pytest.mark.parametrize("root_allow,child_allow", [(True, False), (False, True)])
def test_resolved_any_uses_destination_object_policy(
    restore_resolvers: Any, root_allow: bool, child_allow: bool
) -> None:
    OmegaConf.register_resolver(
        "destination_object_validation", object, annotation_validation="off"
    )
    cfg = OmegaConf.structured(Schema, flags={"allow_objects": root_allow})
    cfg._get_node("payload")._set_flag("allow_objects", child_allow)
    if child_allow:
        _validate(cfg, {"payload": "${destination_object_validation:}"}, resolve=True)
    else:
        with pytest.raises(ValidationError):
            _validate(
                cfg,
                {"payload": "${destination_object_validation:}"},
                resolve=True,
            )


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
def test_no_key_kind_conversion(key_type: Any, key: Any) -> None:
    cfg = OmegaConf.typed_dict({}, key_type=key_type, element_type=int)
    with pytest.raises(KeyValidationError):
        _validate(cfg, {key: 2})


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


@pytest.mark.parametrize("resolve", [False, True])
def test_unknown_structured_field(resolve: bool) -> None:
    with pytest.raises(ConfigKeyError):
        _validate(DictConfig(MISSING, ref_type=Child), {"extra": 2}, resolve=resolve)


@pytest.mark.parametrize("bad", [False, True])
def test_resolution_preserves_inputs_and_ancestor_context(bad: bool) -> None:
    root = OmegaConf.create({"answer": "bad" if bad else 2, "schema": Schema})
    cfg = root.schema
    OmegaConf.set_readonly(root, True)
    supplied = OmegaConf.create({"child": {"count": "${answer}"}})
    OmegaConf.set_readonly(supplied.child, True)
    before = snapshot(root), snapshot(supplied)
    if bad:
        with pytest.raises(InterpolationResolutionError):
            _validate(cfg, supplied, resolve=True)
    else:
        _validate(cfg, supplied, resolve=True)
    assert (snapshot(root), snapshot(supplied)) == before


def test_resolution_only_checks_supplied_fields() -> None:
    cfg = OmegaConf.structured(Child)
    cfg.generated = "${absent}"
    _validate(cfg, {"count": 2}, resolve=True)


@pytest.mark.parametrize("resolve", [False, True])
@pytest.mark.parametrize("result", [2, "bad"])
def test_cached_resolvers_are_private(
    restore_resolvers: Any, resolve: bool, result: Any
) -> None:
    calls: list[int] = []
    OmegaConf.register_resolver(
        "validation_test",
        lambda: calls.append(1) or result,
        use_cache=True,
        annotation_validation="off",
    )
    root = OmegaConf.create({"answer": "${validation_test:}", "schema": Child})
    cfg = root.schema
    supplied = OmegaConf.create({"count": "${answer}"})
    before = snapshot(root), snapshot(supplied)
    if resolve and result == "bad":
        with pytest.raises(InterpolationResolutionError):
            _validate(cfg, supplied, resolve=resolve)
    else:
        _validate(cfg, supplied, resolve=resolve)
    assert calls == ([1] if resolve else [])
    assert (snapshot(root), snapshot(supplied)) == before


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


@pytest.mark.parametrize("resolve", [False, True])
def test_overwritten_interpolation_does_not_run_resolver(
    restore_resolvers: Any, resolve: bool
) -> None:
    calls: list[int] = []
    OmegaConf.register_resolver(
        "unused_validation", lambda: calls.append(1), annotation_validation="off"
    )
    cfg = OmegaConf.structured(Schema)
    cfg.child = "${unused_validation:}"
    before = snapshot(cfg)
    _validate(cfg, {"child": {"count": 2}}, resolve=resolve)
    assert not calls
    assert snapshot(cfg) == before


@pytest.mark.parametrize("expression", ["${.count}", "${..count}", "${answer}"])
def test_relative_and_absolute_interpolation(expression: str) -> None:
    root = OmegaConf.create({"answer": 2, "schema": Schema})
    cfg = root.schema
    cfg.count = 2
    before = snapshot(root)
    patch = {"child": {"count": expression}}
    if expression == "${.count}":
        # A self-reference must fail without changing either input.
        with pytest.raises(InterpolationResolutionError):
            _validate(cfg, patch, resolve=True)
    else:
        _validate(cfg, patch, resolve=True)
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "field_name,result,valid",
    [
        ("numbers", [2], True),
        ("numbers", ["2"], False),
        ("numbers", (2,), False),
        ("pair", (2, "x"), True),
        ("pair", [2, "x"], False),
        ("child", {"count": 2}, True),
        ("child", {"count": "2"}, False),
        ("children", [{"count": 2}], True),
        ("children", [{"count": "2"}], False),
        ("keyed", {Color.RED: 2}, True),
        ("keyed", {"RED": 2}, False),
        ("union", {"count": 2}, True),
        ("union", {"count": "2"}, False),
        ("union", [2], True),
        ("union", ["2"], False),
        ("payload", {"nested": [2]}, True),
    ],
)
def test_resolved_containers_are_strict_and_defaults_free(
    restore_resolvers: Any, field_name: str, result: Any, valid: bool
) -> None:
    OmegaConf.register_resolver(
        "validation_result", lambda: result, annotation_validation="off"
    )
    cfg = OmegaConf.structured(Schema)
    FACTORIES.clear()
    before = snapshot(cfg)
    if valid:
        _validate(cfg, {field_name: "${validation_result:}"}, resolve=True)
    else:
        with pytest.raises(
            (ValidationError, InterpolationResolutionError, KeyValidationError)
        ):
            _validate(cfg, {field_name: "${validation_result:}"}, resolve=True)
    assert not FACTORIES
    assert snapshot(cfg) == before


def test_optional_container_interpolation_resolves_once(
    restore_resolvers: Any,
) -> None:
    calls: list[int] = []
    OmegaConf.register_resolver(
        "optional_container_once",
        lambda: calls.append(1),
        replace=True,
        annotation_validation="off",
    )
    cfg = OmegaConf.structured(Schema)
    _validate(cfg, {"numbers": "${optional_container_once:}"}, resolve=True)
    assert calls == [1]


def test_whole_root_interpolation_checks_only_returned_fields(
    restore_resolvers: Any,
) -> None:
    @dataclass
    class WholeRootSchema:
        count: int = 0
        omitted: int = 1

    cfg = OmegaConf.structured(WholeRootSchema)
    cfg._get_node("omitted").__dict__["_val"] = "invalid unchanged field"
    before = snapshot(cfg)
    OmegaConf.register_resolver(
        "partial_whole_root",
        lambda: {"count": 2},
        replace=True,
        annotation_validation="off",
    )
    _validate(cfg, "${partial_whole_root:}", resolve=True)
    assert snapshot(cfg) == before


@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
def test_recursive_direct_container_is_rejected(kind: str) -> None:
    with pytest.raises(ValidationError, match="recursive input container"):
        _validate(DictConfig({}), recursive_container(kind))


@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
def test_recursive_resolver_container_is_rejected(
    restore_resolvers: Any, kind: str
) -> None:
    resolver_name = f"recursive_validation_{kind}"
    OmegaConf.register_resolver(
        resolver_name,
        lambda kind=kind: recursive_container(kind),
        replace=True,
        annotation_validation="off",
    )
    try:
        cfg = DictConfig(MISSING, ref_type=dict[str, Any])
        with pytest.raises(
            InterpolationResolutionError, match="recursive resolver result"
        ):
            _validate(cfg, f"${{{resolver_name}:}}", resolve=True)

        ordinary = OmegaConf.structured(Schema)
        with pytest.warns(FutureWarning):
            ordinary.count = "1"
        assert ordinary.count == 1
    finally:
        OmegaConf.clear_resolver(resolver_name)


def test_shared_acyclic_container_is_accepted() -> None:
    shared = {"count": 2}
    _validate(
        DictConfig({}),
        {"left": shared, "right": shared},
    )


def test_whole_cfg_resolver_uses_actual_private_parent(
    restore_resolvers: Any,
) -> None:
    seen: list[bool] = []

    def resolve(*, _parent_: Any) -> dict[str, int]:
        seen.append("marker" in _parent_)
        return {"count": 2 if seen[-1] else 3}

    OmegaConf.register_resolver(
        "whole_cfg_parent_context",
        resolve,
        replace=True,
        annotation_validation="off",
    )
    root = OmegaConf.create({"marker": 2, "schema": Schema})
    cfg = root.schema
    before = snapshot(root)
    _validate(cfg, "${whole_cfg_parent_context:}", resolve=True)
    assert seen == [True]
    assert snapshot(root) == before


def test_whole_cfg_relative_alias_uses_actual_private_parent(
    restore_resolvers: Any,
) -> None:
    root = OmegaConf.create({"scope": {"source": {"count": 2}, "schema": Schema}})
    cfg = root.scope.schema
    before = snapshot(root)
    _validate(cfg, "${.source}", resolve=True)
    assert snapshot(root) == before


@pytest.mark.parametrize("container_kind", ["dict", "list", "tuple"])
@pytest.mark.parametrize("source_kind", ["plain", "config_false", "config_true"])
@pytest.mark.parametrize("root_allow,child_allow", [(True, False), (False, True)])
def test_resolved_object_and_resolver_container_policy(
    restore_resolvers: Any,
    container_kind: str,
    source_kind: str,
    root_allow: bool,
    child_allow: bool,
) -> None:
    obj = object()
    result: Any = {
        "dict": {"item": obj},
        "list": [obj],
        "tuple": (obj,),
    }[container_kind]
    source_before: list[Any] | None = None
    if source_kind != "plain":
        result = OmegaConf.create(result, flags={"allow_objects": True})
        result._set_flag("allow_objects", source_kind == "config_true")
        OmegaConf.set_readonly(result, True)
        source_before = snapshot(result)

    OmegaConf.register_resolver(
        "resolved_object_resolver_container",
        lambda: result,
        replace=True,
        annotation_validation="off",
    )
    cfg = OmegaConf.structured(Schema, flags={"allow_objects": root_allow})
    cfg._get_node("payload")._set_flag("allow_objects", child_allow)
    cfg_before = snapshot(cfg)
    patch = {"payload": "${resolved_object_resolver_container:}"}
    if child_allow:
        _validate(cfg, patch, resolve=True)
    else:
        with pytest.raises(ValidationError):
            _validate(cfg, patch, resolve=True)
    assert snapshot(cfg) == cfg_before
    if source_before is not None:
        assert snapshot(result) == source_before


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


@pytest.mark.parametrize("placement", ["root", "nested"])
@pytest.mark.parametrize("container_kind", ["dict", "list", "tuple"])
@pytest.mark.parametrize("source_kind", ["plain", "config_false", "config_true"])
@pytest.mark.parametrize("destination_allow", [False, True])
def test_resolved_typed_container_uses_destination_policy(
    restore_resolvers: Any,
    placement: str,
    container_kind: str,
    source_kind: str,
    destination_allow: bool,
) -> None:
    obj = object()
    raw = {
        "dict": {"item": obj},
        "list": [obj],
        "tuple": (obj,),
    }[container_kind]

    def make_container(value: Any, allow_objects: bool) -> Any:
        flags = {"allow_objects": allow_objects}
        if container_kind == "dict":
            return DictConfig(
                value,
                key_type=str,
                element_type=Any,
                ref_type=dict[str, Any],
                flags=flags,
            )
        if container_kind == "list":
            return ListConfig(value, element_type=Any, ref_type=list[Any], flags=flags)
        return TupleConfig(value, ref_type=tuple[Any, ...], flags=flags)

    result: Any = raw
    source_before: list[Any] | None = None
    if source_kind != "plain":
        result = make_container(raw, True)
        result._set_flag("allow_objects", source_kind == "config_true")
        source_child = (
            result._get_node("item")
            if container_kind == "dict"
            else result._get_node(0)
        )
        assert isinstance(source_child, Node)
        source_child._set_flag("allow_objects", source_kind == "config_true")
        OmegaConf.set_readonly(result, True)
        source_before = snapshot(result)

    OmegaConf.register_resolver(
        "typed_container_destination_policy",
        lambda result=result: result,
        replace=True,
        annotation_validation="off",
    )
    destination = make_container(
        {"dict": {}, "list": [], "tuple": ()}[container_kind],
        destination_allow,
    )
    parent = OmegaConf.create(
        {"scope": destination}, flags={"allow_objects": not destination_allow}
    )
    destination = parent._get_node("scope")
    assert isinstance(destination, (DictConfig, ListConfig, TupleConfig))
    destination._set_flag("allow_objects", destination_allow)
    before = snapshot(parent)

    if destination_allow:
        if placement == "root":
            _validate(
                destination, "${typed_container_destination_policy:}", resolve=True
            )
        else:
            _validate(
                parent,
                {"scope": "${typed_container_destination_policy:}"},
                resolve=True,
            )
    else:
        with pytest.raises((ValidationError, InterpolationResolutionError)):
            if placement == "root":
                _validate(
                    destination,
                    "${typed_container_destination_policy:}",
                    resolve=True,
                )
            else:
                _validate(
                    parent,
                    {"scope": "${typed_container_destination_policy:}"},
                    resolve=True,
                )

    assert snapshot(parent) == before
    if source_before is not None:
        assert snapshot(result) == source_before


@pytest.mark.parametrize(
    "field_name,empty_value,result",
    [
        ("mapping", {"item": None}, {"item": object()}),
        ("values", [None], [object()]),
        ("pair", (None,), (object(),)),
        ("child", NestedAny(), {"payload": object()}),
    ],
)
@pytest.mark.parametrize("source_kind", ["plain", "config_false", "config_true"])
@pytest.mark.parametrize("root_allow,child_allow", [(True, False), (False, True)])
def test_resolved_nested_any_uses_destination_policy(
    restore_resolvers: Any,
    field_name: str,
    empty_value: Any,
    result: Any,
    source_kind: str,
    root_allow: bool,
    child_allow: bool,
) -> None:
    cfg = OmegaConf.structured(NestedAnySchema, flags={"allow_objects": root_allow})
    setattr(cfg, field_name, empty_value)
    destination = cfg._get_node(field_name)
    assert isinstance(destination, Container)
    if field_name == "child":
        destination = destination._get_node("payload")
    elif field_name == "mapping":
        destination = destination._get_node("item")
    else:
        destination = destination._get_node(0)
    assert isinstance(destination, Node)
    destination._set_flag("allow_objects", child_allow)

    source_before: list[Any] | None = None
    if source_kind != "plain":
        source = OmegaConf.create(result, flags={"allow_objects": True})
        source._set_flag("allow_objects", source_kind == "config_true")
        source_child = (
            source._get_node("payload")
            if field_name == "child"
            else source._get_node("item")
            if field_name == "mapping"
            else source._get_node(0)
        )
        assert isinstance(source_child, Node)
        source_child._set_flag("allow_objects", source_kind == "config_true")
        OmegaConf.set_readonly(source, True)
        result = source
        source_before = snapshot(source)

    OmegaConf.register_resolver(
        "resolved_nested_any_policy",
        lambda result=result: result,
        replace=True,
        annotation_validation="off",
    )
    cfg_before = snapshot(cfg)
    patch = {field_name: "${resolved_nested_any_policy:}"}
    if child_allow:
        _validate(cfg, patch, resolve=True)
    else:
        with pytest.raises((ValidationError, InterpolationResolutionError)):
            _validate(cfg, patch, resolve=True)
    assert snapshot(cfg) == cfg_before
    if source_before is not None:
        assert snapshot(result) == source_before


def test_resolved_same_typed_dict_revalidates_enum_keys(
    restore_resolvers: Any,
) -> None:
    source = DictConfig(
        {Text.TWO: 2},
        key_type=str,
        element_type=int,
        ref_type=dict[str, int],
    )
    source_before = snapshot(source)
    OmegaConf.register_resolver(
        "resolved_same_typed_dict_enum_key",
        lambda: source,
        replace=True,
        annotation_validation="off",
    )
    cfg = OmegaConf.create(
        {
            "values": DictConfig(
                {},
                key_type=str,
                element_type=int,
                ref_type=dict[str, int],
            )
        }
    )
    cfg_before = snapshot(cfg)
    with pytest.raises(KeyValidationError):
        _validate(
            cfg,
            {"values": "${resolved_same_typed_dict_enum_key:}"},
            resolve=True,
        )
    assert snapshot(source) == source_before
    assert snapshot(cfg) == cfg_before


@pytest.mark.parametrize("valid", [False, True])
def test_resolver_returned_config_is_not_mutated(
    restore_resolvers: Any, valid: bool
) -> None:
    external = OmegaConf.create(
        {"answer": 2 if valid else "bad", "child": {"count": "${..answer}"}}
    )
    OmegaConf.set_readonly(external, True)
    child = external.child
    OmegaConf.register_resolver(
        "external_validation",
        lambda: child,
        use_cache=True,
        annotation_validation="off",
    )
    cfg = OmegaConf.structured(Schema)
    before = snapshot(external), snapshot(cfg)
    if valid:
        _validate(cfg, {"child": "${external_validation:}"}, resolve=True)
    else:
        with pytest.raises(InterpolationResolutionError):
            _validate(cfg, {"child": "${external_validation:}"}, resolve=True)
    assert (snapshot(external), snapshot(cfg)) == before


@pytest.mark.parametrize(
    "destination,result,valid",
    [
        ("typed", 2, True),
        ("typed", "bad", False),
        ("any", 2, True),
        ("any", "bad", True),
    ],
)
def test_external_scalar_interpolation_is_resolved_privately(
    restore_resolvers: Any, destination: str, result: Any, valid: bool
) -> None:
    calls: list[int] = []
    OmegaConf.register_resolver(
        "external_scalar_validation_inner",
        lambda: calls.append(1) or result,
        annotation_validation="off",
    )
    external = OmegaConf.create({"value": "${external_scalar_validation_inner:}"})
    external_node = external._get_node("value")
    OmegaConf.register_resolver(
        "external_scalar_validation_outer",
        lambda: external_node,
        use_cache=True,
        annotation_validation="off",
    )
    cfg = DictConfig(MISSING, ref_type=Schema if destination == "any" else Child)
    before = snapshot(external), snapshot(cfg)
    field = "payload" if destination == "any" else "count"
    if valid:
        _validate(
            cfg,
            {field: "${external_scalar_validation_outer:}"},
            resolve=True,
        )
    else:
        with pytest.raises(InterpolationResolutionError):
            _validate(
                cfg,
                {field: "${external_scalar_validation_outer:}"},
                resolve=True,
            )
    assert calls == [1]
    assert (snapshot(external), snapshot(cfg)) == before


def test_external_scalar_interpolation_failure_is_propagated(
    restore_resolvers: Any,
) -> None:
    def fail() -> Any:
        raise RuntimeError("broken external scalar resolver")

    OmegaConf.register_resolver(
        "external_scalar_validation_failure", fail, annotation_validation="off"
    )
    external = OmegaConf.create({"value": "${external_scalar_validation_failure:}"})
    external_node = external._get_node("value")
    OmegaConf.register_resolver(
        "external_scalar_validation_failure_outer",
        lambda: external_node,
        annotation_validation="off",
    )
    with pytest.raises(InterpolationResolutionError, match="broken external scalar"):
        _validate(
            DictConfig(MISSING, ref_type=Schema),
            {"payload": "${external_scalar_validation_failure_outer:}"},
            resolve=True,
        )


def test_existing_cache_is_preserved(restore_resolvers: Any) -> None:
    calls: list[int] = []
    OmegaConf.register_resolver(
        "cached_validation",
        lambda: calls.append(1) or 2,
        use_cache=True,
        annotation_validation="off",
    )
    root = OmegaConf.create({"answer": "${cached_validation:}", "schema": Child})
    assert root.answer == 2
    cfg = root.schema
    before = snapshot(root)
    _validate(cfg, {"count": "${answer}"}, resolve=True)
    assert calls == [1]
    assert snapshot(root) == before


@pytest.mark.parametrize("value", [None, MISSING])
@pytest.mark.parametrize("kind", ["list", "tuple", "dict"])
def test_root_special_values(kind: str, value: Any) -> None:
    cfg = {
        "list": ListConfig(None, element_type=int),
        "tuple": TupleConfig(None, ref_type=tuple[int, ...]),
        "dict": DictConfig(None, ref_type=Child),
    }[kind]
    before = snapshot(cfg)
    _validate(cfg, value, resolve=True)
    assert snapshot(cfg) == before


@pytest.mark.parametrize("resolve", [False, True])
def test_supplied_nodes_have_isolated_parents(resolve: bool) -> None:
    source = OmegaConf.create({"other": 1, "patch": {"count": "${answer}"}})
    root = OmegaConf.create({"answer": 2, "schema": Child})
    cfg = root.schema
    patch = source.patch
    before = snapshot(root), snapshot(source)
    _validate(cfg, patch, resolve=resolve)
    assert (snapshot(root), snapshot(source)) == before


def test_failure_does_not_leak_private_context() -> None:
    with pytest.raises(ValidationError):
        _validate(DictConfig(MISSING, ref_type=Child), {"count": "2"})
    FACTORIES.clear()
    cfg = OmegaConf.structured(Child)
    assert FACTORIES == ["called"]
    assert OmegaConf.merge(cfg, {"count": "2"}).count == 2


@pytest.mark.parametrize("resolve", [False, True])
@pytest.mark.parametrize("where", ["count", "numbers", "keyed", "pair", "union"])
def test_typed_scalar_nodes_cannot_bypass_strictness(where: str, resolve: bool) -> None:
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
        _validate(cfg, {where: patch[where]}, resolve=resolve)


@pytest.mark.parametrize("element_type,value", [(int, Number.TWO), (str, Text.TWO)])
@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("resolve", [False, True])
def test_enum_values_cannot_bypass_primitive_strictness(
    element_type: Any, value: Any, kind: str, typed: bool, resolve: bool
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
        _validate(cfg, supplied, resolve=resolve)
    assert snapshot(cfg) == before


@pytest.mark.parametrize("element_type,value", [(int, Number.TWO), (str, Text.TWO)])
def test_resolved_typed_dict_cannot_bypass_primitive_strictness(
    restore_resolvers: Any, element_type: Any, value: Any
) -> None:
    supplied = OmegaConf.typed_dict({"a": value}, element_type=type(value))
    OmegaConf.register_resolver(
        "enum_validation", lambda: supplied, annotation_validation="off"
    )
    cfg = OmegaConf.create(
        {"values": OmegaConf.typed_dict({}, element_type=element_type)}
    )
    before = snapshot(cfg), snapshot(supplied)
    with pytest.raises(InterpolationResolutionError):
        _validate(cfg, {"values": "${enum_validation:}"}, resolve=True)
    assert (snapshot(cfg), snapshot(supplied)) == before


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


@pytest.mark.parametrize("resolve", [False, True])
@pytest.mark.parametrize(
    "schema,patch",
    [
        (FrozenChild, {"count": 2}),
        (FrozenSchema, {"child": {"count": 2}, "children": [{"count": 2}]}),
    ],
)
def test_frozen_structured_schemas(schema: Any, patch: Any, resolve: bool) -> None:
    cfg = DictConfig(MISSING, ref_type=schema)
    FACTORIES.clear()
    before = snapshot(cfg)
    _validate(cfg, patch, resolve=resolve)
    assert not FACTORIES
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


@pytest.mark.parametrize("resolve", [False, True])
def test_structured_source_union_preserves_inputs(resolve: bool) -> None:
    cfg = OmegaConf.structured(Schema)
    source = OmegaConf.structured(Schema)
    source.union.count = 2
    before_cfg = snapshot(cfg)
    before_source = snapshot(source)
    FACTORIES.clear()
    _validate(cfg, source, resolve=resolve)
    assert not FACTORIES
    assert snapshot(cfg) == before_cfg
    assert snapshot(source) == before_source


@pytest.mark.parametrize("kind", ["dict", "list", "tuple"])
def test_resolver_config_in_any_tuple_slot_is_private(
    restore_resolvers: Any, kind: str
) -> None:
    external = {
        "dict": DictConfig({"count": 2}),
        "list": ListConfig([2]),
        "tuple": TupleConfig((2,), ref_type=tuple[int, ...]),
    }[kind]
    OmegaConf.set_readonly(external, True)
    cfg = TupleConfig((None,), ref_type=tuple[Any])
    before_cfg = snapshot(cfg)
    before_external = snapshot(external)
    OmegaConf.register_resolver("tuple_config_validation", lambda: external)
    _validate(cfg, ("${tuple_config_validation:}",), resolve=True)
    assert snapshot(cfg) == before_cfg
    assert snapshot(external) == before_external


@pytest.mark.parametrize("kind", ["list", "tuple"])
@pytest.mark.parametrize("resolve", [False, True])
def test_union_source_preserves_tuple_kind(kind: str, resolve: bool) -> None:
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
            _validate(cfg, overrides, resolve=resolve)
    else:
        _validate(cfg, overrides, resolve=resolve)
    assert snapshot(source) == before_source
    assert snapshot(cfg) == before_cfg
    if kind == "list":
        with pytest.warns(FutureWarning, match="list to tuple"):
            cfg.pair = source._get_node("pair")
    else:
        cfg.pair = source._get_node("pair")
    assert OmegaConf.to_object(cfg.pair) == (1, 2)


@pytest.mark.parametrize("resolve", [False, True])
def test_nullable_union_accepts_explicit_none(resolve: bool) -> None:
    @dataclass
    class Nullable:
        value: int | str | None = None

    cfg = OmegaConf.structured(Nullable)
    before = snapshot(cfg)
    _validate(cfg, {"value": None}, resolve=resolve)
    assert snapshot(cfg) == before


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


@pytest.mark.parametrize("bad", [False, True])
def test_nested_resolution_in_lists_and_tuples(bad: bool) -> None:
    root = OmegaConf.create({"answer": "bad" if bad else 2, "schema": TupleSchema})
    cfg = root.schema
    patch = {"child": ({"count": "${answer}"},), "union": [{"count": "${answer}"}]}
    before = snapshot(root)
    FACTORIES.clear()
    if bad:
        with pytest.raises(InterpolationResolutionError):
            _validate(cfg, patch, resolve=True)
    else:
        _validate(cfg, patch, resolve=True)
    assert not FACTORIES
    assert snapshot(root) == before


def test_resolver_failure_does_not_modify_any_input(restore_resolvers: Any) -> None:
    def fail() -> Any:
        raise RuntimeError("broken resolver")

    OmegaConf.register_resolver("validation_failure", fail)
    root = OmegaConf.create({"schema": Child})
    cfg = root.schema
    supplied = OmegaConf.create({"count": "${validation_failure:}"})
    before = snapshot(root), snapshot(supplied)
    with pytest.raises(InterpolationResolutionError, match="broken resolver"):
        _validate(cfg, supplied, resolve=True)
    assert (snapshot(root), snapshot(supplied)) == before


def test_cfg_must_be_an_omegaconf_container() -> None:
    invalid: Any = {}
    with pytest.raises(TypeError, match="OmegaConf container"):
        _validate(invalid, {})


def test_resolver_body_keeps_normal_omegaconf_behavior(restore_resolvers: Any) -> None:
    def resolve() -> int:
        result = OmegaConf.structured(Child)
        return result.generated

    OmegaConf.register_resolver("construct_validation", resolve)
    FACTORIES.clear()
    _validate(
        DictConfig(MISSING, ref_type=Child),
        {"count": "${construct_validation:}"},
        resolve=True,
    )
    # This factory belongs to the resolver's explicit construction, not validation.
    assert FACTORIES == ["called"]


@pytest.mark.parametrize(
    "cfg,patch", [(ListConfig([]), {}), (DictConfig({}), [1]), (TupleConfig(()), {})]
)
def test_incompatible_root_kind_raises_validation_error(cfg: Any, patch: Any) -> None:
    with pytest.raises(ValidationError, match="incompatible container"):
        _validate(cfg, patch)


@pytest.mark.parametrize("resolve", [False, True])
def test_unchanged_omitted_fields_are_not_validated(resolve: bool) -> None:
    cfg = OmegaConf.structured(Schema)
    cfg.child = Child(count=2, generated="${absent}")  # type: ignore[arg-type]
    cfg.union = {"count": 2, "generated": "${absent}"}
    _validate(cfg, {"child": {"count": 3}, "union": {"count": 3}}, resolve=resolve)


def test_reentrant_validation_restores_outer_strictness(restore_resolvers: Any) -> None:
    def resolve() -> str:
        inner = DictConfig(MISSING, ref_type=Schema, flags={"allow_objects": True})
        _validate(inner, {"payload": object()})
        return "2"

    OmegaConf.register_resolver("nested_validation", resolve)
    cfg = DictConfig(MISSING, ref_type=Child)
    with pytest.raises(InterpolationResolutionError):
        _validate(cfg, {"count": "${nested_validation:}"}, resolve=True)


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
    _validate(cfg, {"payload": "${opaque_validation:}"}, resolve=True)
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
