from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

import attr
from pytest import mark, raises

from omegaconf import MISSING, DictConfig, MissingMandatoryValue, OmegaConf
from omegaconf.errors import ConfigKeyError, ReadonlyConfigError, ValidationError


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
