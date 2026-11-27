import copy
from dataclasses import dataclass, field, make_dataclass
from enum import Enum
from typing import Any, Literal

import attr
import pytest

from omegaconf import MISSING, Node, OmegaConf, TupleConfig, UnionNode
from omegaconf.errors import (
    ConfigKeyError,
    KeyValidationError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    ValidationError,
)


@dataclass
class Child:
    count: int = MISSING
    label: str = "default"


@dataclass(frozen=True)
class FrozenChild:
    count: int = MISSING
    label: str = "default"


@attr.define
class AttrChild:
    count: int = MISSING
    label: str = "default"


@attr.define(frozen=True)
class FrozenAttrChild:
    count: int = MISSING
    label: str = "default"


class TupleKey(Enum):
    A = 1


def nested(shape: str, annotation: Any, value: Any) -> tuple[Any, Any]:
    if shape == "list":
        return list[annotation], [value]
    if shape == "dict":
        return dict[str, annotation], {"child": value}
    return annotation, value


@pytest.mark.parametrize("child", [Child, FrozenChild, AttrChild, FrozenAttrChild])
@pytest.mark.parametrize("shape", ["direct", "list", "dict"])
@pytest.mark.parametrize("source_node", [False, True])
def test_tuple_constructs_structured_children(
    child: Any, shape: str, source_node: bool
) -> None:
    annotation, value = nested(shape, child, {"count": "5"})
    _, expected = nested(shape, child, child(count=5))
    source = OmegaConf.create((value,)) if source_node else (value,)
    original = copy.deepcopy(source)

    cfg = OmegaConf.typed_tuple(source, tuple[annotation])

    assert OmegaConf.to_object(cfg) == (expected,)
    assert source == original
    leaf = cfg[0]
    if shape == "list":
        leaf = leaf[0]
    elif shape == "dict":
        leaf = leaf["child"]
    assert OmegaConf.is_readonly(leaf) is (
        True if child in (FrozenChild, FrozenAttrChild) else None
    )


@pytest.mark.parametrize(
    "annotation,value",
    [
        (list[int], ["bad"]),
        (dict[str, int], {"child": "bad"}),
        (Child, {"count": "bad"}),
        (list[Child], [{"count": "bad"}]),
        (dict[str, Child], {"child": {"count": "bad"}}),
    ],
)
def test_tuple_rejects_invalid_container_children(annotation: Any, value: Any) -> None:
    source = OmegaConf.create((value,))
    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple(source, tuple[annotation])
    assert OmegaConf.to_container(source) == (value,)


def test_tuple_structured_fields_use_schema_validation() -> None:
    schema = make_dataclass(
        "Schema", [("payload", tuple[list[Child], dict[str, Child]])]
    )
    cfg = OmegaConf.merge(
        OmegaConf.structured(schema),
        {"payload": ([{"count": "5"}], {"child": {"count": "6"}})},
    )
    result: Any = OmegaConf.to_object(cfg)
    assert result.payload == ([Child(count=5)], {"child": Child(count=6)})
    with pytest.raises(ConfigKeyError):
        OmegaConf.typed_tuple(({"count": 5, "unknown": 1},), tuple[Child])
    cfg = OmegaConf.typed_tuple(({},), tuple[Child])
    with pytest.raises(MissingMandatoryValue):
        OmegaConf.to_object(cfg)


@pytest.mark.parametrize("operation", ["copy", "slice", "multiply", "concatenate"])
def test_tuple_copies_keep_flags_and_do_not_rerun_factories(operation: str) -> None:
    calls = []

    def factory() -> list[int]:
        calls.append(True)
        return [1]

    schema = make_dataclass(
        "WithFactory", [("values", list[int], field(default_factory=factory))]
    )
    cfg = OmegaConf.typed_tuple((schema(values=[2]),), tuple[schema])
    OmegaConf.set_readonly(cfg[0], True)
    OmegaConf.set_struct(cfg[0], True)
    result = {
        "copy": lambda: copy.copy(cfg),
        "slice": lambda: cfg[:],
        "multiply": lambda: cfg * 2,
        "concatenate": lambda: cfg + cfg,
    }[operation]()
    assert calls == []
    for item in result:
        assert OmegaConf.is_readonly(item) is True
        assert OmegaConf.is_struct(item) is True
        assert item["values"] == [2]


@pytest.mark.parametrize("special", [None, "${value}"])
def test_tuple_preserves_special_container_flags(special: Any) -> None:
    child = TupleConfig(special, ref_type=tuple[int, ...], flags={"readonly": True})
    cfg = OmegaConf.typed_tuple((child,), tuple[tuple[int, ...] | None])
    node = cfg._get_node(0)
    assert isinstance(node, TupleConfig)
    assert node._metadata.flags == child._metadata.flags
    assert node._value() == child._value()


@pytest.mark.parametrize("convert", [True, False])
def test_tuple_retyping_preserves_leaf_flags(convert: bool) -> None:
    source = OmegaConf.create((["5"],))
    leaf = source[0]._get_node(0)
    leaf._set_flag(["readonly", "convert"], [True, convert])
    if not convert:
        with pytest.raises(ValidationError):
            OmegaConf.typed_tuple(source, tuple[list[int]])
    else:
        cfg = OmegaConf.typed_tuple(source, tuple[list[int]])
        converted = cfg[0]._get_node(0)
        assert converted._value() == 5
        assert converted._metadata.flags == leaf._metadata.flags
    assert leaf._value() == "5"
    assert leaf._get_flag("convert") is convert


def test_tuple_rejects_unrelated_structured_node() -> None:
    unrelated = make_dataclass("Unrelated", [("count", int, 5)])
    source = OmegaConf.structured(unrelated)
    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple((source,), tuple[Child])


@pytest.mark.parametrize("special", [None, "${value}"])
def test_tuple_retypes_special_source_container(special: Any) -> None:
    source = TupleConfig(special, flags={"readonly": True})
    cfg = OmegaConf.typed_tuple((source,), tuple[tuple[int] | None])
    child = cfg._get_node(0)
    assert isinstance(child, TupleConfig)
    assert child._value() == special
    assert child._get_flag("readonly") is True


def test_tuple_honors_structured_source_conversion_policy() -> None:
    source = OmegaConf.create({"count": "5"})
    source._set_flag("convert", False)
    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple((source,), tuple[Child])


def test_tuple_accepts_valid_containers_without_conversion() -> None:
    cfg = TupleConfig(([5],), ref_type=tuple[list[int]], flags={"convert": False})
    assert cfg[0] == [5]
    with pytest.raises(ValidationError):
        TupleConfig((["5"],), ref_type=tuple[list[int]], flags={"convert": False})


@pytest.mark.parametrize("source_node", [False, True])
@pytest.mark.parametrize(
    "annotation,value,expected",
    [(list[int], (1, 2), [1, 2]), (tuple[int, int], [1, 2], (1, 2))],
)
def test_tuple_keeps_nested_sequence_conversions(
    source_node: bool, annotation: Any, value: Any, expected: Any
) -> None:
    source = OmegaConf.create((value,)) if source_node else (value,)
    assert OmegaConf.to_object(OmegaConf.typed_tuple(source, tuple[annotation])) == (
        expected,
    )


@pytest.mark.parametrize("source_node", [False, True])
@pytest.mark.parametrize(
    "annotation,source,expected",
    [
        (list[tuple[int, int]], [[1, 2]], [(1, 2)]),
        (list[list[int]], [(1, 2)], [[1, 2]]),
        (dict[str, tuple[int, int]], {"a": [1, 2]}, {"a": (1, 2)}),
    ],
)
def test_tuple_keeps_recursive_nested_sequence_conversions(
    source_node: bool, annotation: Any, source: Any, expected: Any
) -> None:
    source = (source,)
    input_value = OmegaConf.create(source) if source_node else source
    original = copy.deepcopy(input_value)

    cfg = OmegaConf.typed_tuple(input_value, tuple[annotation])

    assert OmegaConf.to_object(cfg) == (expected,)
    if source_node:
        assert OmegaConf.to_container(input_value) == OmegaConf.to_container(original)
    else:
        assert input_value == original


@pytest.mark.parametrize("source_node", [False, True])
@pytest.mark.parametrize(
    "annotation,source",
    [
        (list[tuple[int, int]], [[1, "bad"]]),
        (list[list[int]], [(1, "bad")]),
        (dict[str, tuple[int, int]], {"a": [1, "bad"]}),
    ],
)
def test_tuple_rejects_bad_recursive_sequence_values_without_mutating_source(
    source_node: bool, annotation: Any, source: Any
) -> None:
    source = (source,)
    input_value = OmegaConf.create(source) if source_node else source
    original = copy.deepcopy(input_value)

    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple(input_value, tuple[annotation])

    if source_node:
        assert OmegaConf.to_container(input_value) == OmegaConf.to_container(original)
    else:
        assert input_value == original


def assert_typed_string_retypes_to_literal(
    source: Any, annotation: Any, key: Any, expected: Any
) -> None:
    source_leaf = source._get_node(key)
    source_leaf._set_flag("convert", False)
    source_flags = copy.deepcopy(source_leaf._metadata.flags)

    cfg = OmegaConf.typed_tuple((source,), tuple[annotation])
    destination_leaf = cfg[0]._get_node(key)

    assert destination_leaf._metadata.flags == source_flags
    with pytest.raises(ValidationError):
        cfg[0][key] = "bad"
    cfg[0][key] = "x"
    assert OmegaConf.to_object(cfg) == (expected,)
    assert source[key] == "x"
    assert source_leaf._metadata.flags == source_flags


def test_tuple_retypes_typed_list_string_values_to_literal_validators() -> None:
    source = OmegaConf.typed_list(["x"], element_type=str)
    assert_typed_string_retypes_to_literal(source, list[Literal["x"]], 0, ["x"])


def test_tuple_retypes_typed_dict_string_values_to_literal_validators() -> None:
    source = OmegaConf.typed_dict({"child": "x"}, key_type=str, element_type=str)
    assert_typed_string_retypes_to_literal(
        source, dict[str, Literal["x"]], "child", {"child": "x"}
    )


def test_tuple_narrows_typed_literal_values_to_destination_validator() -> None:
    source = OmegaConf.typed_list(["x"], element_type=Literal["x", "y"])
    cfg = OmegaConf.typed_tuple((source,), tuple[list[Literal["x"]]])

    with pytest.raises(ValidationError):
        cfg[0][0] = "y"
    cfg[0][0] = "x"

    assert OmegaConf.to_object(cfg) == (["x"],)
    assert source[0] == "x"


def test_tuple_retypes_typed_bool_with_int_validator() -> None:
    source = OmegaConf.typed_list([True], element_type=bool)
    source_leaf = source._get_node(0)
    assert isinstance(source_leaf, Node)
    source_leaf._set_flag("convert", False)
    source_flags = copy.deepcopy(source_leaf._metadata.flags)

    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple((source,), tuple[list[int]])
    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple(([True],), tuple[list[int]])

    assert source[0] is True
    assert source_leaf._metadata.flags == source_flags


def test_tuple_retypes_literal_string_with_string_validator() -> None:
    source = OmegaConf.typed_list(["x"], element_type=Literal["x"])
    source_leaf = source._get_node(0)
    assert isinstance(source_leaf, Node)
    source_leaf._set_flag("convert", False)
    source_flags = copy.deepcopy(source_leaf._metadata.flags)
    cfg = OmegaConf.typed_tuple((source,), tuple[list[str]])

    cfg[0][0] = "y"
    raw_cfg = OmegaConf.typed_tuple((["x"],), tuple[list[str]])
    raw_cfg[0][0] = "y"

    assert cfg[0][0] == "y"
    assert raw_cfg[0][0] == "y"
    assert source[0] == "x"
    assert source_leaf._metadata.flags == source_flags


def nested_sequence_source(shape: str, value: Any) -> Any:
    if shape == "list":
        return OmegaConf.create(([(value,)],))
    return OmegaConf.create(({"child": (value,)},))


def nested_sequence_leaf(config: Any, shape: str) -> Any:
    if shape == "list":
        return config[0][0]._get_node(0)
    return config[0]["child"]._get_node(0)


def set_nested_sequence_value(config: Any, shape: str, value: Any) -> None:
    if shape == "list":
        config[0][0][0] = value
    else:
        config[0]["child"][0] = value


def tuple_sequence_type(shape: str) -> Any:
    if shape == "list":
        return tuple[list[list[int]]]
    return tuple[dict[str, list[int]]]


@pytest.mark.parametrize("shape", ["list", "dict"])
@pytest.mark.parametrize("convert", [False, True])
def test_tuple_sequence_kind_conversion_preserves_convert_flag(
    shape: str, convert: bool
) -> None:
    source = nested_sequence_source(shape, "5")
    source_leaf = nested_sequence_leaf(source, shape)
    source_leaf._set_flag("convert", convert)
    source_snapshot = copy.deepcopy(source)

    if convert:
        cfg = OmegaConf.typed_tuple(source, tuple_sequence_type(shape))
        destination_leaf = nested_sequence_leaf(cfg, shape)
        assert destination_leaf._value() == 5
        assert destination_leaf._metadata.flags == source_leaf._metadata.flags
        if shape == "list":
            assert OmegaConf.to_object(cfg) == ([[5]],)
        else:
            assert OmegaConf.to_object(cfg) == ({"child": [5]},)
    else:
        with pytest.raises(ValidationError):
            OmegaConf.typed_tuple(source, tuple_sequence_type(shape))

    assert source_leaf._value() == "5"
    assert source_leaf._metadata.flags == {"convert": convert}
    assert OmegaConf.to_container(source) == OmegaConf.to_container(source_snapshot)


@pytest.mark.parametrize("shape", ["list", "dict"])
def test_tuple_sequence_kind_conversion_preserves_readonly_flag(shape: str) -> None:
    source = nested_sequence_source(shape, 5)
    source_leaf = nested_sequence_leaf(source, shape)
    source_leaf._set_flag("readonly", True)
    source_snapshot = copy.deepcopy(source)

    cfg = OmegaConf.typed_tuple(source, tuple_sequence_type(shape))
    destination_leaf = nested_sequence_leaf(cfg, shape)

    assert destination_leaf._metadata.flags == {"readonly": True}
    with pytest.raises(ReadonlyConfigError):
        set_nested_sequence_value(cfg, shape, 6)
    assert source_leaf._value() == 5
    assert source_leaf._metadata.flags == {"readonly": True}
    assert OmegaConf.to_container(source) == OmegaConf.to_container(source_snapshot)


@pytest.mark.parametrize("convert", [False, True])
def test_tuple_list_to_tuple_conversion_preserves_leaf_flags(convert: bool) -> None:
    source = OmegaConf.create(([[("5")]],))
    source_leaf = source[0][0]._get_node(0)
    source_leaf._set_flag("convert", convert)
    source_snapshot = copy.deepcopy(source)

    if convert:
        cfg = OmegaConf.typed_tuple(source, tuple[list[tuple[int]]])
        destination_leaf = cfg[0][0]._get_node(0)
        assert OmegaConf.to_object(cfg) == ([(5,)],)
        assert destination_leaf._metadata.flags == {"convert": True}
    else:
        with pytest.raises(ValidationError):
            OmegaConf.typed_tuple(source, tuple[list[tuple[int]]])

    assert source_leaf._value() == "5"
    assert source_leaf._metadata.flags == {"convert": convert}
    assert OmegaConf.to_container(source) == OmegaConf.to_container(source_snapshot)


@pytest.mark.parametrize("shape", ["list", "dict"])
@pytest.mark.parametrize(
    "annotation,value,valid",
    [
        (Literal["x"], "x", True),
        (Literal["x"], "bad", False),
        (Literal[1], 1, True),
        (Literal[1], True, False),
        (Literal[None], None, True),
        (Literal["x", None], None, True),
        (Literal["x"], None, False),
    ],
)
def test_tuple_validates_nested_literals(
    shape: str, annotation: Any, value: Any, valid: bool
) -> None:
    annotation, supplied = nested(shape, annotation, value)
    if valid:
        cfg = OmegaConf.typed_tuple((supplied,), tuple[annotation])
        assert OmegaConf.to_object(cfg) == (supplied,)
    else:
        with pytest.raises(ValidationError):
            OmegaConf.typed_tuple((supplied,), tuple[annotation])


@pytest.mark.parametrize("source_node", [False, True])
@pytest.mark.parametrize("shape", ["direct", "list"])
@pytest.mark.parametrize(
    "key_type,source_key,expected_key",
    [(TupleKey, "A", TupleKey.A), (bool, 1, True)],
)
def test_tuple_normalizes_raw_dictionary_keys(
    source_node: bool,
    shape: str,
    key_type: Any,
    source_key: Any,
    expected_key: Any,
) -> None:
    dictionary_type = dict[key_type, int]
    item_type = list[dictionary_type] if shape == "list" else dictionary_type
    value = {source_key: "5"}
    if shape == "list":
        value = [value]
    source = OmegaConf.create((value,)) if source_node else (value,)
    original = copy.deepcopy(source)

    cfg = OmegaConf.typed_tuple(source, tuple[item_type])

    expected_dict = {expected_key: 5}
    expected = (expected_dict,) if shape == "direct" else ([expected_dict],)
    assert OmegaConf.to_object(cfg) == expected
    dict_node = cfg[0] if shape == "direct" else cfg[0][0]
    normalized_key = next(iter(dict_node))
    assert type(normalized_key) is type(expected_key)
    if source_node:
        assert OmegaConf.to_container(source) == OmegaConf.to_container(original)
    else:
        assert source == original


@pytest.mark.parametrize("source_node", [False, True])
@pytest.mark.parametrize("shape", ["direct", "list"])
@pytest.mark.parametrize("key_type,source_key", [(TupleKey, "invalid"), (bool, 2)])
def test_tuple_rejects_invalid_raw_dictionary_keys_without_mutating_source(
    source_node: bool, shape: str, key_type: Any, source_key: Any
) -> None:
    dictionary_type = dict[key_type, int]
    item_type = list[dictionary_type] if shape == "list" else dictionary_type
    value = {source_key: "5"}
    if shape == "list":
        value = [value]
    source = OmegaConf.create((value,)) if source_node else (value,)
    original = copy.deepcopy(source)

    with pytest.raises(KeyValidationError):
        OmegaConf.typed_tuple(source, tuple[item_type])

    if source_node:
        assert OmegaConf.to_container(source) == OmegaConf.to_container(original)
    else:
        assert source == original


@pytest.mark.parametrize("source_node", [False, True])
def test_tuple_dictionary_key_normalization_collisions_match_typed_dict(
    source_node: bool,
) -> None:
    value = {"A": "3", 1: "5"}
    source = OmegaConf.create((value,)) if source_node else (value,)
    original = copy.deepcopy(source)
    expected = OmegaConf.to_container(
        OmegaConf.typed_dict(value, key_type=TupleKey, element_type=int)
    )

    cfg = OmegaConf.typed_tuple(source, tuple[dict[TupleKey, int]])

    assert OmegaConf.to_container(cfg[0]) == expected
    if source_node:
        assert OmegaConf.to_container(source) == OmegaConf.to_container(original)
    else:
        assert source == original


@pytest.mark.parametrize("source_node", [False, True])
@pytest.mark.parametrize("shape", ["direct", "list"])
@pytest.mark.parametrize(
    "entries",
    [
        [("A", "bad"), (1, "5")],
        [("A", "5"), (1, "bad")],
    ],
)
def test_tuple_validates_all_values_before_alias_collision(
    source_node: bool,
    shape: str,
    entries: list[tuple[Any, Any]],
) -> None:
    dictionary_type = dict[TupleKey, int]
    item_type = list[dictionary_type] if shape == "list" else dictionary_type
    value = dict(entries)
    if shape == "list":
        value = [value]
    source = OmegaConf.create((value,)) if source_node else (value,)
    original = copy.deepcopy(source)

    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple(source, tuple[item_type])

    if source_node:
        assert OmegaConf.to_container(source) == OmegaConf.to_container(original)
    else:
        assert source == original


@pytest.mark.parametrize(
    "key_type,key",
    [(TupleKey, TupleKey.A), (bool, True)],
)
def test_tuple_preserves_explicitly_typed_dictionary_keys(
    key_type: Any, key: Any
) -> None:
    source = OmegaConf.typed_dict({key: "5"}, key_type=key_type, element_type=int)

    cfg = OmegaConf.typed_tuple((source,), tuple[dict[key_type, int]])

    assert OmegaConf.to_object(cfg) == ({key: 5},)
    assert type(next(iter(cfg[0]))) is type(key)


@pytest.mark.parametrize("flag", ["readonly", "struct"])
def test_tuple_key_normalization_preserves_mapping_flags(flag: str) -> None:
    source = OmegaConf.create(({"A": "3", 1: "5"},))
    source_dict = source[0]
    source_dict._set_flag(flag, True)
    original = copy.deepcopy(source)

    cfg = OmegaConf.typed_tuple(source, tuple[dict[TupleKey, int]])

    assert OmegaConf.to_object(cfg) == ({TupleKey.A: 5},)
    assert getattr(OmegaConf, f"is_{flag}")(cfg[0]) is True
    child = cfg[0]._get_node(TupleKey.A)
    assert child is not None
    assert child._get_parent() is cfg[0]
    assert child._key() is TupleKey.A
    assert source_dict._get_flag(flag) is True
    assert OmegaConf.to_container(source) == OmegaConf.to_container(original)


def test_tuple_key_normalization_preserves_mapping_convert_policy() -> None:
    source = OmegaConf.create(({"A": "5"},))
    source_dict = source[0]
    source_dict._set_flag("convert", False)
    original = copy.deepcopy(source)

    with pytest.raises(ValidationError):
        OmegaConf.typed_tuple(source, tuple[dict[TupleKey, int]])

    assert source_dict._get_flag("convert") is False
    assert OmegaConf.to_container(source) == OmegaConf.to_container(original)


@pytest.mark.parametrize("source_kind", [tuple, list])
@pytest.mark.parametrize("convert", [True, False])
def test_tuple_retyping_keeps_direct_scalar_flags(
    source_kind: Any, convert: bool
) -> None:
    source = OmegaConf.create(source_kind(["5"]))
    source._get_node(0)._set_flag(["convert", "readonly"], [convert, True])
    if convert:
        result = OmegaConf.typed_tuple(source, tuple[int])
        assert OmegaConf.to_object(result) == (5,)
        result_leaf = result._get_node(0)
        assert isinstance(result_leaf, Node)
        assert result_leaf._metadata.flags == source._get_node(0)._metadata.flags
    else:
        with pytest.raises(ValidationError):
            OmegaConf.typed_tuple(source, tuple[int])
    assert source[0] == "5"
    assert source._get_node(0)._get_flag("convert") is convert


@pytest.mark.parametrize("special", [None, "${value}"])
def test_tuple_retyping_keeps_special_child_flags(special: Any) -> None:
    child = TupleConfig(special, flags={"readonly": True})
    source = OmegaConf.create((child,))
    result = OmegaConf.typed_tuple(source, tuple[tuple[int] | None])
    result_child = result._get_node(0)
    source_child = source._get_node(0)
    assert isinstance(result_child, Node)
    assert isinstance(source_child, Node)
    assert result_child._metadata.flags == child._metadata.flags
    assert result_child._value() == special
    assert source_child._metadata.flags == child._metadata.flags


@pytest.mark.parametrize(
    "annotation,first,last",
    [(list[int], [3], [5]), (dict[str, int], {"v": 3}, {"v": 5})],
)
def test_tuple_key_collisions_preserve_winning_container_flags(
    annotation: Any, first: Any, last: Any
) -> None:
    source = OmegaConf.create({"A": first, 1: last})
    OmegaConf.set_readonly(source[1], True)
    result = OmegaConf.typed_tuple((source,), tuple[dict[TupleKey, annotation]])
    assert OmegaConf.to_object(result) == ({TupleKey.A: last},)
    assert OmegaConf.is_readonly(result[0][TupleKey.A]) is True
    with pytest.raises(ReadonlyConfigError):
        result[0][TupleKey.A][0 if isinstance(last, list) else "v"] = 7
    assert OmegaConf.to_container(source) == {"A": first, 1: last}


@pytest.mark.parametrize("source_kind", ["tuple", "list"])
@pytest.mark.parametrize("destination", [int, int | float, int | str, Any])
@pytest.mark.parametrize("value", [1, "bad"])
def test_tuple_retypes_source_union_nodes(
    source_kind: str, destination: Any, value: Any
) -> None:
    source = (
        OmegaConf.typed_tuple((value,), tuple[int | str])
        if source_kind == "tuple"
        else OmegaConf.typed_list([value], element_type=int | str)
    )
    source_node = source._get_node(0)
    assert isinstance(source_node, Node)
    source_node._set_flag(["readonly", "convert"], [True, False])
    if value == "bad" and destination not in (Any, int | str):
        with pytest.raises(ValidationError):
            OmegaConf.typed_tuple(source, tuple[destination])
    else:
        result = OmegaConf.typed_tuple(source, tuple[destination])
        result_node = result._get_node(0)
        assert isinstance(result_node, Node)
        assert OmegaConf.to_object(result) == (value,)
        assert result_node._metadata.flags == source_node._metadata.flags
        if destination in (Any, int | str):
            assert isinstance(result_node, UnionNode)
    assert source[0] == value
    assert source_node._get_flag("convert") is False
