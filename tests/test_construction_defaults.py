from dataclasses import dataclass, field, make_dataclass
from typing import Any, cast

import attr
from pytest import mark, raises

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf.base import Node, UnionNode
from omegaconf.errors import (
    ConfigKeyError,
    KeyValidationError,
    ReadonlyConfigError,
    ValidationError,
)
from omegaconf.nodes import IntegerNode
from omegaconf.omegaconf import _node_wrap


@mark.parametrize("kind", ["dataclass", "attrs"])
@mark.filterwarnings("ignore:.*Subclassing.*:UserWarning")
def test_structured_dictionary_instance_retains_fields(kind: str) -> None:
    @dataclass
    class DataclassChild(dict):
        count: int = 1

    @attr.s(auto_attribs=True)
    class AttrsChild(dict):
        count: int = 1

    schema = DataclassChild if kind == "dataclass" else AttrsChild
    source = schema(count=8)
    assert DictConfig(source, ref_type=schema).count == 8
    assert source.count == 8


@mark.parametrize("operation", ["assign", "set-value"])
def test_dictionary_subclass_failure_preserves_existing_child(operation: str) -> None:
    class Patch(dict):
        pass

    @dataclass
    class Child:
        a: int = 1
        b: int = 2

    @dataclass
    class Parent:
        child: Child = field(default_factory=Child)

    cfg = OmegaConf.structured(Parent)
    original = cfg.child
    with raises(ValidationError):
        if operation == "assign":
            cfg.child = Patch(a=7, b="bad")
        else:
            original._set_value(Patch(a=7, b="bad"))
    assert cfg.child is original
    assert OmegaConf.to_container(original) == {"a": 1, "b": 2}

    cfg.child = Patch(a=7)
    assert OmegaConf.to_container(cfg.child) == {"a": 7, "b": 2}


@mark.parametrize("source_override", [True, False])
def test_nested_dictionary_defaults_enforce_struct_policy(
    source_override: bool,
) -> None:
    default = OmegaConf.create({"known": 1}, flags={"struct": True})
    Schema = make_dataclass(
        "Schema", [("settings", Any, field(default_factory=lambda: default))]
    )
    source: Any = {"new": 2}
    if source_override:
        source = OmegaConf.create(source, flags={"struct": False})
        result = DictConfig({"settings": source}, ref_type=Schema)
        assert result.settings == {"known": 1, "new": 2}
        assert OmegaConf.is_struct(result.settings) is False
    else:
        with raises(ConfigKeyError):
            DictConfig({"settings": source}, ref_type=Schema)
    assert default == {"known": 1}
    assert OmegaConf.is_struct(default) is True


@mark.parametrize("shape", ["list", "dict"])
@mark.parametrize("invalid", [True, False])
def test_copy_requires_destination_container_metadata(
    shape: str, invalid: bool
) -> None:
    value: Any = "bad" if invalid else 3
    source = (
        DictConfig({"a": value}, ref_type=dict[str, int])
        if shape == "dict"
        else ListConfig([value], ref_type=list[int])
    )
    annotation = dict[str, int] if shape == "dict" else list[int]
    assert source._metadata.element_type is Any
    if invalid:
        with raises(ValidationError):
            OmegaConf.typed_list([source], annotation)
    else:
        result = OmegaConf.typed_list([source], annotation)[0]
        assert result._metadata.element_type is int
        with raises(ValidationError):
            result["a" if shape == "dict" else 0] = "bad"
    assert source._metadata.element_type is Any


@mark.parametrize("replacement", [3, MISSING, None])
def test_select_dictionary_value_before_typed_default_validation(
    replacement: Any,
) -> None:
    @dataclass
    class Schema:
        settings: Any = field(default_factory=lambda: {"a": "bad", "b": 2})

    source = OmegaConf.typed_dict(
        {} if replacement is None else {"a": replacement}, str, int
    )
    if replacement is None or replacement == MISSING:
        with raises(ValidationError):
            DictConfig({"settings": source}, ref_type=Schema)
    else:
        result = DictConfig({"settings": source}, ref_type=Schema)
        assert result.settings == {"a": 3, "b": 2}
        assert result.settings._metadata.key_type is str
        assert result.settings._metadata.element_type is int
    assert OmegaConf.to_container(source) == (
        {} if replacement is None else {"a": replacement}
    )


def test_staged_mapping_rejects_new_ambiguous_keys() -> None:
    @dataclass
    class Schema:
        settings: Any = field(default_factory=dict)

    for supplied in [{1: "a", "1": "b"}, {"1": "b", 1: "a"}]:
        with raises(KeyValidationError):
            DictConfig({"settings": supplied}, ref_type=Schema)


def _default_node(shape: str) -> tuple[Node, Any]:
    if shape == "list":
        return OmegaConf.typed_list([1], int), list[int]
    if shape == "tuple":
        return OmegaConf.typed_tuple((1,), tuple[int]), tuple[int]
    return IntegerNode(1), int


@mark.parametrize("shape", ["list", "tuple", "scalar"])
@mark.parametrize("source_override", [True, False])
def test_default_node_flags_precede_replacement_validation(
    shape: str, source_override: bool
) -> None:
    default, annotation = _default_node(shape)
    default._set_flag(["readonly", "convert"], [True, False])
    Schema = make_dataclass(
        "Schema", [("payload", annotation, field(default_factory=lambda: default))]
    )
    source: Any = [5] if shape == "list" else (5,) if shape == "tuple" else 5
    if source_override:
        source, _ = _default_node(shape)
        source._set_flag(["readonly", "convert"], [False, True])
    result = DictConfig({"payload": source}, ref_type=Schema)
    node = result._get_node("payload")
    assert isinstance(node, Node)
    assert node._get_flag("readonly") is not source_override
    assert node._get_flag("convert") is source_override
    assert default._metadata.flags == {"readonly": True, "convert": False}
    if not source_override:
        bad: Any = ["5"] if shape == "list" else ("5",) if shape == "tuple" else "5"
        with raises(ValidationError):
            DictConfig({"payload": bad}, ref_type=Schema)


@mark.parametrize("operation", ["construct", "merge"])
def test_partial_mapping_retains_selected_union_defaults(operation: str) -> None:
    @dataclass
    class Child:
        count: int = 1
        label: str = "default"

    @dataclass
    class Parent:
        child: Child | int = field(default_factory=lambda: Child(count=10))

    supplied = {"child": {"label": "supplied"}}
    result = (
        DictConfig(supplied, ref_type=Parent)
        if operation == "construct"
        else OmegaConf.merge(OmegaConf.typed_list([], Parent), [supplied])[0]
    )
    assert result.child.count == 10
    assert result.child.label == "supplied"
    assert DictConfig({"child": 7}, ref_type=Parent).child == 7
    concrete = DictConfig({"child": Child(count=8)}, ref_type=Parent)
    assert concrete.child.count == 8
    assert concrete.child.label == "default"


@mark.parametrize("source_readonly", [None, True, False])
def test_union_wrapper_defaults_do_not_override_selected_policy(
    source_readonly: bool | None,
) -> None:
    @dataclass
    class Child:
        count: int = 1
        label: str = "default"

    default = UnionNode(Child(count=10), ref_type=Child | int)
    default._set_flag("readonly", False)
    selected_default = default._value()
    assert isinstance(selected_default, DictConfig)
    selected_default._set_flag("readonly", True)

    @dataclass
    class Parent:
        child: Child | int = field(default_factory=lambda: cast(Any, default))

    source: Any = {"label": "supplied"}
    if source_readonly is not None:
        source = OmegaConf.create(source, flags={"readonly": source_readonly})
    result = DictConfig({"child": source}, ref_type=Parent)
    assert result.child.count == 10
    assert OmegaConf.is_readonly(result.child) is (source_readonly is not False)
    if source_readonly is False:
        result.child.count = 12
    else:
        with raises(ReadonlyConfigError):
            result.child.count = 12
    assert default._metadata.flags == {"convert": False, "readonly": False}
    assert selected_default._get_flag("readonly") is True
    assert selected_default.count == 10


def _union_value(shape: str, value: Any) -> tuple[Node, Any, Any]:
    if shape == "list":
        return OmegaConf.typed_list([value], type(value)), list[int] | str, [value]
    if shape == "tuple":
        return (
            OmegaConf.typed_tuple((value,), tuple[type(value)]),
            tuple[int] | str,
            (value,),
        )
    if shape == "dict":
        return (
            OmegaConf.typed_dict({"a": value}, str, type(value)),
            dict[str, int] | str,
            {"a": value},
        )
    return IntegerNode(value), int | str, value


@mark.parametrize("shape", ["scalar", "list", "tuple", "dict"])
@mark.parametrize("override", [None, True, False])
@mark.parametrize("mode", ["source", "caller"])
def test_union_default_policy_and_overrides_across_branches(
    shape: str, override: bool | None, mode: str
) -> None:
    _, annotation, default_value = _union_value(shape, 1)
    default = UnionNode(default_value, ref_type=annotation)
    default._set_flag("readonly", False)
    selected_default = default._value()
    assert isinstance(selected_default, Node)
    selected_default._set_flag("readonly", True)
    source, _, native = _union_value(shape, 5)
    flags = None if override is None else {"readonly": override}
    if mode == "source":
        if override is not None:
            source._set_flag("readonly", override)
        Schema = make_dataclass(
            "Schema", [("payload", annotation, field(default_factory=lambda: default))]
        )
        node = DictConfig({"payload": source}, ref_type=Schema)._get_node("payload")
    else:
        node = _node_wrap(
            parent=None,
            is_optional=False,
            value=native,
            key=None,
            ref_type=annotation,
            flags=flags,
            defaults=default,
        )
    assert isinstance(node, UnionNode)
    selected = node._value()
    assert isinstance(selected, Node)
    assert selected._get_flag("readonly") is (override is not False)
    assert selected._get_flag("convert") is False
    assert selected_default._get_flag("readonly") is True


@mark.parametrize("shape", ["list", "tuple", "dict"])
def test_source_cannot_enable_union_container_conversion(shape: str) -> None:
    source, annotation, _ = _union_value(shape, "5")
    source._set_flag("convert", True)
    with raises(ValidationError):
        OmegaConf.typed_tuple((source,), tuple[annotation])
