import copy
import json
import pickle
import re
from dataclasses import dataclass, field
from typing import Any, List

from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationResolutionError,
    InterpolationToMissingValueError,
)
from omegaconf.resolvers.oc.dict import _get_and_validate_dict_input
from tests import Color, User, Users


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param(
            {"foo": "${oc.dict.keys:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            ["a", "b"],
            id="dictconfig",
        ),
        param(
            {"foo": "${oc.dict.keys:bar}", "bar": "${boz}", "boz": {"a": 0, "b": 1}},
            "foo",
            ["a", "b"],
            id="dictconfig_chained_interpolation",
        ),
        param(
            {"a": "${oc.dict.keys:''}", "b": 10},
            "a",
            ["a", "b"],
            id="select_keys_of_root",
        ),
    ],
)
def test_dict_keys(cfg: Any, key: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected
    assert isinstance(val, ListConfig)
    assert val._parent is cfg


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param(
            {"x": "${oc.dict.keys_or_values:y}", "y": "???"},
            "x",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "MissingMandatoryValue raised while resolving interpolation: "
                    "Missing mandatory value: y"
                ),
            ),
            id="select_missing",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:bar}"},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "ConfigKeyError raised while resolving interpolation: "
                    "Key not found: 'bar'"
                ),
            ),
            id="config_key_error",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:bar}", "bar": 0},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "TypeError raised while resolving interpolation: "
                    "`oc.dict.keys_or_values` cannot be applied to objects of type: int"
                ),
            ),
            id="type_error",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:bar}", "bar": DictConfig(None)},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "TypeError raised while resolving interpolation: "
                    "`oc.dict.keys_or_values` cannot be applied to objects of type: NoneType"
                ),
            ),
            id="type_error_dictconfig",
        ),
    ],
)
def test_get_and_validate_dict_input(
    restore_resolvers: Any, cfg: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_resolver(
        "oc.dict.keys_or_values",
        lambda in_dict, _parent_: _get_and_validate_dict_input(
            in_dict, parent=_parent_, resolver_name="oc.dict.keys_or_values"
        ),
    )
    cfg = OmegaConf.create(cfg)
    with expected:
        cfg[key]


@mark.parametrize(
    ("cfg", "key", "expected_val"),
    [
        param(
            {"foo": "${oc.dict.values:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            id="dictconfig",
        ),
        param(
            {
                "foo": "${oc.dict.values:bar}",
                "bar": {"a": {"x": 0, "y": 1}, "b": {"x": 0}},
            },
            "foo",
            [{"x": 0, "y": 1}, {"x": 0}],
            id="dictconfig_deep",
        ),
        param(
            {
                "foo": "${oc.dict.values:bar}",
                "bar": {"key": "${val_ref}"},
                "val_ref": "value",
            },
            "foo",
            ["value"],
            id="dictconfig_with_interpolated_value",
        ),
        param(
            {
                "foo": "${oc.dict.values:bar}",
                "bar": "${boz}",
                "boz": {"a": 0, "b": 1},
            },
            "foo",
            [0, 1],
            id="dictconfig_chained_interpolation",
        ),
    ],
)
def test_dict_values(cfg: Any, key: Any, expected_val: Any) -> None:
    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected_val
    assert isinstance(val, ListConfig)
    assert val._parent is cfg
    assert all(OmegaConf.is_interpolation(val, i) for i in range(len(val)))


def test_dict_values_with_missing_value() -> None:
    cfg = OmegaConf.create({"foo": "${oc.dict.values:bar}", "bar": {"missing": "???"}})
    foo = cfg.foo
    with raises(InterpolationToMissingValueError):
        foo[0]
    cfg.bar.missing = 1
    assert foo[0] == 1


@mark.parametrize(
    "literal_key",
    [
        "a.b",
        "a[b]",
        "a:b",
        "with space",
        "",
        "a\\",
        "a\\.b",
        "'quoted'",
        '"quoted"',
        "${probe:}",
        "???",
        "line\nbreak",
        42,
        True,
        False,
        1.5,
        b"key",
        Color.RED,
        float("nan"),
    ],
)
def test_dict_values_literal_keys(restore_resolvers: Any, literal_key: Any) -> None:
    calls: list[str] = []
    OmegaConf.register_resolver("probe", lambda: calls.append("key") or "target")
    OmegaConf.register_resolver("value", lambda: calls.append("value") or 111)
    cfg = OmegaConf.create(
        {
            "mapping": {literal_key: "${value:}", "target": 222},
            "values": "${oc.dict.values:mapping}",
        }
    )
    values = cfg["values"]
    assert calls == []
    assert list(values) == [111, 222]
    assert calls == ["value"]
    cfg.mapping[literal_key] = {"nested": 333}
    assert values[0] == {"nested": 333}
    cfg.mapping[literal_key] = 444
    assert values[0] == 444
    assert calls == ["value"]


@mark.parametrize("literal_key", [True, 1.5, b"key", Color.RED])
def test_dict_values_distinguish_key_types(literal_key: Any) -> None:
    cfg = OmegaConf.create(
        {
            "mapping": {literal_key: 111, str(literal_key): 222},
            "values": "${oc.dict.values:mapping}",
        }
    )
    assert list(cfg["values"]) == [111, 222]


@mark.parametrize("source_key", ["a:b", "with space", "${probe:}", "a\\", ""])
def test_dict_values_source_path(restore_resolvers: Any, source_key: str) -> None:
    calls: list[str] = []
    OmegaConf.register_resolver("probe", lambda: calls.append("key") or "target")
    OmegaConf.register_resolver("path", lambda: "mapping." + source_key)
    cfg = OmegaConf.create(
        {
            "mapping": {source_key: {"a.b": "${.target}", "target": 111}},
            "keys": "${oc.dict.keys:${path:}}",
            "values": "${oc.dict.values:${path:}}",
        }
    )
    assert list(cfg["keys"]) == ["a.b", "target"]
    values = cfg["values"]
    assert list(values) == [111, 111]
    cfg.mapping[source_key].target = 222
    assert list(values) == [222, 222]
    assert calls == []


@mark.parametrize(
    "literal_key",
    ["ordinary", "a.b", "${probe:}", "", True, 42, 1.5, b"key", Color.RED],
)
@mark.parametrize(
    "roundtrip", ["copy", "pickle", "container", "yaml", "references_json"]
)
def test_dict_values_saved_references(literal_key: Any, roundtrip: str) -> None:
    cfg = OmegaConf.create(
        {
            "mapping": {literal_key: 111},
            "values": "${oc.dict.values:mapping}",
        }
    )
    cfg.saved = cfg["values"]
    if roundtrip == "copy":
        loaded = copy.deepcopy(cfg)
    elif roundtrip == "pickle":
        loaded = pickle.loads(pickle.dumps(cfg))
    elif roundtrip == "container":
        loaded = OmegaConf.create(OmegaConf.to_container(cfg, resolve=False))
    elif roundtrip == "references_json":
        loaded = copy.deepcopy(cfg)
        loaded.saved = json.loads(
            json.dumps(OmegaConf.to_container(cfg.saved, resolve=False))
        )
    else:
        loaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=False))
        if literal_key is Color.RED:
            literal_key = "RED"  # YAML converts Enum keys to names.
    assert isinstance(loaded, DictConfig)
    loaded.mapping[literal_key] = 222
    assert list(loaded.saved) == [222]
    loaded.mapping[literal_key] = 333
    assert list(loaded.saved) == [333]
    assert cfg.mapping[next(iter(cfg.mapping))] == 111


def test_dict_values_follow_replaced_source() -> None:
    cfg = OmegaConf.create(
        {
            "first": {"a.b": 111},
            "second": {"a.b": 222},
            "mapping": "${first}",
            "values": "${oc.dict.values:mapping}",
        }
    )
    values = cfg["values"]
    cfg.mapping = "${second}"
    assert list(values) == [222]
    cfg.second = {"a.b": 333}
    assert list(values) == [333]


def test_dict_values_saved_nested_update() -> None:
    cfg = OmegaConf.create(
        {
            "mapping": {"a.b": {"x": 111}},
            "values": "${oc.dict.values:mapping}",
        }
    )
    cfg.saved = cfg["values"]
    OmegaConf.update(cfg, "saved[0].x", 222)
    assert cfg.mapping["a.b"].x == 222


def test_dict_values_saved_update_through_value_interpolation() -> None:
    cfg = OmegaConf.create(
        {
            "mapping": {"a.b": "${target}"},
            "target": {"x": 111},
            "values": "${oc.dict.values:mapping}",
        }
    )
    cfg.saved = cfg["values"]
    OmegaConf.update(cfg, "saved[0].x", 222)
    assert cfg.target.x == 222


def test_dict_values_saved_update_resolver_source(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver(
        "make", lambda _parent_: OmegaConf.create({"a.b": {"x": 111}}, parent=_parent_)
    )
    cfg = OmegaConf.create(
        {"mapping": "${make:}", "values": "${oc.dict.values:mapping}"}
    )
    cfg.saved = cfg["values"]
    OmegaConf.update(cfg, "saved[0].x", 222)
    assert cfg.saved[0].x == 222
    assert cfg.mapping["a.b"].x == 111


def test_dict_values_saved_update_rejects_non_dict_source() -> None:
    cfg = OmegaConf.create(
        {"mapping": {"a.b": {"x": 111}}, "values": "${oc.dict.values:mapping}"}
    )
    cfg.saved = cfg["values"]
    cfg.mapping = []
    with raises(
        InterpolationResolutionError, match="oc.dict.values requires a DictConfig"
    ):
        OmegaConf.update(cfg, "saved[0].x", 222)


@mark.parametrize("roundtrip", [False, True])
def test_dict_values_deleted_key(roundtrip: bool) -> None:
    cfg = OmegaConf.create(
        {"mapping": {Color.RED: 111, "RED": 222}, "values": "${oc.dict.values:mapping}"}
    )
    cfg.saved = cfg["values"]
    if roundtrip:
        cfg = OmegaConf.create(OmegaConf.to_container(cfg, resolve=False))
    assert isinstance(cfg, DictConfig)
    del cfg.mapping[Color.RED]
    with raises(InterpolationKeyError):
        cfg.saved[0]
    assert cfg.saved[1] == 222
    cfg.mapping[Color.RED] = 333
    assert cfg.saved[0] == 333


@mark.parametrize(
    "expression",
    ["${oc.dict._value:abc}", "${oc.dict._value:W10}", "${oc.dict._value:WzEsIHt9XQ}"],
)
def test_dict_values_unresolved_serialization_does_not_evaluate(
    expression: str,
) -> None:
    cfg = OmegaConf.create({"value": expression})
    assert OmegaConf.to_container(cfg, enum_to_str=True) == {"value": expression}


def test_dict_values_nan_key_roundtrip() -> None:
    key = float("nan")
    cfg = OmegaConf.create(
        {"mapping": {key: 111}, "values": "${oc.dict.values:mapping}"}
    )
    cfg.saved = cfg["values"]
    loaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=False))
    loaded.mapping[next(iter(loaded.mapping))] = 222
    assert list(loaded.saved) == [222]


def test_dict_values_distinct_nan_keys() -> None:
    first, second = float("nan"), float("nan")
    cfg = OmegaConf.create(
        {"mapping": {first: 111, second: 222}, "values": "${oc.dict.values:mapping}"}
    )
    values = cfg["values"]
    assert list(values) == [111, 222]
    del cfg.mapping[first]
    with raises(InterpolationKeyError):
        values[0]
    assert values[1] == 222


def test_dict_values_distinct_nan_keys_container_roundtrip() -> None:
    first, second = float("nan"), float("nan")
    cfg = OmegaConf.create(
        {"mapping": {first: 111, second: 222}, "values": "${oc.dict.values:mapping}"}
    )
    cfg.saved = cfg["values"]
    loaded = OmegaConf.create(OmegaConf.to_container(cfg, resolve=False))
    assert isinstance(loaded, DictConfig)
    assert list(loaded.saved) == [111, 222]
    del loaded.mapping[first]
    with raises(InterpolationKeyError):
        loaded.saved[0]
    assert loaded.saved[1] == 222


def test_dict_values_typed_container_yaml_roundtrip() -> None:
    @dataclass
    class Typed:
        mapping: dict[Color, User] = field(default_factory=dict)
        values: list[User] = field(default_factory=list)
        saved: list[User] = field(default_factory=list)

    cfg = OmegaConf.structured(
        Typed(
            mapping={Color.RED: User(name="red", age=111)},
            values="${oc.dict.values:mapping}",  # type: ignore[arg-type]
        )
    )
    cfg.saved = cfg["values"]

    yaml_loaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=False))
    yaml_loaded.mapping.RED.age = 222
    assert yaml_loaded.saved[0].age == 222

    primitive = OmegaConf.to_container(cfg, resolve=False, enum_to_str=True)
    primitive_loaded = OmegaConf.create(primitive)
    assert isinstance(primitive_loaded, DictConfig)
    primitive_loaded.mapping.RED.age = 333
    assert primitive_loaded.saved[0].age == 333


def test_dict_values_distinct_nan_keys_enum_to_str_container_roundtrip() -> None:
    first, second = float("nan"), float("nan")
    cfg = OmegaConf.create(
        {
            "mapping": {first: 111, second: 222},
            "values": "${oc.dict.values:mapping}",
        }
    )
    cfg.saved = cfg["values"]
    loaded = OmegaConf.create(
        OmegaConf.to_container(cfg, resolve=False, enum_to_str=True)
    )
    assert isinstance(loaded, DictConfig)
    source_keys = list(loaded.mapping)

    assert list(loaded.saved) == [111, 222]
    loaded.mapping[source_keys[1]] = 333
    assert list(loaded.saved) == [111, 333]
    del loaded.mapping[source_keys[0]]
    with raises(InterpolationKeyError):
        loaded.saved[0]
    assert loaded.saved[1] == 333


@mark.parametrize("eager", [False, True])
def test_dict_values_resolution_context(eager: bool) -> None:
    cfg = OmegaConf.create(
        {
            "outer": {
                "mapping": {"a.b": "${.target}", "target": "${..target}"},
                "target": 111,
                "values": "${oc.dict.values:.mapping}",
            }
        }
    )
    cfg.outer.saved = cfg.outer["values"]
    del cfg.outer["values"]
    if eager:
        OmegaConf.resolve(cfg)
        assert OmegaConf.to_container(cfg.outer.saved, resolve=False) == [111, 111]
    else:
        cfg = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=False))
        cfg.outer.target = 222
        assert list(cfg.outer.saved) == [222, 222]


def test_dict_values_reject_parent_reference(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("root", lambda _root_: _root_)
    cfg = OmegaConf.create(
        {"mapping": {"key": "${root:}"}, "values": "${oc.dict.values:mapping}"}
    )
    with raises(InterpolationResolutionError, match="Interpolation to parent node"):
        cfg["values"][0]


def test_dict_values_opaque_resolver_result(restore_resolvers: Any) -> None:
    cfg = OmegaConf.create(
        {"mapping": {Color.RED: 111}, "values": "${oc.dict.values:mapping}"}
    )
    references = OmegaConf.to_container(cfg["values"], resolve=False)
    assert isinstance(references, list)
    reference = references[0]
    OmegaConf.register_resolver("literal", lambda: reference)
    cfg.text = "${literal:}"
    result = OmegaConf.to_container(cfg, resolve=True, enum_to_str=True)
    assert isinstance(result, dict)
    assert result["text"] == reference
    assert reference in OmegaConf.to_yaml(cfg, resolve=True)


@mark.parametrize(
    ("make_resolver", "key", "expected"),
    [
        param(
            lambda _parent_: OmegaConf.create({"x": 1}, parent=_parent_),
            0,
            1,
            id="basic",
        ),
        param(
            lambda _parent_: OmegaConf.create({"x": "${y}", "y": 1}, parent=_parent_),
            0,
            999,  # referring to the `y` node from the global config
            id="inter_abs",
        ),
        param(
            lambda _parent_: OmegaConf.create({"x": "${.y}", "y": 1}, parent=_parent_),
            0,
            1,
            id="inter_rel",
        ),
        param(lambda: OmegaConf.create({"x": 1}), 0, 1, id="basic_no_parent"),
        param(
            lambda: OmegaConf.create({"x": "${y}", "y": 1}),
            0,
            1,  # no parent => referring to the local `y` node in the generated config
            id="inter_abs_no_parent",
        ),
        param(
            lambda: OmegaConf.create({"x": "${.y}", "y": 1}),
            0,
            1,
            id="inter_rel_no_parent",
        ),
    ],
)
def test_dict_values_dictconfig_resolver_output(
    restore_resolvers: Any, make_resolver: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_resolver("make", make_resolver)
    cfg = OmegaConf.create(
        {
            "foo": "${oc.dict.values:bar}",
            "bar": "${make:}",
            "y": 999,
        }
    )

    assert cfg.foo[key] == expected


def test_dict_values_are_typed() -> None:
    cfg = OmegaConf.create(
        {
            "x": "${oc.dict.values: y.name2user}",
            "y": Users(
                name2user={
                    "john": User(name="john", age=30),
                    "jane": User(name="jane", age=33),
                }
            ),
        }
    )
    x = cfg.x
    assert x._metadata.ref_type == List[User]
    assert x._metadata.element_type == User


@mark.parametrize(
    ("cfg", "expected"),
    [
        param({"x": "${oc.dict.values:y}", "y": {"a": 1}}, [1], id="values_inter"),
        param({"x": "${oc.dict.keys:y}", "y": {"a": 1}}, ["a"], id="keys_inter"),
    ],
)
def test_readonly_parent(cfg: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_readonly(cfg, True)
    assert cfg.x == expected


@mark.parametrize(
    ("cfg", "expected"),
    [
        param(
            {"outer": {"x": "${oc.dict.values:.y}", "y": {"a": 1}}},
            [1],
            id="values_inter",
        ),
        param(
            {"outer": {"x": "${oc.dict.keys:.y}", "y": {"a": 1}}},
            ["a"],
            id="keys_inter",
        ),
        param(
            {"outer": {"x": "${oc.dict.values:..y}"}, "y": {"a": 1}},
            [1],
            id="parent_values_inter",
        ),
        param(
            {"outer": {"x": "${oc.dict.keys:..y}"}, "y": {"a": 1}},
            ["a"],
            id="parent_keys_inter",
        ),
    ],
)
def test_relative_path(cfg: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    assert cfg.outer.x == expected


@mark.parametrize(
    ("cfg", "expected"),
    [
        param(
            {"x": "${sum:${oc.dict.values:y}}", "y": {"one": 1, "two": 2}},
            3,
            id="values",
        ),
        param(
            {"x": "${sum:${oc.dict.keys:y}}", "y": {1: "one", 2: "two"}},
            3,
            id="keys",
        ),
    ],
)
def test_nested_oc_dict(restore_resolvers: Any, cfg: Any, expected: Any) -> None:
    OmegaConf.register_resolver("sum", sum)
    cfg = OmegaConf.create(cfg)
    assert cfg.x == expected


@mark.parametrize(
    "cfg",
    [
        param({"x": "${oc.dict.keys:[]}"}, id="list"),
        param({"x": "${oc.dict.keys:${bool}}", "bool": True}, id="bool_interpolation"),
        param({"x": "${oc.dict.keys:int}", "int": 0}, id="int_select"),
    ],
)
def test_dict_keys_invalid_type(cfg: Any) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(InterpolationResolutionError, match="TypeError"):
        cfg.x


@mark.parametrize(
    "cfg",
    [
        param({"x": "${oc.dict.values:[]}"}, id="list"),
        param(
            {"x": "${oc.dict.values:${bool}}", "bool": True}, id="bool_interpolation"
        ),
        param({"x": "${oc.dict.values:int}", "int": 0}, id="int_select"),
    ],
)
def test_dict_values_invalid_type(cfg: Any) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(InterpolationResolutionError, match="TypeError"):
        cfg.x
