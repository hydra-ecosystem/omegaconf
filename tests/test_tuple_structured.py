from dataclasses import dataclass, field, make_dataclass
from enum import Enum
from types import GenericAlias
from typing import Any, List, Literal, NamedTuple, Optional, Tuple, cast

import attr
from pytest import mark, param, raises
from typing_extensions import TypeVarTuple, Unpack

from omegaconf import (
    MISSING,
    DictConfig,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    TupleConfig,
    ValidationError,
)
from omegaconf.base import Node, UnionNode
from omegaconf.basecontainer import _deep_update_type_hint
from omegaconf.errors import ConfigKeyError, KeyValidationError, ReadonlyConfigError
from omegaconf.nodes import AnyNode, FloatNode, IntegerNode, StringNode


@dataclass
class TupleFields:
    fixed: Tuple[int, str] = (1, "x")
    variadic: Tuple[int, ...] = (1, 2)
    empty: Tuple[()] = ()
    bare: tuple = ()
    optional: Optional[Tuple[int, ...]] = None
    missing: Tuple[int, str] = MISSING
    numbers: List[int] = field(default_factory=list)


@attr.s(auto_attribs=True)
class AttrTupleFields:
    fixed: Tuple[int, str] = (1, "x")
    variadic: tuple[int, ...] = (1, 2)
    optional: Optional[Tuple[int, ...]] = None


class Point(NamedTuple):
    x: int
    y: int


def test_create_native_tuple_returns_tupleconfig() -> None:
    cfg = OmegaConf.create((1, "x"))
    assert isinstance(cfg, TupleConfig)
    assert cfg == (1, "x")
    assert cfg._metadata.ref_type == Tuple[Any, ...]
    assert OmegaConf.get_type(cfg) is tuple


def test_create_native_list_still_returns_listconfig() -> None:
    cfg = OmegaConf.create([1, "x"])
    assert isinstance(cfg, ListConfig)
    assert OmegaConf.get_type(cfg) is list


def test_namedtuple_keeps_existing_non_tupleconfig_behavior() -> None:
    cfg = OmegaConf.create(Point(1, 2))

    assert isinstance(cfg, ListConfig)
    assert not isinstance(cfg, TupleConfig)


def test_nested_native_tuple_preserves_identity() -> None:
    cfg = OmegaConf.create({"value": (1, 2)})
    assert isinstance(cfg.value, TupleConfig)
    assert cfg.value == (1, 2)


def test_public_predicates() -> None:
    tuple_cfg = OmegaConf.create((1,))
    list_cfg = OmegaConf.create([1])
    assert OmegaConf.is_tuple(tuple_cfg)
    assert not OmegaConf.is_list(tuple_cfg)
    assert OmegaConf.is_config(tuple_cfg)
    assert OmegaConf.is_sequence(tuple_cfg)
    assert OmegaConf.is_sequence(list_cfg)
    assert not OmegaConf.is_sequence((1,))
    assert not OmegaConf.is_sequence([1])


def test_typed_tuple_requires_content() -> None:
    with raises(TypeError, match="content"):
        OmegaConf.typed_tuple()  # type: ignore[call-arg]


def test_typed_tuple_rejects_none() -> None:
    with raises(ValidationError, match="Non optional"):
        OmegaConf.typed_tuple(None, Tuple[int])


@mark.parametrize(
    "tuple_type,content,expected",
    [
        param(Tuple[int, str], [1, 2], (1, "2"), id="typing_fixed_list"),
        param(tuple[int, str], (1, 2), (1, "2"), id="builtin_fixed_tuple"),
        param(Tuple[int, ...], ["1", 2], (1, 2), id="typing_variadic"),
        param(tuple[()], [], (), id="empty"),
    ],
)
def test_typed_tuple(tuple_type: Any, content: Any, expected: Any) -> None:
    cfg = OmegaConf.typed_tuple(content, tuple_type=tuple_type)
    assert isinstance(cfg, TupleConfig)
    assert cfg == expected
    assert cfg._metadata.ref_type == tuple_type


def test_typed_tuple_does_not_infer_positional_types() -> None:
    cfg = OmegaConf.typed_tuple([1, "x"])
    assert cfg._metadata.ref_type == Tuple[Any, ...]


def test_typed_tuple_converts_nested_list_to_tuple() -> None:
    cfg = OmegaConf.typed_tuple(([["1"]],), tuple[list[tuple[int]]])

    assert cfg == ([(1,)],)


def test_typed_tuple_converts_nested_tuple_to_list() -> None:
    cfg = OmegaConf.typed_tuple(({"x": ("1",)},), tuple[dict[str, list[int]]])

    assert cfg == ({"x": [1]},)


def test_typed_tuple_converts_typed_source_scalar() -> None:
    source = OmegaConf.typed_list(["5"], element_type=str)

    cfg = OmegaConf.typed_tuple((source,), tuple[list[int]])

    assert cfg == ([5],)
    assert source == ["5"]
    assert source._metadata.element_type is str


def test_typed_tuple_validates_nested_literal_values() -> None:
    tuple_type = tuple[list[Literal["red", "blue"]]]

    assert OmegaConf.typed_tuple((["red"],), tuple_type) == (["red"],)
    with raises(ValidationError):
        OmegaConf.typed_tuple((["green"],), tuple_type)


@mark.parametrize(
    "annotation,value",
    [
        (Literal["red", "blue"], "red"),
        (Optional[Literal["red"]], None),
        (Literal[None], None),
        (Literal[1, None], 1),
        (Literal[1, None], None),
    ],
)
def test_tuple_copies_support_literal_values(annotation: Any, value: Any) -> None:
    cfg = OmegaConf.typed_tuple((value,), tuple[annotation])
    assert cfg[:] == (value,)
    assert cfg * 2 == (value, value)
    assert cfg + cfg == (value, value)

    nested = OmegaConf.typed_tuple(([value],), tuple[list[annotation]])
    assert nested[:] == ([value],)
    assert nested * 2 == ([value], [value])
    assert nested + nested == ([value], [value])


def test_deep_update_rejects_non_literal_nodes_for_literal_types() -> None:
    node = StringNode("red")

    with raises(ValidationError):
        _deep_update_type_hint(node, Literal["red", "blue"])

    assert node._metadata.ref_type is str


def test_deep_update_rejects_literal_nodes_with_different_choices() -> None:
    source_type = Literal["red", "green"]
    node = OmegaConf.typed_tuple(("red",), tuple[source_type])._get_node(0)
    assert isinstance(node, Node)

    with raises(ValidationError):
        _deep_update_type_hint(node, Literal["red", "blue"])

    assert node._metadata.ref_type == source_type


def test_typed_tuple_rejects_non_tuple_annotation() -> None:
    with raises(ValidationError, match="Unsupported tuple type"):
        OmegaConf.typed_tuple([1], tuple_type=List[int])


def test_typed_tuple_rejects_pep646_unpack() -> None:
    types = TypeVarTuple("types")

    with raises(ValidationError, match="Unsupported tuple type"):
        OmegaConf.typed_tuple([], tuple_type=tuple[Unpack[types]])


def test_typed_tuple_rejects_misplaced_ellipsis() -> None:
    tuple_type = GenericAlias(tuple, (int, ..., str))

    with raises(ValidationError, match="Unsupported tuple type"):
        OmegaConf.typed_tuple([], tuple_type=tuple_type)


def test_dataclass_tuple_fields() -> None:
    cfg = OmegaConf.structured(TupleFields)
    assert isinstance(cfg.fixed, TupleConfig)
    assert isinstance(cfg.variadic, TupleConfig)
    assert isinstance(cfg.empty, TupleConfig)
    assert isinstance(cfg.bare, TupleConfig)
    assert cfg.fixed == (1, "x")
    assert cfg.variadic == (1, 2)
    assert cfg.empty == ()
    assert cfg.optional is None


def test_tuple_merge_constructs_nested_structured_values() -> None:
    @dataclass
    class Child:
        count: int = 1

    schema = make_dataclass("Input", [("items", tuple[Child, ...])])
    cfg = OmegaConf.merge(OmegaConf.structured(schema), {"items": [{"count": "5"}]})
    result: Any = OmegaConf.to_object(cfg)
    assert result.items == (Child(count=5),)
    with raises(ValidationError):
        OmegaConf.merge(OmegaConf.structured(schema), {"items": [{"count": "bad"}]})


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
def test_copy_typed_tuple_does_not_run_structured_defaults(operation: str) -> None:
    calls: list[str] = []

    def factory() -> int:
        calls.append("called")
        raise RuntimeError("default factory must not run for a copied value")

    @dataclass
    class Child:
        value: int = field(default_factory=factory)

    cfg = OmegaConf.typed_tuple((Child(value=3),), tuple[Child])
    assert calls == []

    if operation == "slice":
        result = cfg[:]
        expected = (Child(value=3),)
    elif operation == "multiply":
        result = cfg * 2
        expected = (Child(value=3), Child(value=3))
    else:
        result = cfg + ()
        expected = (Child(value=3),)

    assert calls == []
    assert result == expected
    child = result._get_node(0)
    assert isinstance(child, DictConfig)
    assert OmegaConf.get_type(child) is Child
    assert child._metadata.ref_type is Child
    assert child._metadata.key == 0
    assert child._get_parent() is result
    assert child.value == 3
    value_node = child._get_node("value")
    assert value_node is not None
    assert value_node._get_parent() is child


def test_copy_typed_tuple_preserves_derived_structured_type() -> None:
    @dataclass
    class Base:
        value: int

    @dataclass
    class Derived(Base):
        label: str = "derived"

    cfg = OmegaConf.typed_tuple((Derived(value=3, label="kept"),), tuple[Base])

    result = cfg[:]
    child = result._get_node(0)
    assert isinstance(child, DictConfig)

    assert OmegaConf.get_type(child) is Derived
    assert child._metadata.ref_type is Base
    assert child._metadata.key == 0
    assert child._get_parent() is result
    assert child.value == 3
    assert child.label == "kept"


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
def test_tuple_collection_copies_preserve_scalar_flags(operation: str) -> None:
    cfg = OmegaConf.typed_tuple(([1],), tuple[list[int]])
    container = cfg._get_node(0)
    assert isinstance(container, ListConfig)
    leaf = container._get_node(0)
    assert isinstance(leaf, Node)
    leaf._set_flag(["readonly", "convert"], [True, False])

    if operation == "slice":
        result = cfg[:]
    elif operation == "multiply":
        result = cfg * 2
    else:
        result = cfg + ()

    result_container = result._get_node(0)
    assert isinstance(result_container, ListConfig)
    result_leaf = result_container._get_node(0)
    assert isinstance(result_leaf, Node)
    assert result_leaf._metadata.flags == {"readonly": True, "convert": False}
    assert result_leaf._get_parent() is result_container
    assert result_leaf._metadata.key == 0
    with raises(ReadonlyConfigError):
        result[0][0] = "2"
    assert leaf._metadata.flags == {"readonly": True, "convert": False}


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
def test_tuple_collection_copies_preserve_convert_flag(operation: str) -> None:
    cfg = OmegaConf.typed_tuple(([1],), tuple[list[int]])
    container = cfg._get_node(0)
    assert isinstance(container, ListConfig)
    leaf = container._get_node(0)
    assert isinstance(leaf, Node)
    leaf._set_flag("convert", False)

    if operation == "slice":
        result = cfg[:]
    elif operation == "multiply":
        result = cfg * 2
    else:
        result = cfg + ()

    with raises(ValidationError):
        result[0][0] = "2"
    assert result[0][0] == 1


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
@mark.parametrize(
    "annotation,value",
    [(int | None, None), (Any, None), (int, "$" + "{tuple_copy_answer}")],
)
def test_tuple_collection_copies_preserve_special_leaf_flags(
    operation: str, annotation: Any, value: Any
) -> None:
    cfg = OmegaConf.typed_tuple(([value],), tuple[list[annotation]])
    container = cfg._get_node(0)
    assert isinstance(container, ListConfig)
    leaf = container._get_node(0)
    assert isinstance(leaf, Node)
    leaf._set_flag(["readonly", "convert"], [True, False])

    if operation == "slice":
        result = cfg[:]
    elif operation == "multiply":
        result = cfg * 2
    else:
        result = cfg + ()

    result_container = result._get_node(0)
    assert isinstance(result_container, ListConfig)
    result_leaf = result_container._get_node(0)
    assert isinstance(result_leaf, Node)
    assert result_leaf._metadata.flags == {"readonly": True, "convert": False}
    assert result_leaf._get_parent() is result_container
    assert result_leaf._metadata.key == 0
    assert leaf._metadata.flags == {"readonly": True, "convert": False}


@mark.parametrize("shape", ["direct", "nested"])
def test_typed_tuple_materializes_frozen_structured_mappings(shape: str) -> None:
    @dataclass(frozen=True)
    class FrozenChild:
        count: int = 1

    if shape == "direct":
        cfg = OmegaConf.typed_tuple(({"count": "2"},), tuple[FrozenChild])
        child = cfg._get_node(0)
    else:
        cfg = OmegaConf.typed_tuple(([{"count": "2"}],), tuple[list[FrozenChild]])
        container = cfg._get_node(0)
        assert isinstance(container, ListConfig)
        child = container._get_node(0)

    assert isinstance(child, DictConfig)
    assert child.count == 2
    assert OmegaConf.is_readonly(child) is True
    with raises(ReadonlyConfigError):
        child.count = 3


@mark.parametrize("shape", ["direct", "nested"])
def test_typed_tuple_normalizes_enum_dictionary_keys(shape: str) -> None:
    class Color(Enum):
        RED = 1

    source = {"RED": "5"}
    if shape == "direct":
        cfg = OmegaConf.typed_tuple((source,), tuple[dict[Color, int]])
        result = cfg[0]
    else:
        cfg = OmegaConf.typed_tuple(([source],), tuple[list[dict[Color, int]]])
        result = cfg[0][0]

    assert result == {Color.RED: 5}
    assert source == {"RED": "5"}
    with raises(KeyValidationError):
        OmegaConf.typed_tuple(({"BLUE": 5},), tuple[dict[Color, int]])


def test_typed_tuple_normalizes_enum_keys_from_source_nodes() -> None:
    class Color(Enum):
        RED = 1

    source = OmegaConf.create(({"RED": "5"},))
    cfg = OmegaConf.typed_tuple(source, tuple[dict[Color, int]])

    assert cfg[0] == {Color.RED: 5}
    assert source[0] == {"RED": "5"}


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
@mark.parametrize(
    "annotation,value",
    [
        (list[int] | None, None),
        (dict[str, int] | None, None),
        (tuple[int, ...] | None, None),
        (list[int], "$" + "{container_flags}"),
        (dict[str, int], "$" + "{container_flags}"),
        (tuple[int, ...], "$" + "{container_flags}"),
    ],
)
def test_tuple_collection_copies_preserve_special_container_flags(
    operation: str, annotation: Any, value: Any
) -> None:
    cfg = OmegaConf.typed_tuple(([value],), tuple[list[annotation]])
    container = cfg._get_node(0)
    assert isinstance(container, ListConfig)
    special = container._get_node(0)
    assert isinstance(special, (DictConfig, ListConfig, TupleConfig))
    special._set_flag(["readonly", "convert"], [True, False])

    if operation == "slice":
        result = cfg[:]
    elif operation == "multiply":
        result = cfg * 2
    else:
        result = cfg + ()

    result_container = result._get_node(0)
    assert isinstance(result_container, ListConfig)
    result_special = result_container._get_node(0)
    assert isinstance(result_special, (DictConfig, ListConfig, TupleConfig))
    assert result_special._metadata.flags == {"readonly": True, "convert": False}
    assert result_special._get_parent() is result_container
    assert result_special._metadata.key == 0
    assert special._metadata.flags == {"readonly": True, "convert": False}


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
def test_tuple_collection_copy_preserves_special_container_convert_flag(
    operation: str,
) -> None:
    cfg = OmegaConf.typed_tuple(([None],), tuple[list[list[int] | None]])
    container = cfg._get_node(0)
    assert isinstance(container, ListConfig)
    special = container._get_node(0)
    assert isinstance(special, ListConfig)
    special._set_flag("convert", False)

    if operation == "slice":
        result = cfg[:]
    elif operation == "multiply":
        result = cfg * 2
    else:
        result = cfg + ()

    with raises(ValidationError):
        result[0][0] = ["2"]
    assert result[0][0] is None


@mark.parametrize("operation", ["slice", "multiply", "concatenate"])
@mark.parametrize(
    "annotation,value",
    [
        (list[int] | None, None),
        (dict[str, int] | None, None),
        (tuple[int, ...] | None, None),
        (list[int], "$" + "{container_flags}"),
        (dict[str, int], "$" + "{container_flags}"),
        (tuple[int, ...], "$" + "{container_flags}"),
    ],
)
def test_tuple_copy_preserves_direct_special_container_flags(
    operation: str, annotation: Any, value: Any
) -> None:
    cfg = OmegaConf.typed_tuple((value,), tuple[annotation])
    special = cfg._get_node(0)
    assert isinstance(special, (DictConfig, ListConfig, TupleConfig))
    special._set_flag(["readonly", "convert"], [True, False])

    if operation == "slice":
        result = cfg[:]
    elif operation == "multiply":
        result = cfg * 2
    else:
        result = cfg + ()

    result_special = result._get_node(0)
    assert isinstance(result_special, (DictConfig, ListConfig, TupleConfig))
    assert result_special._metadata.flags == {"readonly": True, "convert": False}
    assert result_special._get_parent() is result
    assert result_special._metadata.key == 0
    assert special._metadata.flags == {"readonly": True, "convert": False}


@mark.parametrize(
    "source,annotation,expected",
    [
        param(
            IntegerNode(1, flags={"readonly": True, "convert": False}),
            int,
            1,
            id="int",
        ),
        param(
            StringNode("value", flags={"readonly": True, "convert": False}),
            str,
            "value",
            id="str",
        ),
        param(
            FloatNode(1.5, flags={"readonly": True, "convert": False}),
            float,
            1.5,
            id="float",
        ),
    ],
)
def test_typed_tuple_narrowing_preserves_scalar_node_flags(
    source: Node, annotation: Any, expected: Any
) -> None:
    cfg = OmegaConf.typed_tuple((source,), tuple[annotation])
    result_node = cfg._get_node(0)

    assert type(result_node) is type(source)
    assert result_node._metadata.optional is False
    assert result_node._metadata.flags == {"readonly": True, "convert": False}
    assert result_node._get_parent() is cfg
    assert result_node._metadata.key == 0
    assert source._metadata.optional is True
    assert source._metadata.flags == {"readonly": True, "convert": False}
    assert source._get_parent() is None
    assert cfg[0] == expected


def test_typed_tuple_narrowing_rejects_none_scalar_node() -> None:
    source = IntegerNode(
        None, flags={"readonly": True, "convert": False}, is_optional=True
    )

    with raises(ValidationError):
        OmegaConf.typed_tuple((source,), tuple[int])

    assert source._metadata.optional is True
    assert source._metadata.flags == {"readonly": True, "convert": False}
    assert source._get_parent() is None


def test_typed_tuple_rebuild_scalar_node_preserves_flags() -> None:
    flags = {"readonly": True, "convert": True}
    source = StringNode("1", flags=flags)

    cfg = OmegaConf.typed_tuple((source,), tuple[int])
    result_node = cfg._get_node(0)

    assert isinstance(result_node, IntegerNode)
    assert result_node._metadata.optional is False
    assert result_node._metadata.flags == flags
    assert result_node._get_parent() is cfg
    assert cfg[0] == 1
    assert source._metadata.ref_type is str
    assert source._metadata.flags == flags
    assert source._get_parent() is None


def test_typed_tuple_rebuild_respects_scalar_convert_false() -> None:
    flags = {"readonly": True, "convert": False}
    source = StringNode("1", flags=flags)

    with raises(ValidationError):
        OmegaConf.typed_tuple((source,), tuple[int])

    assert source._metadata.ref_type is str
    assert source._metadata.optional is True
    assert source._metadata.flags == flags
    assert source._get_parent() is None


def test_typed_tuple_wrappers_preserve_supplied_scalar_flags() -> None:
    flags = {"readonly": True, "convert": False}
    source = IntegerNode(1, flags=flags)

    union_cfg = OmegaConf.typed_tuple((source,), tuple[int | str])
    union_node = union_cfg._get_node(0)
    assert isinstance(union_node, Node)
    assert union_node._metadata.flags == flags
    assert source._metadata.flags == flags

    source_with_conversion = IntegerNode(1, flags={"readonly": True, "convert": True})
    converted_union_cfg = OmegaConf.typed_tuple(
        (source_with_conversion,), tuple[int | str]
    )
    converted_union_node = converted_union_cfg._get_node(0)
    assert isinstance(converted_union_node, Node)
    assert converted_union_node._metadata.flags == {
        "readonly": True,
        "convert": False,
    }

    optional_container_source = AnyNode(None, flags=flags)
    container_cfg = OmegaConf.typed_tuple(
        (optional_container_source,), tuple[list[int] | None]
    )
    container_node = container_cfg._get_node(0)
    assert isinstance(container_node, Node)
    assert container_node._metadata.flags == flags
    assert optional_container_source._metadata.flags == flags


@mark.parametrize("kind", ["list", "dict", "tuple"])
@mark.parametrize("operation", ["create", "typed", "concatenate"])
def test_any_tuple_accepts_existing_typed_containers(kind: str, operation: str) -> None:
    if kind == "list":
        source = OmegaConf.typed_list([1], int)
    elif kind == "dict":
        source = OmegaConf.typed_dict({"a": 1}, str, int)
    else:
        source = OmegaConf.typed_tuple((1,), tuple[int])
    flags = {"readonly": True, "convert": False}
    source._set_flag("readonly", True)
    source._set_flag("convert", False)

    if operation == "create":
        result = OmegaConf.create((source,))
    elif operation == "typed":
        result = OmegaConf.typed_tuple((source,), tuple[Any])
    else:
        result = OmegaConf.typed_tuple((), tuple[Any, ...]) + (source,)

    child = result._get_node(0)
    assert isinstance(child, (DictConfig, ListConfig, TupleConfig))
    assert type(child) is type(source)
    assert child._metadata.type_hint == source._metadata.type_hint
    assert child._metadata.flags == flags
    assert child._get_parent() is result
    assert child._key() == 0
    assert child is not source
    assert source._get_parent() is None
    assert OmegaConf.to_object(result) == (OmegaConf.to_object(source),)


@mark.parametrize("operation", ["create", "typed", "concatenate"])
def test_any_tuple_accepts_supplied_union_container(operation: str) -> None:
    holder = OmegaConf.typed_tuple(
        (OmegaConf.typed_list([1], int),), tuple[list[int] | list[str]]
    )
    source = holder._get_node(0)
    assert isinstance(source, UnionNode)
    source._set_flag("readonly", True)
    flags = dict(source._metadata.flags or {})
    source_branch = source._value()
    assert isinstance(source_branch, ListConfig)
    source_branch_flags = dict(source_branch._metadata.flags or {})

    if operation == "create":
        result = OmegaConf.create((source,))
    elif operation == "typed":
        result = OmegaConf.typed_tuple((source,), tuple[Any])
    else:
        result = OmegaConf.typed_tuple(()) + (source,)

    child = result._get_node(0)
    assert isinstance(child, UnionNode)
    assert child._metadata.type_hint == source._metadata.type_hint
    assert child._metadata.flags == flags
    assert child._get_parent() is result
    assert child._key() == 0
    child_branch = child._value()
    assert isinstance(child_branch, ListConfig)
    assert child_branch._metadata.type_hint == source_branch._metadata.type_hint
    assert child_branch._metadata.flags == source_branch_flags
    assert child_branch._get_parent() is child
    assert child_branch._key() == 0
    assert child is not source
    assert child_branch is not source_branch
    assert source._get_parent() is holder
    assert source._metadata.flags == flags
    assert source_branch._get_parent() is source
    assert OmegaConf.to_object(holder) == ([1],)
    assert OmegaConf.to_object(result) == ([1],)


@mark.parametrize(
    "annotation", [list[int], dict[str, int], tuple[int, ...], TupleFields]
)
def test_typed_tuple_narrowing_preserves_optional_container_flags(
    annotation: Any,
) -> None:
    source = cast(
        Node,
        OmegaConf.typed_tuple(
            ("${optional_container_flags}",), tuple[annotation | None]
        )._get_node(0),
    )
    flags = {"readonly": True, "convert": False}
    source._set_flag("readonly", True)
    source._set_flag("convert", False)

    result = OmegaConf.typed_tuple((source,), tuple[annotation])
    child = result._get_node(0)

    assert isinstance(child, (DictConfig, ListConfig, TupleConfig))
    assert child._metadata.type_hint == annotation
    assert child._metadata.flags == flags
    assert child._metadata.optional is False
    assert child._is_interpolation()
    assert child._value() == "${optional_container_flags}"
    assert child._get_parent() is result
    assert child._key() == 0
    assert child is not source
    assert source._metadata.type_hint == annotation | None
    assert source._metadata.flags == flags
    assert source._get_parent() is not result


@mark.parametrize("shape", ["direct", "nested"])
@mark.parametrize("kind", ["list", "dict", "tuple", "structured"])
@mark.parametrize("value", [None, "${optional_flags}"])
def test_typed_tuple_optional_destinations_preserve_supplied_scalar_flags(
    shape: str, kind: str, value: Any
) -> None:
    @dataclass
    class Child:
        count: int = 1

    annotations = {
        "list": list[int] | None,
        "dict": dict[str, int] | None,
        "tuple": tuple[int, ...] | None,
        "structured": Child | None,
    }
    annotation = annotations[kind]
    flags = {"readonly": True, "convert": False}
    source = AnyNode(value, flags=flags)
    parent: Any
    if shape == "direct":
        cfg = OmegaConf.typed_tuple((source,), tuple[annotation])
        parent = cfg
    else:
        cfg = OmegaConf.typed_tuple(((source,),), tuple[tuple[annotation]])
        parent = cast(Any, cfg._get_node(0))
    result = parent._get_node(0)

    assert isinstance(result, (ListConfig, DictConfig, TupleConfig))
    assert result._metadata.type_hint == annotation
    assert result._metadata.flags == flags
    assert result._get_parent() is parent
    assert result._key() == 0
    assert result is not source
    assert source._metadata.flags == flags
    assert source._get_parent() is None


@mark.parametrize("shape", ["list", "dict", "tuple", "nested"])
def test_nested_typed_tuple_values_do_not_run_default_factories(shape: str) -> None:
    calls: list[str] = []

    def factory() -> int:
        calls.append("called")
        raise RuntimeError("supplied structured values must not run defaults")

    @dataclass
    class Child:
        value: int = field(default_factory=factory)

    if shape == "list":
        tuple_type = tuple[list[Child]]
        value = ([Child(value=3)],)
        path = (0,)
    elif shape == "dict":
        tuple_type = tuple[dict[str, Child]]
        value = ({"child": Child(value=3)},)
        path = ("child",)
    elif shape == "tuple":
        tuple_type = tuple[tuple[Child, ...]]
        value = ((Child(value=3),),)
        path = (0,)
    else:
        tuple_type = tuple[dict[str, list[Child]]]
        value = ({"children": [Child(value=3)]},)
        path = ("children", 0)

    cfg = OmegaConf.typed_tuple(value, tuple_type)
    assert not calls

    for result in (cfg[:], cfg * 2, cfg + ()):
        assert not calls
        node = result._get_node(0)
        assert isinstance(node, (DictConfig, ListConfig, TupleConfig))
        parent = node
        for key in path:
            parent = node
            node = cast(Any, parent)._get_node(key)
            assert isinstance(node, (DictConfig, ListConfig, TupleConfig))

        assert OmegaConf.get_type(node) is Child
        assert node._metadata.ref_type is Child
        assert node._metadata.key == path[-1]
        assert node._get_parent() is parent
        value_node = cast(Any, node)._get_node("value")
        assert value_node is not None
        assert value_node._get_parent() is node


@mark.parametrize("shape", ["list", "dict"])
def test_nested_attrs_tuple_values_do_not_run_default_factories(shape: str) -> None:
    calls: list[str] = []

    def factory() -> int:
        calls.append("called")
        raise RuntimeError("supplied attrs values must not run defaults")

    @attr.define
    class Child:
        value: int = attr.field(factory=factory)

    if shape == "list":
        tuple_type = tuple[list[Child]]
        value = ([Child(value=3)],)
        key: Any = 0
    else:
        tuple_type = tuple[dict[str, Child]]
        value = ({"child": Child(value=3)},)
        key = "child"

    cfg = OmegaConf.typed_tuple(value, tuple_type)
    for result in (cfg[:], cfg * 2, cfg + ()):
        assert not calls
        container = result._get_node(0)
        assert isinstance(container, (DictConfig, ListConfig))
        child = cast(Any, container)._get_node(key)
        assert isinstance(child, DictConfig)
        assert OmegaConf.get_type(child) is Child
        assert child._metadata.ref_type is Child
        assert child._get_parent() is container
        assert child.value == 3


def test_nested_typed_tuple_preserves_derived_structured_type() -> None:
    @dataclass
    class Base:
        value: int

    @dataclass
    class Derived(Base):
        label: str = "derived"

    cfg = OmegaConf.typed_tuple(([Derived(value=3, label="kept")],), tuple[list[Base]])
    children = cfg._get_node(0)
    assert isinstance(children, ListConfig)
    child = children._get_node(0)
    assert isinstance(child, DictConfig)

    assert OmegaConf.get_type(child) is Derived
    assert child._metadata.ref_type is Base
    assert child.label == "kept"


def test_nested_typed_tuple_rejects_unrelated_structured_type() -> None:
    @dataclass
    class Child:
        value: int = 1

    @dataclass
    class Other:
        value: int = 1

    source = OmegaConf.create(([Other(value=3)],))

    with raises(ValidationError, match="not a subclass"):
        OmegaConf.typed_tuple(source, tuple[list[Child]])


@mark.parametrize("shape", ["list", "dict", "tuple", "nested"])
def test_typed_tuple_materializes_nested_raw_mappings(shape: str) -> None:
    calls: list[str] = []

    def factory() -> int:
        calls.append("called")
        return 9

    @dataclass
    class Child:
        count: int = 1
        generated: int = field(default_factory=factory)

    if shape == "list":
        tuple_type = tuple[list[Child]]
        value = ([{"count": "5"}],)
        path = (0, 0)
    elif shape == "dict":
        tuple_type = tuple[dict[str, Child]]
        value = ({"child": {"count": "5"}},)
        path = (0, "child")
    elif shape == "tuple":
        tuple_type = tuple[tuple[Child, ...]]
        value = (({"count": "5"},),)
        path = (0, 0)
    else:
        tuple_type = tuple[dict[str, list[Child]]]
        value = ({"children": [{"count": "5"}]},)
        path = (0, "children", 0)

    cfg = OmegaConf.typed_tuple(value, tuple_type)
    result: Any = OmegaConf.to_object(cfg)
    child = result
    for key in path:
        child = child[key]
    assert child == Child(count=5, generated=9)
    assert calls == ["called"]


@mark.parametrize("raw", [{"count": "bad"}, {"count": 5, "unknown": 1}])
def test_typed_tuple_rejects_bad_nested_structured_mappings(raw: Any) -> None:
    @dataclass
    class Child:
        count: int = 1

    with raises((ValidationError, ConfigKeyError)):
        OmegaConf.typed_tuple(([raw],), tuple[list[Child]])


def test_typed_tuple_nested_structured_mapping_requires_mandatory_fields() -> None:
    @dataclass
    class Child:
        count: int = MISSING

    cfg = OmegaConf.typed_tuple(([{}],), tuple[list[Child]])

    with raises(MissingMandatoryValue):
        cfg[0][0].count


def test_typed_tuple_optional_nested_container_none_and_interpolation(
    restore_resolvers: Any,
) -> None:
    @dataclass
    class Child:
        value: int = 1

    optional_type = tuple[list[Child] | None]
    none_cfg = OmegaConf.typed_tuple((None,), optional_type)
    assert none_cfg[:][0] is None

    OmegaConf.register_resolver("tuple_none_list", lambda: None)
    interpolation_cfg = OmegaConf.typed_tuple(("${tuple_none_list:}",), optional_type)
    copied = interpolation_cfg[:]
    assert copied[0] is None


def test_typed_tuple_optional_fixed_tuple_element_accepts_none() -> None:
    cfg = OmegaConf.typed_tuple(([None],), tuple[list[tuple[int] | None]])

    assert cfg == ([None],)


def test_typed_tuple_revalidates_optional_structured_element() -> None:
    @dataclass
    class Child:
        value: int = 1

    Holder = make_dataclass("Holder", [("maybe", Child | None, None)])
    source = OmegaConf.structured(Holder)
    maybe = source._get_node("maybe")
    assert isinstance(maybe, DictConfig)

    with raises(ValidationError):
        OmegaConf.typed_tuple((maybe,), tuple[Child])

    optional = OmegaConf.typed_tuple((maybe,), tuple[Child | None])
    assert optional == (None,)


def test_typed_tuple_revalidates_optional_structured_interpolation(
    restore_resolvers: Any,
) -> None:
    @dataclass
    class Child:
        value: int = 1

    Holder = make_dataclass("Holder", [("maybe", Child | None, "${tuple_none_child:}")])
    OmegaConf.register_resolver("tuple_none_child", lambda: None)
    source = OmegaConf.structured(Holder)
    maybe = source._get_node("maybe")
    assert isinstance(maybe, DictConfig)

    result = OmegaConf.typed_tuple((maybe,), tuple[Child])

    with raises(ValidationError):
        _ = result[0]


def test_attrs_tuple_fields() -> None:
    cfg = OmegaConf.structured(AttrTupleFields)
    assert isinstance(cfg.fixed, TupleConfig)
    assert isinstance(cfg.variadic, TupleConfig)
    assert cfg.fixed == (1, "x")
    assert cfg.variadic == (1, 2)
    assert cfg.optional is None


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_tuple_field_accepts_list_and_coerces_scalars() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.fixed = [2, 3]
    assert isinstance(cfg.fixed, TupleConfig)
    assert cfg.fixed == (2, "3")


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_tuple_field_accepts_listconfig() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.fixed = OmegaConf.typed_list([2, 3], element_type=Any)
    assert isinstance(cfg.fixed, TupleConfig)
    assert cfg.fixed == (2, "3")


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_list_field_accepts_tupleconfig() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.numbers = OmegaConf.typed_tuple([1, 2], Tuple[int, ...])
    assert isinstance(cfg.numbers, ListConfig)
    assert cfg.numbers == [1, 2]


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_list_field_accepts_native_tuple() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.numbers = (1, 2)  # type: ignore[assignment]
    assert isinstance(cfg.numbers, ListConfig)
    assert cfg.numbers == [1, 2]


def test_tuple_field_rejects_wrong_arity_on_replacement() -> None:
    cfg = OmegaConf.structured(TupleFields)
    with raises(ValidationError, match="length"):
        cfg.fixed = [1]


def test_tuple_field_rejects_direct_missing_element() -> None:
    cfg = OmegaConf.structured(TupleFields)
    with raises(ValidationError, match="cannot be missing"):
        cfg.fixed = [1, MISSING]


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_missing_whole_tuple_accepts_complete_replacement() -> None:
    cfg = OmegaConf.structured(TupleFields)
    assert OmegaConf.is_missing(cfg, "missing")
    cfg.missing = [2, 3]
    assert isinstance(cfg.missing, TupleConfig)
    assert cfg.missing == (2, "3")


@mark.filterwarnings("ignore:Implicit conversion from:FutureWarning")
def test_optional_tuple_accepts_complete_replacement_and_none() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.optional = [1, 2]
    assert isinstance(cfg.optional, TupleConfig)
    assert cfg.optional == (1, 2)
    cfg.optional = None
    assert cfg.optional is None


def test_non_optional_tuple_rejects_none() -> None:
    cfg = OmegaConf.structured(TupleFields)
    with raises(ValidationError, match="not Optional"):
        cfg.fixed = None  # type: ignore[assignment]
