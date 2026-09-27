import copy
import pickle
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, Union, cast

import yaml
from pytest import MonkeyPatch, mark, raises

from omegaconf import (
    MISSING,
    DictConfig,
    EnumNode,
    ListConfig,
    OmegaConf,
    TupleConfig,
    _impl,
)
from omegaconf.errors import (
    InterpolationResolutionError,
    InterpolationToMissingValueError,
    ValidationError,
)
from omegaconf.nodes import AnyNode


@mark.parametrize("slashes", range(1, 4))
def test_escaped_missing_scalar_roundtrip(slashes: int) -> None:
    spelling = "\\" * slashes + "???"
    expected = "\\" * (slashes - 1) + "???"
    cfg = OmegaConf.create({"value": spelling, "alias": "${value}"})

    assert cfg.value == expected
    assert cfg.alias == expected
    assert not OmegaConf.is_missing(cfg, "value")
    assert not OmegaConf.is_missing(cfg.value)
    assert not OmegaConf.is_missing(cfg.alias)
    assert OmegaConf.is_missing(MISSING)

    for clone in (copy.deepcopy(cfg), pickle.loads(pickle.dumps(cfg))):
        assert not OmegaConf.is_missing(clone, "value")
        assert not OmegaConf.is_missing(clone.value)

    reloaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=True))
    assert reloaded.value == expected
    assert not OmegaConf.is_missing(reloaded, "value")

    OmegaConf.resolve(cfg)
    assert cfg.alias == expected
    assert not OmegaConf.is_missing(cfg, "alias")
    OmegaConf.resolve(cfg)
    assert not OmegaConf.is_missing(cfg, "alias")


def test_escaped_missing_through_resolvers() -> None:
    OmegaConf.register_resolver("test_missing_escape_identity", lambda value: value)
    OmegaConf.register_resolver("test_missing_escape_literal", lambda: r"\???")
    cfg = OmegaConf.create(
        {
            "value": r"\???",
            "nested": "${test_missing_escape_identity:${value}}",
            "returned": "${test_missing_escape_literal:}",
        }
    )
    assert not OmegaConf.is_missing(cfg.nested)
    assert not OmegaConf.is_missing(cfg.returned)
    OmegaConf.resolve(cfg)
    assert not OmegaConf.is_missing(cfg, "nested")
    assert not OmegaConf.is_missing(cfg, "returned")


@mark.parametrize("slashes", range(1, 3))
def test_escaped_missing_through_quoted_interpolation_argument(slashes: int) -> None:
    OmegaConf.register_resolver(
        "test_missing_escape_quoted_identity", lambda value: value, replace=True
    )
    spelling = "\\" * slashes + "???"
    expected = "\\" * (slashes - 1) + "???"
    cfg = OmegaConf.create(
        {
            "literal": spelling,
            "value": '${test_missing_escape_quoted_identity:"${literal}"}',
        }
    )

    assert cfg.value == expected
    assert not OmegaConf.is_missing(cfg, "value")
    OmegaConf.resolve(cfg)
    assert cfg.value == expected
    assert not OmegaConf.is_missing(cfg, "value")


def test_escaped_missing_resolver_return_matches_literal_annotation() -> None:
    def resolver() -> Literal["???"]:
        return cast(Literal["???"], r"\???")

    OmegaConf.register_resolver(
        "test_missing_escape_literal_return", resolver, annotation_validation="error"
    )
    cfg = OmegaConf.create({"value": "${test_missing_escape_literal_return:}"})

    assert cfg.value == "???"
    assert not OmegaConf.is_missing(cfg, "value")
    OmegaConf.resolve(cfg)
    assert cfg.value == "???"
    assert not OmegaConf.is_missing(cfg, "value")


def test_string_enum_with_escaped_missing_value_keeps_enum_identity() -> None:
    class Escaped(str, Enum):
        VALUE = r"\???"
        OTHER = "ordinary"

    node = EnumNode(Escaped, value=Escaped.VALUE)
    assert node._value() is Escaped.VALUE

    cfg = OmegaConf.create({"value": Escaped.OTHER})
    cfg.value = Escaped.VALUE
    assert cfg.value is Escaped.VALUE
    assert not OmegaConf.is_missing(cfg, "value")

    OmegaConf.register_resolver(
        "test_missing_escape_enum", lambda: Escaped.VALUE, annotation_validation="error"
    )
    resolved = OmegaConf.create({"value": "${test_missing_escape_enum:}"})
    assert resolved.value is Escaped.VALUE


def test_plain_missing_resolver_result_is_missing_on_access() -> None:
    OmegaConf.register_resolver("test_missing_escape_missing", lambda: MISSING)
    cfg = OmegaConf.create({"value": "${test_missing_escape_missing:}"})
    with raises(InterpolationToMissingValueError):
        _ = cfg.value
    with raises(InterpolationToMissingValueError):
        OmegaConf.resolve(cfg)


def test_missing_and_escaped_missing_are_structurally_different() -> None:
    missing = OmegaConf.create({"value": MISSING})
    literal = OmegaConf.create({"value": r"\???"})
    assert not OmegaConf.structural_equality(missing, literal)


def test_native_resolver_container_remains_opaque_after_resolve() -> None:
    original = [r"\???", MISSING]
    OmegaConf.register_resolver("test_missing_escape_container", lambda: original)
    cfg = OmegaConf.create({"value": "${test_missing_escape_container:}"})
    assert cfg.value is original
    assert cfg.value == [r"\???", MISSING]
    assert all(type(item) is str for item in cfg.value)
    exported = OmegaConf.to_container(cfg, resolve=True)
    assert isinstance(exported, dict)
    assert isinstance(exported["value"], list)
    assert type(exported["value"][1]) is str
    lazy_reloaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=True))
    assert lazy_reloaded.value[0] == r"\???"
    assert lazy_reloaded.value[1] == MISSING
    assert not OmegaConf.is_missing(lazy_reloaded.value, 1)
    assert all(type(item) is str for item in original)
    OmegaConf.resolve(cfg)
    assert not OmegaConf.is_interpolation(cfg, "value")
    assert cfg.value[0] == r"\???"
    assert cfg.value[1] == MISSING
    assert not OmegaConf.is_missing(cfg.value, 1)
    assert all(type(item) is str for item in original)
    reloaded = OmegaConf.create(OmegaConf.to_yaml(cfg))
    assert reloaded.value[0] == r"\???"
    assert reloaded.value[1] == MISSING
    assert not OmegaConf.is_missing(reloaded.value, 1)


def test_direct_resolve_of_interpolating_container_preserves_opaque_leaves() -> None:
    values = {
        "list": [r"\???", MISSING],
        "tuple": (r"\???", MISSING),
        "dict": {"escaped": r"\???", "plain": MISSING},
    }
    for kind, value in values.items():
        OmegaConf.register_resolver(
            f"test_missing_escape_direct_{kind}", lambda v=value: v
        )

    root = OmegaConf.create({})
    list_cfg = ListConfig("${test_missing_escape_direct_list:}", parent=root)
    tuple_cfg = TupleConfig("${test_missing_escape_direct_tuple:}", parent=root)
    dict_cfg = DictConfig("${test_missing_escape_direct_dict:}", parent=root)
    OmegaConf.resolve(list_cfg)
    assert list_cfg[0] == r"\???"
    assert list_cfg[1] == MISSING
    assert not OmegaConf.is_missing(list_cfg, 1)
    OmegaConf.resolve(tuple_cfg)
    assert tuple_cfg[0] == r"\???"
    assert tuple_cfg[1] == MISSING
    assert not OmegaConf.is_missing(tuple_cfg, 1)
    OmegaConf.resolve(dict_cfg)
    assert dict_cfg.escaped == r"\???"
    assert dict_cfg.plain == MISSING
    assert not OmegaConf.is_missing(dict_cfg, "plain")


def test_direct_resolve_rejects_recursive_resolver_container() -> None:
    recursive: list[object] = []
    recursive.append(recursive)
    OmegaConf.register_resolver("test_missing_escape_direct_cycle", lambda: recursive)
    cfg = ListConfig(
        "${test_missing_escape_direct_cycle:}", parent=OmegaConf.create({})
    )

    with raises(InterpolationResolutionError, match="recursive resolver result"):
        OmegaConf.resolve(cfg)
    assert cfg._is_interpolation()


def test_cycle_scan_visits_shared_containers_once(monkeypatch: MonkeyPatch) -> None:
    shared: list[object] = []
    for _ in range(20):
        shared = [shared, shared]

    visits = 0
    original = _impl.is_primitive_container

    def counted(value: object) -> bool:
        nonlocal visits
        visits += 1
        if visits > 100:
            raise AssertionError("cycle scan revisited shared containers")
        return original(value)

    monkeypatch.setattr(_impl, "is_primitive_container", counted)
    assert not _impl._is_recursive_container(shared)


def test_tuple_resolve_rejects_missing_node_from_resolver() -> None:
    OmegaConf.register_resolver(
        "test_missing_escape_node_missing", lambda: AnyNode(MISSING)
    )
    cfg = TupleConfig(("${test_missing_escape_node_missing:}",))

    with raises(InterpolationToMissingValueError):
        OmegaConf.resolve(cfg)


def test_native_resolver_container_preserves_identity_aliases_and_cycles() -> None:
    class ListSubclass(list):
        pass

    class TupleSubclass(tuple):
        pass

    source = [1, 2]
    shared = [source, source]
    ordered = OrderedDict(value=1)
    cyclic: list[object] = []
    cyclic.append(cyclic)
    list_subclass = ListSubclass([1])
    tuple_subclass = TupleSubclass((1,))

    OmegaConf.register_resolver("test_missing_escape_identity_list", lambda: source)
    OmegaConf.register_resolver("test_missing_escape_identity_shared", lambda: shared)
    OmegaConf.register_resolver("test_missing_escape_identity_ordered", lambda: ordered)
    OmegaConf.register_resolver(
        "test_missing_escape_identity_list_subclass", lambda: list_subclass
    )
    OmegaConf.register_resolver(
        "test_missing_escape_identity_tuple_subclass", lambda: tuple_subclass
    )
    OmegaConf.register_resolver("test_missing_escape_identity_cycle", lambda: cyclic)
    cfg = OmegaConf.create(
        {
            "source": "${test_missing_escape_identity_list:}",
            "shared": "${test_missing_escape_identity_shared:}",
            "ordered": "${test_missing_escape_identity_ordered:}",
            "list_subclass": "${test_missing_escape_identity_list_subclass:}",
            "tuple_subclass": "${test_missing_escape_identity_tuple_subclass:}",
            "cycle": "${test_missing_escape_identity_cycle:}",
        }
    )

    assert cfg.source is source
    first_access = cfg.source
    assert first_access is cfg.source
    source.append(3)
    assert cfg.source == [1, 2, 3]
    assert cfg.shared is shared
    assert cfg.shared[0] is cfg.shared[1]
    assert cfg.ordered is ordered
    assert type(cfg.ordered) is OrderedDict
    assert cfg.list_subclass is list_subclass
    assert cfg.tuple_subclass is tuple_subclass
    assert cfg.cycle is cyclic
    assert cfg.cycle[0] is cyclic

    exported = OmegaConf.to_container(cfg, resolve=True)
    assert isinstance(exported, dict)
    assert exported["cycle"][0] is exported["cycle"]
    with raises(InterpolationResolutionError, match="recursive resolver result"):
        OmegaConf.resolve(cfg)
    assert OmegaConf.is_interpolation(cfg, "cycle")


@mark.parametrize("native", [False, True])
def test_escaped_missing_mapping_keys_export_as_plain_strings(native: bool) -> None:
    key = OmegaConf.create({"key": r"\???"}).key
    if native:
        OmegaConf.register_resolver(
            "test_missing_escape_mapping_key", lambda: {key: 1}, replace=True
        )
        cfg = OmegaConf.create({"value": "${test_missing_escape_mapping_key:}"})
        exported_root = OmegaConf.to_container(cfg, resolve=True)
        assert isinstance(exported_root, dict)
        exported = exported_root["value"]
        yaml_text = OmegaConf.to_yaml(cfg, resolve=True)
    else:
        cfg = OmegaConf.create({key: 1})
        exported = OmegaConf.to_container(cfg)
        yaml_text = OmegaConf.to_yaml(cfg)

    assert isinstance(exported, dict)
    assert list(exported) == ["???"]
    assert type(next(iter(exported))) is str
    assert "_EscapedMissing" not in yaml_text
    reloaded = OmegaConf.create(yaml_text)
    reloaded = reloaded.value if native else reloaded
    assert list(reloaded.keys()) == ["???"]
    assert type(next(iter(reloaded.keys()))) is str


def test_native_resolver_tuple_graph_preserves_aliases_for_both_exports() -> None:
    items: list[object] = []
    shared = (1, 2)
    result = (items, r"\???", shared, shared)
    items.append(result)
    OmegaConf.register_resolver(
        "test_missing_escape_tuple_graph", lambda: result, replace=True
    )
    cfg = OmegaConf.create({"value": "${test_missing_escape_tuple_graph:}"})

    exported_root = OmegaConf.to_container(cfg, resolve=True)
    assert isinstance(exported_root, dict)
    exported = exported_root["value"]
    assert isinstance(exported, tuple)
    assert exported is exported[0][0]
    assert exported[2] is exported[3]
    assert exported[1] == r"\???"

    yaml_text = OmegaConf.to_yaml(cfg, resolve=True)
    loaded = yaml.safe_load(yaml_text)["value"]
    assert loaded is loaded[0][0]
    assert loaded[2] is loaded[3]
    assert loaded[1] == r"\\???"


@mark.parametrize(
    "argument,expected",
    [
        ("???", None),
        ('"???"', None),
        (r"\???", "???"),
        (r"\\???", r"\???"),
    ],
)
def test_missing_resolver_argument(argument: str, expected: str | None) -> None:
    OmegaConf.register_resolver(
        "test_missing_escape_argument", lambda value: value, replace=True
    )
    cfg = OmegaConf.create(
        {"value": "${test_missing_escape_argument:" + argument + "}"}
    )
    if expected is None:
        with raises(InterpolationToMissingValueError):
            _ = cfg.value
    else:
        assert cfg.value == expected
        assert not OmegaConf.is_missing(cfg.value)


def test_key_named_missing_remains_available() -> None:
    cfg = OmegaConf.create({"???": 123, "selected": "${???}"})
    assert cfg.selected == 123


@mark.parametrize("reverse", [False, True])
def test_interpolation_chain_is_independent_of_key_order(reverse: bool) -> None:
    items = [("a", r"\???"), ("b", "${a}"), ("c", "${b}")]
    cfg = OmegaConf.create(dict(reversed(items) if reverse else items))
    for key in ("a", "b", "c"):
        assert cfg[key] == MISSING
        assert not OmegaConf.is_missing(cfg[key])
    OmegaConf.resolve(cfg)
    for key in ("a", "b", "c"):
        assert not OmegaConf.is_missing(cfg, key)
    reloaded = OmegaConf.create(OmegaConf.to_yaml(cfg))
    for key in ("a", "b", "c"):
        assert not OmegaConf.is_missing(reloaded, key)


def test_assignment_merge_and_select_preserve_literal() -> None:
    cfg = OmegaConf.create(
        {"source": r"\???", "target": "x", "selected": "${oc.select:source}"}
    )
    cfg.target = cfg.source
    assert not OmegaConf.is_missing(cfg, "target")
    assert not OmegaConf.is_missing(cfg.selected)
    merged = OmegaConf.merge(cfg, {"other": cfg.source})
    assert not OmegaConf.is_missing(merged, "other")
    assert not OmegaConf.is_missing(OmegaConf.select(cfg, "source"))
    cfg.target = MISSING
    assert OmegaConf.is_missing(cfg, "target")


def test_structured_string_field_preserves_literal() -> None:
    @dataclass
    class Schema:
        value: str = r"\???"

    cfg = OmegaConf.structured(Schema)
    assert cfg.value == MISSING
    assert not OmegaConf.is_missing(cfg, "value")
    assert not OmegaConf.is_missing(OmegaConf.create(OmegaConf.to_yaml(cfg)), "value")


def test_typed_fields_accept_literal_without_treating_it_as_missing() -> None:
    @dataclass
    class Schema:
        optional: Optional[str] = r"\???"
        union: Union[str, int] = r"\???"
        literal: Literal["???"] = MISSING
        integer: int = 7

    cfg = OmegaConf.structured(Schema)
    OmegaConf.update(cfg, "literal", r"\???")
    for key in ("optional", "union", "literal"):
        assert cfg[key] == MISSING
        assert not OmegaConf.is_missing(cfg, key)
    with raises(ValidationError):
        cfg.integer = r"\???"


def test_composite_interpolation_preserves_literal_when_result_is_whole_missing() -> (
    None
):
    cfg = OmegaConf.create(
        {
            "value": r"\???",
            "empty": "",
            "whole": "${value}${empty}",
            "part": "prefix-${value}",
        }
    )
    assert cfg.whole == MISSING
    assert not OmegaConf.is_missing(cfg.whole)
    assert cfg.part == "prefix-???"
    OmegaConf.resolve(cfg)
    assert not OmegaConf.is_missing(cfg, "whole")


def test_nested_resolver_preserves_literal_and_stops_missing() -> None:
    calls: list[str] = []

    def outer(value: str) -> str:
        calls.append(value)
        return value

    OmegaConf.register_resolver("test_missing_escape_inner", lambda: r"\???")
    OmegaConf.register_resolver("test_missing_escape_outer", outer)
    cfg = OmegaConf.create(
        {"value": "${test_missing_escape_outer:${test_missing_escape_inner:}}"}
    )
    assert cfg.value == MISSING
    assert not OmegaConf.is_missing(cfg.value)
    assert len(calls) == 2

    OmegaConf.register_resolver(
        "test_missing_escape_inner", lambda: MISSING, replace=True
    )
    with raises(InterpolationToMissingValueError):
        _ = cfg.value
    assert len(calls) == 2


def test_oc_env_default_preserves_escaped_value(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("OMEGACONF_TEST_1302_ABSENT", raising=False)
    cfg = OmegaConf.create({"value": r"${oc.env:OMEGACONF_TEST_1302_ABSENT,\???}"})
    assert cfg.value == MISSING
    assert not OmegaConf.is_missing(cfg.value)


def test_composite_plain_missing_result_respects_selection_policy() -> None:
    OmegaConf.register_resolver("test_missing_escape_fragment", lambda value: value)
    cfg = OmegaConf.create(
        {"value": "${test_missing_escape_fragment:?}${test_missing_escape_fragment:??}"}
    )
    with raises(InterpolationToMissingValueError):
        _ = cfg.value
    assert OmegaConf.select(cfg, "value", throw_on_resolution_failure=False) is None


def test_nested_native_resolver_container_yaml_roundtrip() -> None:
    OmegaConf.register_resolver(
        "test_missing_escape_nested_container",
        lambda: {"tuple": (r"\???", MISSING), "list": ["ordinary", 42]},
    )
    cfg = OmegaConf.create({"value": "${test_missing_escape_nested_container:}"})
    reloaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=True))
    assert reloaded.value["tuple"][0] == r"\???"
    assert reloaded.value["tuple"][1] == MISSING
    assert not OmegaConf.is_missing(reloaded.value["tuple"], 1)
    assert reloaded.value["list"] == ["ordinary", 42]


def test_yaml_quotes_do_not_override_missing_escape() -> None:
    cfg = OmegaConf.create("required: '???'\nliteral: '\\???'\nbackslash: '\\\\???'\n")
    assert OmegaConf.is_missing(cfg, "required")
    assert cfg.literal == MISSING
    assert not OmegaConf.is_missing(cfg, "literal")
    assert cfg.backslash == r"\???"
    assert not OmegaConf.is_missing(cfg, "backslash")


def test_missing_keys_and_dotlist_respect_escaped_literal() -> None:
    cfg = OmegaConf.from_dotlist([r"literal=\???", "required=???"])
    assert OmegaConf.missing_keys(cfg) == {"required"}
    assert cfg.literal == MISSING
    assert not OmegaConf.is_missing(cfg, "literal")


def test_oc_decode_preserves_forwarded_literal() -> None:
    cfg = OmegaConf.create({"literal": r"\???", "decoded": "${oc.decode:${literal}}"})
    assert cfg.decoded == MISSING
    assert not OmegaConf.is_missing(cfg.decoded)
