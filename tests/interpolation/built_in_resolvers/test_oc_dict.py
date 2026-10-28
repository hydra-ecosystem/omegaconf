import re
from itertools import product
from typing import Any, List

from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import (
    InterpolationResolutionError,
    InterpolationToMissingValueError,
)
from omegaconf.resolvers.oc.dict import _get_and_validate_dict_input
from tests import Color, User, Users


@mark.parametrize("resolver", ["oc.dict.keys", "oc.dict.values"])
@mark.parametrize("path", ["a[b", "a[b]junk"])
def test_dict_resolvers_reject_malformed_path(resolver: str, path: str) -> None:
    cfg = OmegaConf.create(
        {"a": {"b": {"key": 10}}, "path": path, "result": "${" + resolver + ":${path}}"}
    )
    with raises(InterpolationResolutionError, match="GrammarParseError"):
        cfg.result


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
    ("cfg", "key", "expected_val", "expected_content"),
    [
        param(
            {"foo": "${oc.dict.values:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            ["${bar.a}", "${bar.b}"],
            id="dictconfig",
        ),
        param(
            {
                "foo": "${oc.dict.values:bar}",
                "bar": {"a": {"x": 0, "y": 1}, "b": {"x": 0}},
            },
            "foo",
            [{"x": 0, "y": 1}, {"x": 0}],
            ["${bar.a}", "${bar.b}"],
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
            ["${bar.key}"],
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
            ["${bar.a}", "${bar.b}"],
            id="dictconfig_chained_interpolation",
        ),
    ],
)
def test_dict_values(
    cfg: Any, key: Any, expected_val: Any, expected_content: Any
) -> None:
    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected_val
    assert isinstance(val, ListConfig)
    assert val._parent is cfg
    content = val._content
    assert content == expected_content


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
        "plain",
        "a.b",
        "a[b]",
        "a]b",
        "a:b",
        "a=b",
        r"a\b",
        r"a\.b",
        "a\\",
        "",
        "a b",
        " a ",
        "a\tb",
        "a{b}",
        "a(b)",
        "a'b",
        'a"b',
        "${target}",
        "${probe:}",
        "${oc.env:HOME}",
        "a\nb",
        "a\rb",
    ],
)
def test_dict_values_escape_key(literal_key: str) -> None:
    cfg = OmegaConf.create(
        {
            "mapping": {literal_key: "${.target}", "a": {"b": 999}, "target": 111},
            "values": "${oc.dict.values:mapping}",
        }
    )
    values = cfg["values"]
    assert isinstance(values, ListConfig)
    assert values[0] == 111
    cfg.mapping.target = 222
    assert values[0] == 222

    cfg.mapping[literal_key] = {"x": 333}
    cfg.saved = values
    OmegaConf.update(cfg, "saved[0].x", 444)
    assert cfg.mapping[literal_key].x == 444

    loaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=False))
    loaded.mapping[literal_key].x = 555
    assert loaded.saved[0].x == 555


@mark.parametrize("source_key", ["a:b", "a.b", "a[b]", r"a\b", "", "a b", "${target}"])
@mark.parametrize("relative", [False, True])
def test_dict_values_escape_source_path(source_key: str, relative: bool) -> None:
    path = "mapping[" + source_key.replace("]", r"\]") + "]"
    if relative:
        path = "." + path
    cfg = OmegaConf.create(
        {
            "mapping": {source_key: {"x": 111}},
            "path": path.replace("${", r"\${"),
            "values": "${oc.dict.values:${path}}",
        }
    )
    values = cfg["values"]
    assert list(values) == [111]
    cfg.mapping[source_key].x = 222
    assert list(values) == [222]
    cfg.saved = values
    loaded = OmegaConf.create(OmegaConf.to_yaml(cfg, resolve=False))
    loaded.mapping[source_key].x = 333
    assert list(loaded.saved) == [333]


def test_dict_values_literal_keys_do_not_interpolate(restore_resolvers: Any) -> None:
    calls = []
    OmegaConf.register_resolver("probe", lambda: calls.append(True) or "target")
    cfg = OmegaConf.create(
        {
            "mapping": {"${target}": 111, "${probe:}": 222, "chosen": 333},
            "target": "chosen",
            "values": "${oc.dict.values:mapping}",
        }
    )
    assert list(cfg["values"]) == [111, 222, 333]
    assert calls == []


@mark.parametrize("characters", list(product("a\\.[]:={}()'\" \t$", repeat=2)))
def test_dict_values_literal_key_combinations(characters: tuple[str, ...]) -> None:
    key = "".join(characters)
    cfg = OmegaConf.create(
        {"mapping": {key: 111}, "values": "${oc.dict.values:mapping}"}
    )
    assert list(cfg["values"]) == [111]


@mark.parametrize("path", ["", "."])
def test_dict_values_root_path(path: str) -> None:
    cfg = OmegaConf.create(
        {"first": 111, "path": path, "values": "${oc.dict.values:${path}}"}
    )
    values = cfg["values"]
    assert values[0] == 111
    cfg.first = 222
    assert values[0] == 222


@mark.parametrize("mapping", [{1: 111}, DictConfig({Color.RED: 111}, key_type=Color)])
def test_dict_values_supported_non_string_keys(mapping: Any) -> None:
    cfg = OmegaConf.create({"mapping": mapping, "values": "${oc.dict.values:mapping}"})
    assert list(cfg["values"]) == [111]


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
