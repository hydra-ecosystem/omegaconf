from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Literal, cast

import attr
from pytest import mark, raises

from omegaconf import MISSING, DictConfig, MissingMandatoryValue, OmegaConf
from omegaconf.base import Node
from omegaconf.basecontainer import _deep_update_type_hint
from omegaconf.errors import (
    ConfigKeyError,
    KeyValidationError,
    ReadonlyConfigError,
    ValidationError,
)
from omegaconf.nodes import AnyNode, IntegerNode


@mark.parametrize("shape", ["list", "dict", "tuple"])
@mark.parametrize("convert", [True, False])
def test_construction_applies_source_policy_before_conversion(
    shape: str, convert: bool
) -> None:
    source = OmegaConf.typed_list(["5"], str)
    source_node = source._get_node(0)
    assert isinstance(source_node, Node)
    source_node._set_flag(["convert", "readonly"], [convert, True])

    def construct() -> Any:
        if shape == "list":
            return OmegaConf.typed_list(cast(Any, source), int)
        if shape == "dict":
            return OmegaConf.typed_dict({"value": source._get_node(0)}, str, int)
        return OmegaConf.typed_tuple((source._get_node(0),), tuple[int])

    if convert:
        result = construct()
        key = "value" if shape == "dict" else 0
        assert result[key] == 5
        node = result._get_node(key)
        assert node._metadata.flags == {"convert": True, "readonly": True}
        assert node._get_parent() is result
        assert node is not source._get_node(0)
    else:
        with raises(ValidationError):
            construct()
    assert source[0] == "5"
    assert source_node._get_parent() is source


def test_typed_dictionary_reconstructs_supplied_typed_values() -> None:
    source = OmegaConf.typed_dict({"value": "5"}, str, str)
    result = OmegaConf.typed_dict(cast(Any, source), str, int)
    assert result.value == 5
    assert source.value == "5"


def test_direct_structured_mapping_construction_validates_and_adds_defaults() -> None:
    @dataclass
    class Child:
        count: int = 1
        label: str = "default"

    result = DictConfig({"count": "5"}, ref_type=Child)
    assert OmegaConf.to_object(result) == Child(count=5)
    with raises(ValidationError):
        DictConfig({"count": "bad"}, ref_type=Child)
    with raises(ConfigKeyError):
        DictConfig({"unknown": 1}, ref_type=Child)


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_structured_construction_preserves_field_policy_but_merge_keeps_precedence() -> (
    None
):
    @dataclass
    class Child:
        count: int = 1

    @dataclass
    class Parent:
        child: Child = field(default_factory=Child)

    source = IntegerNode(5, flags={"readonly": True, "convert": False})
    target = OmegaConf.structured(Parent)
    target.child = {"count": source}
    child = target._get_node("child")
    assert isinstance(child, DictConfig)
    child_node = child._get_node("count")
    assert isinstance(child_node, IntegerNode)
    assert child_node._metadata.flags == source._metadata.flags
    with raises(ReadonlyConfigError):
        child.count = 6
    merged = OmegaConf.merge(OmegaConf.structured(Child), {"count": source})
    assert isinstance(merged, DictConfig)
    merged_node = merged._get_node("count")
    assert isinstance(merged_node, IntegerNode)
    assert merged_node._metadata.flags == {}
    merged.count = "6"
    assert merged.count == 6


def test_reconstruction_cannot_enable_union_conversion() -> None:
    source = OmegaConf.create([AnyNode(1, flags={"convert": True})])
    target = OmegaConf.typed_list([], list[int | str])
    target.append(source)
    assert target[0]._get_node(0)._get_flag("convert") is False
    with raises(ValidationError):
        target[0][0] = 1.5


def test_union_narrowing_preserves_supplied_flags() -> None:
    source = OmegaConf.typed_tuple((1,), tuple[int | str])._get_node(0)
    assert isinstance(source, Node)
    source._set_flag("readonly", True)
    target = OmegaConf.typed_tuple((source,), tuple[int])
    assert isinstance(target._get_node(0), IntegerNode)
    node = target._get_node(0)
    assert isinstance(node, IntegerNode)
    assert node._metadata.flags == {"convert": False, "readonly": True}


@mark.parametrize("shape", ["list", "dict", "dict-new-key"])
@mark.parametrize("wrapped", [True, False])
@mark.parametrize("replace", [True, False])
@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_nested_assignment_converts_supplied_numeric_nodes(
    shape: str, wrapped: bool, replace: bool
) -> None:
    source_node = IntegerNode(789)
    if shape == "list":
        target = DictConfig({"value": [[1.0]]}, element_type=list[list[float]])
        source: Any = [[source_node]]
    else:
        target = DictConfig(
            {"value": {"child": {"old": 1.0}}},
            element_type=dict[str, dict[str, float]],
        )
        source = {"child": {"old" if shape == "dict" else "new": source_node}}
    if not replace:
        del target["value"]
    if wrapped:
        source = OmegaConf.create(source)
    target["value"] = source
    result = (
        target["value"][0][0]
        if shape == "list"
        else next(iter(target["value"]["child"].values()))
    )
    assert result == 789.0
    assert type(result) is float
    assert source_node._value() == 789


@mark.parametrize("source", [IntegerNode(None), AnyNode("bad")])
def test_type_hint_narrowing_rejects_incompatible_scalar(source: Node) -> None:
    with raises(ValidationError):
        _deep_update_type_hint(source, int)


def test_type_hint_narrowing_rejects_incompatible_dictionary_keys() -> None:
    source = OmegaConf.create({1: 2})
    with raises(KeyValidationError):
        _deep_update_type_hint(source, dict[str, int])


def test_type_hint_narrowing_retains_matching_literal_validator() -> None:
    source = OmegaConf.typed_tuple(("red",), tuple[Literal["red", "blue"]])
    node = source._get_node(0)
    assert isinstance(node, Node)
    _deep_update_type_hint(node, Literal["red", "blue"])
    with raises(ValidationError):
        node._set_value("green")


def test_strict_assignment_uses_selected_union_container() -> None:
    from omegaconf._validation_context import _schema_validation
    from omegaconf.base import UnionNode

    target = OmegaConf.create({"value": [0]})
    source = UnionNode([1], ref_type=list[int] | str)
    token = _schema_validation.set(True)
    try:
        target["value"] = source
    finally:
        _schema_validation.reset(token)
    assert target["value"] == [1]


def test_structured_mapping_retains_nested_field_defaults() -> None:
    @dataclass
    class Child:
        count: int = 1
        label: str = "default"

    @dataclass
    class Parent:
        child: Child = field(default_factory=lambda: Child(count=7))

    result = DictConfig({"child": {"label": "supplied"}}, ref_type=Parent)
    assert OmegaConf.to_object(result) == Parent(child=Child(count=7, label="supplied"))


@mark.parametrize("shape", ["list", "dict", "tuple"])
def test_declared_frozen_schema_cannot_be_disabled_by_source_flags(shape: str) -> None:
    @dataclass(frozen=True)
    class Frozen:
        count: int = 1

    source = DictConfig(Frozen, ref_type=Frozen)
    source._set_flag("readonly", False)
    if shape == "list":
        result = OmegaConf.typed_list([source], Frozen)[0]
    elif shape == "dict":
        result = OmegaConf.typed_dict({"value": source}, str, Frozen)["value"]
    else:
        result = OmegaConf.typed_tuple((source,), tuple[Frozen])[0]
    with raises(ReadonlyConfigError):
        result.count = 2
    assert source._get_flag("readonly") is False


@mark.parametrize("shape", ["list", "dict", "tuple"])
@mark.parametrize("operation", ["construct", "merge"])
@mark.parametrize("source_kind", ["raw", "wrapped", "typed"])
def test_structured_mapping_retains_nested_dictionary_defaults(
    shape: str, operation: str, source_kind: str
) -> None:
    @dataclass
    class Schema:
        settings: Dict[str, Dict[str, int]] = field(
            default_factory=lambda: {"child": {"a": 1, "b": 2}, "other": {"c": 3}}
        )

    supplied: Any = {"settings": {"child": {"a": "5"}}}
    if source_kind == "wrapped":
        supplied = OmegaConf.create(supplied)
    elif source_kind == "typed":
        supplied = {
            "settings": OmegaConf.typed_dict({"child": {"a": 5}}, str, Dict[str, int])
        }
    if shape == "list":
        result = (
            OmegaConf.typed_list([supplied], Schema)
            if operation == "construct"
            else OmegaConf.merge(OmegaConf.typed_list([], Schema), [supplied])
        )[0]
    elif shape == "dict":
        container: Any = (
            OmegaConf.typed_dict({"value": supplied}, str, Schema)
            if operation == "construct"
            else OmegaConf.merge(
                OmegaConf.typed_dict({}, str, Schema), {"value": supplied}
            )
        )
        result = container["value"]
    else:
        result = (
            OmegaConf.typed_tuple((supplied,), tuple[Schema])
            if operation == "construct"
            else OmegaConf.merge(
                OmegaConf.typed_tuple((Schema(),), tuple[Schema]), (supplied,)
            )
        )[0]
    assert OmegaConf.to_object(result) == Schema(
        settings={"child": {"a": 5, "b": 2}, "other": {"c": 3}}
    )


@mark.parametrize("wrapped", [True, False])
@mark.parametrize("typed", [True, False])
def test_structured_mapping_retains_untyped_dictionary_defaults(
    wrapped: bool, typed: bool
) -> None:
    @dataclass
    class Schema:
        settings: Any = field(default_factory=lambda: {"a": 1, "b": 2})

    supplied: Any = {"settings": {"a": 3}}
    if typed:
        supplied = {"settings": OmegaConf.typed_dict({"a": 3}, str, int)}
    if wrapped:
        supplied = OmegaConf.create(supplied)
    result = OmegaConf.merge(OmegaConf.typed_list([], Schema), [supplied])[0]
    assert OmegaConf.to_object(result) == Schema(settings={"a": 3, "b": 2})
    if typed:
        settings = result.settings
        assert settings._metadata.key_type is str
        assert settings._metadata.element_type is int
        with raises(ValidationError):
            settings["new"] = "bad"


def test_structured_mapping_honors_explicit_open_schema() -> None:
    @dataclass
    class Schema:
        count: int = 1

    result = DictConfig({"extra": 2}, ref_type=Schema, flags={"struct": False})
    assert result.extra == 2


@mark.parametrize("wrapped", [False, True])
@mark.parametrize("operation", ["direct", "list-merge", "dict-merge", "tuple"])
def test_structured_mapping_missing_values_retain_defaults(
    wrapped: bool, operation: str
) -> None:
    @dataclass
    class Schema:
        count: int = 1
        settings: dict[str, int] = field(default_factory=lambda: {"a": 2})
        required: int = MISSING

    supplied: Any = {"count": MISSING, "settings": {"a": MISSING}}
    if wrapped:
        supplied = OmegaConf.create(supplied)
    result: Any
    if operation == "direct":
        result = DictConfig(supplied, ref_type=Schema)
    elif operation == "list-merge":
        result = OmegaConf.merge(OmegaConf.typed_list([], Schema), [supplied])[0]
    elif operation == "dict-merge":
        container: Any = OmegaConf.merge(
            OmegaConf.typed_dict({}, str, Schema), {"value": supplied}
        )
        result = container["value"]
    else:
        result = OmegaConf.typed_tuple((supplied,), tuple[Schema])[0]
    assert result.count == 1
    assert result.settings.a == 2
    assert OmegaConf.is_missing(result, "required")


def _child_type(calls: list[str], fail: bool = False) -> type[Any]:
    def factory() -> int:
        calls.append("factory")
        if fail:
            raise RuntimeError("supplied structured values must not run defaults")
        return 9

    @dataclass
    class Child:
        count: int = 1
        generated: int = field(default_factory=factory)

    return Child


@mark.parametrize("shape", ["list", "dict"])
def test_typed_containers_construct_assign_and_replace_mappings(shape: str) -> None:
    calls: list[str] = []
    Child = _child_type(calls)
    source = {"count": "5"}

    if shape == "list":
        cfg = OmegaConf.typed_list([source], element_type=Child)
        first = cfg._get_node(0)
        assert isinstance(first, DictConfig)
        assert first.count == 5
        assert first.generated == 9
        assert calls == ["factory"]
        source["count"] = "99"
        assert first.count == 5

        cfg.append({"count": 6})
        cfg[0] = {"count": 7}
        assert cfg[0].count == 7
        assert cfg[1].count == 6
        assert cfg[0].generated == cfg[1].generated == 9
    else:
        cfg = OmegaConf.typed_dict({"first": source}, str, Child)
        first = cfg._get_node("first")
        assert isinstance(first, DictConfig)
        assert first.count == 5
        assert first.generated == 9
        assert calls == ["factory"]
        source["count"] = "99"
        assert first.count == 5

        cfg["second"] = {"count": 6}
        cfg["first"] = {"count": 7}
        assert cfg["first"].count == 7
        assert cfg["second"].count == 6
        assert cfg["first"].generated == cfg["second"].generated == 9

    assert calls == ["factory", "factory", "factory"]


@mark.parametrize("shape", ["list", "dict"])
def test_typed_container_merge_constructs_raw_mappings(shape: str) -> None:
    calls: list[str] = []
    Child = _child_type(calls)

    if shape == "list":
        cfg = OmegaConf.merge(OmegaConf.typed_list([], Child), [{"count": "5"}])
        child = cfg._get_node(0)
    else:
        cfg = OmegaConf.merge(
            OmegaConf.typed_dict({}, str, Child), {"child": {"count": "5"}}
        )
        child = cast(DictConfig, cfg)._get_node("child")

    assert isinstance(child, DictConfig)
    assert child.count == 5
    assert child.generated == 9
    assert calls == ["factory"]


@mark.parametrize("shape", ["list", "dict"])
@mark.parametrize("operation", ["construct", "insert", "merge"])
def test_typed_container_mapping_promotion_preserves_flags(
    shape: str, operation: str
) -> None:
    @dataclass
    class Child:
        count: int = 1
        extra: int = 2

    source = OmegaConf.create({"count": 5})
    flags = {"readonly": True, "convert": False}
    source._set_flag(list(flags), list(flags.values()))

    if shape == "list":
        if operation == "construct":
            result = OmegaConf.typed_list([source], Child)
        elif operation == "insert":
            result = OmegaConf.typed_list([], Child)
            result.append(source)
        else:
            target = OmegaConf.typed_list([], Child)
            result = OmegaConf.merge(target, OmegaConf.create([source]))
        child = result._get_node(0)
    else:
        if operation == "construct":
            result = OmegaConf.typed_dict({"child": source}, str, Child)
        elif operation == "insert":
            result = OmegaConf.typed_dict({}, str, Child)
            result["child"] = source
        else:
            target = OmegaConf.typed_dict({}, str, Child)
            result = OmegaConf.merge(target, OmegaConf.create({"child": source}))
        child = cast(DictConfig, result)._get_node("child")

    assert isinstance(child, DictConfig)
    assert child._metadata.object_type is Child
    assert child._metadata.flags == flags
    assert child.count == 5
    assert child.extra == 2
    assert OmegaConf.is_readonly(child) is True
    assert child._get_parent() is result
    assert source._metadata.flags == flags
    assert source.count == 5
    assert source._get_parent() is None
    with raises(ReadonlyConfigError):
        child.count = 6


@mark.parametrize("shape", ["list", "dict"])
@mark.parametrize("operation", ["construct", "insert", "merge"])
def test_typed_container_mapping_promotion_respects_convert_false(
    shape: str, operation: str
) -> None:
    @dataclass
    class Child:
        count: int = 1

    source = OmegaConf.create({"count": "5"})
    source._set_flag("convert", False)

    if shape == "list":
        target = OmegaConf.typed_list([], Child)
        if operation == "construct":
            with raises(ValidationError):
                OmegaConf.typed_list([source], Child)
        elif operation == "insert":
            with raises(ValidationError):
                target.append(source)
        else:
            with raises(ValidationError):
                OmegaConf.merge(target, OmegaConf.create([source]))
        assert len(target) == 0
    else:
        target = OmegaConf.typed_dict({}, str, Child)
        if operation == "construct":
            with raises(ValidationError):
                OmegaConf.typed_dict({"child": source}, str, Child)
        elif operation == "insert":
            with raises(ValidationError):
                target["child"] = source
        else:
            with raises(ValidationError):
                OmegaConf.merge(target, OmegaConf.create({"child": source}))
        assert len(target) == 0

    assert source.count == "5"
    assert source._metadata.flags == {"convert": False}
    assert source._get_parent() is None


@mark.parametrize("shape", ["list", "dict"])
def test_typed_container_merge_does_not_run_unused_factories(shape: str) -> None:
    calls: list[str] = []
    Child = _child_type(calls, fail=True)
    supplied = Child(count=3, generated=4)

    if shape == "list":
        target = OmegaConf.typed_list([], Child)
        result = OmegaConf.merge(target, OmegaConf.create([supplied]))
        assert result[0].count == 3
        assert result[0].generated == 4
        result = OmegaConf.merge(result, OmegaConf.typed_list([], Child))
        assert len(result) == 0
    else:
        target = OmegaConf.typed_dict({}, str, Child)
        result = cast(
            DictConfig, OmegaConf.merge(target, OmegaConf.create({"child": supplied}))
        )
        assert result["child"].count == 3
        assert result["child"].generated == 4
        result = OmegaConf.merge(result, OmegaConf.typed_dict({}, str, Child))
        assert len(result) == 1

    assert calls == []


@mark.parametrize("shape", ["list", "dict"])
def test_typed_container_constructs_frozen_structured_mappings(shape: str) -> None:
    @dataclass(frozen=True)
    class FrozenChild:
        count: int = 1

    if shape == "list":
        cfg = OmegaConf.typed_list([{"count": "5"}], FrozenChild)
        child = cfg._get_node(0)
    else:
        cfg = OmegaConf.typed_dict({"child": {"count": "5"}}, str, FrozenChild)
        child = cfg._get_node("child")

    assert isinstance(child, DictConfig)
    assert child.count == 5
    assert OmegaConf.is_readonly(child) is True
    with raises(ReadonlyConfigError):
        child.count = 6


@mark.parametrize("shape", ["list", "dict"])
def test_typed_containers_construct_and_assign_attrs_mappings(shape: str) -> None:
    calls: list[str] = []

    def factory() -> int:
        calls.append("factory")
        return 9

    @attr.define
    class Child:
        count: int = 1
        generated: int = attr.field(factory=factory)

    if shape == "list":
        cfg = OmegaConf.typed_list([{"count": "5"}], Child)
        cfg.append({"count": 6})
        cfg[0] = {"count": 7}
        assert cfg[0].count == 7
        assert cfg[1].count == 6
        assert cfg[0].generated == cfg[1].generated == 9
        child = cfg._get_node(0)
    else:
        cfg = OmegaConf.typed_dict({"first": {"count": "5"}}, str, Child)
        cfg["second"] = {"count": 6}
        cfg["first"] = {"count": 7}
        assert cfg["first"].count == 7
        assert cfg["second"].count == 6
        assert cfg["first"].generated == cfg["second"].generated == 9
        child = cfg._get_node("first")

    assert isinstance(child, DictConfig)
    assert OmegaConf.get_type(child) is Child
    assert calls == ["factory", "factory", "factory"]


@mark.parametrize("shape", ["list", "dict"])
def test_structured_mapping_replacement_preserves_destination_flags(
    shape: str,
) -> None:
    @dataclass
    class Child:
        count: int = 1

    cfg: Any
    key: Any
    if shape == "list":
        cfg = OmegaConf.typed_list([Child()], Child)
        key = 0
    else:
        cfg = OmegaConf.typed_dict({"child": Child()}, str, Child)
        key = "child"

    cfg_any = cast(Any, cfg)
    child = cfg_any._get_node(key)
    assert isinstance(child, DictConfig)
    child._set_flag("convert", False)
    with raises(ValidationError):
        cfg_any[key] = {"count": "5"}
    assert cfg_any[key].count == 1
    assert cfg_any._get_node(key) is child

    cfg_any[key] = {"count": 6}
    replacement = cfg_any._get_node(key)
    assert isinstance(replacement, DictConfig)
    assert replacement._metadata.flags == {"convert": False}
    replacement._set_flag("readonly", True)

    cfg_any[key] = {"count": 7}
    replacement = cfg_any._get_node(key)
    assert isinstance(replacement, DictConfig)
    assert replacement._metadata.flags == {"convert": False, "readonly": True}
    assert replacement.count == 7
    with raises(ReadonlyConfigError):
        replacement.count = 8


@mark.parametrize("shape", ["list", "dict"])
def test_typed_containers_construct_frozen_attrs_mappings(shape: str) -> None:
    @attr.frozen
    class FrozenChild:
        count: int = 1

    if shape == "list":
        cfg = OmegaConf.typed_list([{"count": "5"}], FrozenChild)
        child = cfg._get_node(0)
    else:
        cfg = OmegaConf.typed_dict({"child": {"count": "5"}}, str, FrozenChild)
        child = cfg._get_node("child")

    assert isinstance(child, DictConfig)
    assert child.count == 5
    assert OmegaConf.is_readonly(child) is True
    with raises(ReadonlyConfigError):
        child.count = 6


@mark.parametrize("shape", ["list", "dict"])
def test_typed_containers_promote_raw_dictconfig_to_frozen_structured_type(
    shape: str,
) -> None:
    @dataclass(frozen=True)
    class FrozenChild:
        count: int = 1
        label: str = "default"

    source = OmegaConf.create({"count": "5"})
    if shape == "list":
        cfg = OmegaConf.typed_list([source], FrozenChild)
        child = cfg._get_node(0)
        key = 0
    else:
        cfg = OmegaConf.typed_dict({"child": source}, str, FrozenChild)
        child = cast(DictConfig, cfg)._get_node("child")
        key = "child"

    assert isinstance(child, DictConfig)
    assert OmegaConf.get_type(child) is FrozenChild
    assert child.count == 5
    assert child.label == "default"
    assert OmegaConf.is_readonly(child) is True
    assert child._get_parent() is cfg
    assert child._key() == key
    with raises(ReadonlyConfigError):
        child.count = 6

    assert OmegaConf.get_type(source) is dict
    assert source.count == "5"
    assert source._get_parent() is None


def test_typed_dict_rejects_unrelated_structured_node() -> None:
    @dataclass
    class Child:
        count: int = 1

    @dataclass
    class Other:
        count: int = 2

    source = OmegaConf.structured(Other(count=3))
    target = OmegaConf.typed_dict({}, str, Child)

    with raises(ValidationError, match="not a subclass"):
        target["child"] = source

    assert len(target) == 0
    assert OmegaConf.get_type(source) is Other
    assert source.count == 3
    assert source._get_parent() is None


@mark.parametrize("shape", ["list", "dict"])
def test_typed_container_preserves_structured_validation(shape: str) -> None:
    @dataclass
    class Child:
        count: int = MISSING

    if shape == "list":
        cfg = OmegaConf.typed_list([{}], Child)
        child = cfg[0]
        with raises(ValidationError):
            OmegaConf.typed_list([{"count": "bad"}], Child)
        with raises((ConfigKeyError, ValidationError)):
            OmegaConf.typed_list([{"count": 1, "unknown": 2}], Child)
    else:
        cfg = OmegaConf.typed_dict({"child": {}}, str, Child)
        child = cfg["child"]
        with raises(ValidationError):
            OmegaConf.typed_dict({"child": {"count": "bad"}}, str, Child)
        with raises((ConfigKeyError, ValidationError)):
            OmegaConf.typed_dict({"child": {"count": 1, "unknown": 2}}, str, Child)

    with raises(MissingMandatoryValue):
        _ = child.count


def test_typed_dict_normalizes_enum_keys_for_structured_values() -> None:
    calls: list[str] = []
    Child = _child_type(calls)

    class Color(Enum):
        RED = 1

    source = {"RED": {"count": "5"}}
    cfg = OmegaConf.typed_dict(source, Color, Child)

    assert list(cfg) == [Color.RED]
    assert cfg[Color.RED].count == 5
    assert cfg[Color.RED].generated == 9
    assert source == {"RED": {"count": "5"}}


def test_structured_field_assignment_preserves_declared_schema_for_mappings() -> None:
    @dataclass
    class Child:
        count: int = 1
        label: str = "default"

    @dataclass
    class Parent:
        child: Child = field(default_factory=Child)

    cfg = OmegaConf.structured(Parent)
    before = OmegaConf.to_object(cfg)

    with raises(ValidationError):
        cfg.child = {"count": "bad"}

    assert OmegaConf.to_object(cfg) == before

    cfg.child = {"count": 5}
    assert OmegaConf.get_type(cfg.child) is Child
    result = cast(Parent, OmegaConf.to_object(cfg))
    assert result.child == Child(count=5, label="default")
