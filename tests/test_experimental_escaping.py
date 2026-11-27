import copy
import io
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, cast

import attr
import pytest

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf, TupleConfig
from omegaconf.base import Node
from omegaconf.errors import (
    ConfigKeyError,
    GrammarParseError,
    InterpolationResolutionError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    ValidationError,
)
from omegaconf.experimental import (
    _INTERPOLATION_OPEN,
    escape_key,
    escape_value,
    from_input,
    unescape_key,
    unescape_value,
)
from omegaconf.nodes import AnyNode, StringNode

TEXTS = [
    "",
    "ordinary",
    "???",
    r"\???",
    r"\\???",
    "${",
    "${}",
    "${bad:[}",
    "${escaping_probe:}",
    "Cost is ${price}",
    "${${escaping_probe:}}",
    "${escaping_probe:}${escaping_probe:}",
    "Unicode: café\n${price}",
    "\x00${price}",
    r"C:\Users\example",
    "prefix???",
    "???suffix",
]


def test_long_backslash_runs_preserve_transforms_and_match_boundaries() -> None:
    run = "\\" * 16_384
    adjacent_opener = run + "${value}"
    match = _INTERPOLATION_OPEN.match(adjacent_opener)
    assert match is not None and match.group(1) == run
    assert _INTERPOLATION_OPEN.match(adjacent_opener, 1) is None

    for value in (run, adjacent_opener, run + " text ${value}"):
        assert unescape_value(escape_value(value)) == value
        assert unescape_value(value) == value


@pytest.fixture
def calls() -> Any:
    seen: list[str] = []
    OmegaConf.register_resolver(
        "escaping_probe", lambda: seen.append("called") or "EXECUTED", replace=True
    )
    yield seen
    OmegaConf.clear_resolver("escaping_probe")


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("before", range(5))
@pytest.mark.parametrize("after", range(3))
def test_escape_values_preserves_caller_text(
    text: str, before: int, after: int, calls: list[str]
) -> None:
    original = "\\" * before + text + "\\" * after
    escaped = escape_value(original)
    assert type(escaped) is str
    assert unescape_value(escaped) == original
    cfg = OmegaConf.create({"value": escaped})
    assert cfg.value == original
    assert calls == []


@pytest.mark.parametrize("text", TEXTS)
def test_recursive_native_values_and_yaml(text: str, calls: list[str]) -> None:
    original = {"a.b": [text, (text, None, 5)], "${escaping_probe:}": text}
    snapshot = copy.deepcopy(original)
    escaped = escape_value(original)
    assert escaped is not original
    assert escaped["a.b"] is not original["a.b"]
    assert list(escaped) == list(original)
    assert unescape_value(escaped) == original == snapshot
    cfg = OmegaConf.create(escaped)
    assert OmegaConf.to_object(cfg) == original
    stream = io.StringIO()
    OmegaConf.save(cfg, stream)
    # Ordinary YAML sequences reload as lists, including serialized tuples.
    assert OmegaConf.to_object(OmegaConf.load(io.StringIO(stream.getvalue()))) == {
        "a.b": [text, [text, None, 5]],
        "${escaping_probe:}": text,
    }
    assert calls == []


@pytest.mark.parametrize(
    "key",
    [
        "a.b",
        "a[0]",
        "[a]",
        "a:b=c",
        "a b\tc",
        r"a\b",
        '"a"',
        "'a'",
        "a{b}(c)",
        "${x}",
        "???",
    ],
)
def test_key_escaping_selects_literal_key(key: str) -> None:
    path = escape_key(key)
    assert unescape_key(path) == key
    cfg = OmegaConf.create({key: 7})
    assert OmegaConf.select(cfg, path) == 7
    assert list(escape_value(cfg)) == [key]


def test_key_segments_do_not_parse_paths_or_unknown_escapes() -> None:
    assert escape_key("") == unescape_key("") == ""
    assert OmegaConf.select(OmegaConf.create({"": 7}), "[]") == 7
    assert unescape_key(r"a\.b.c") == "a.b.c"
    assert unescape_key(r"a\q") == r"a\q"
    assert unescape_value(r"a\q") == r"a\q"
    assert unescape_value("${escaping_probe:}") == "${escaping_probe:}"
    assert unescape_value(r"\\${x}") == r"\\${x}"


def test_unescape_decoded_missing_string_returns_plain_string() -> None:
    cfg = OmegaConf.create({"value": r"\???"})
    result = unescape_value(cfg.value)
    assert result == "???"
    assert type(result) is str
    assert not OmegaConf.is_missing(cfg, "value")


@pytest.mark.parametrize(
    "factory", [DictConfig, ListConfig, TupleConfig, AnyNode, StringNode]
)
def test_config_copy_escape_and_unescape(factory: Any, calls: list[str]) -> None:
    if factory is DictConfig:
        original = factory(
            {"v": "${escaping_probe:}", "missing": MISSING, "literal": r"\???"}
        )
    elif factory in (ListConfig, TupleConfig):
        original = factory(["${escaping_probe:}", None, r"\???"])
    else:
        original = factory("${escaping_probe:}")

    def get_node(cfg: Node) -> Node:
        if isinstance(cfg, DictConfig):
            return cast(Node, cfg._get_node("v"))
        if isinstance(cfg, (ListConfig, TupleConfig)):
            return cast(Node, cfg._get_node(0))
        return cfg

    OmegaConf.set_readonly(original, True)
    if OmegaConf.is_config(original):
        OmegaConf.set_struct(original, True)
    escaped = escape_value(original)
    assert escaped is not original and type(escaped) is type(original)
    assert OmegaConf.is_readonly(escaped) is True
    assert get_node(escaped)._value() == r"\${escaping_probe:}"
    decoded = unescape_value(escaped)
    assert get_node(decoded)._value() == get_node(original)._value()
    assert get_node(original)._value() == "${escaping_probe:}"
    assert OmegaConf.is_readonly(decoded) is True
    if OmegaConf.is_config(original):
        assert OmegaConf.structural_equality(original, decoded)
        assert OmegaConf.is_struct(decoded) is True
    assert calls == []


def test_subtree_and_ancestors_are_independent(calls: list[str]) -> None:
    source = OmegaConf.create({"sibling": "original", "child": {"v": "${..sibling}"}})
    OmegaConf.set_readonly(source, True)
    escaped = escape_value(source.child)
    assert escaped._get_parent() is not source
    assert OmegaConf.is_readonly(escaped) is True
    assert escaped.v == "${..sibling}"
    decoded = unescape_value(escaped)
    assert decoded.v == "original"
    with pytest.raises(ReadonlyConfigError):
        decoded.v = "changed"
    assert source.child._get_parent() is source
    assert source.child.v == "original"
    assert calls == []


@pytest.mark.parametrize(
    "copy_kind", ["container.copy", "container.deepcopy", "scalar.copy"]
)
@pytest.mark.parametrize(
    "transform, source_value, expected_value, resolved_value",
    [
        (escape_value, "${..sibling}", r"\${..sibling}", "${..sibling}"),
        (unescape_value, r"\${..sibling}", "${..sibling}", "original"),
    ],
    ids=["escape", "unescape"],
)
def test_transforms_copied_nodes_with_ancestor_context(
    copy_kind: str,
    transform: Any,
    source_value: str,
    expected_value: str,
    resolved_value: str,
) -> None:
    source = OmegaConf.create({"sibling": "original", "child": {"v": source_value}})
    OmegaConf.set_readonly(source, True)
    source_child = source.child
    source_node = cast(Node, source_child._get_node("v"))

    if copy_kind == "container.copy":
        copied = source_child.copy()
    elif copy_kind == "container.deepcopy":
        copied = copy.deepcopy(source_child)
    else:
        copied = copy.copy(source_node)

    copied_parent = copied._get_parent()
    copied_value = copied._value() if isinstance(copied, Node) else None
    result = transform(copied)

    assert result is not copied and type(result) is type(copied)
    assert result._get_flag("readonly") is True
    assert copied._get_parent() is copied_parent
    assert copied._value() == copied_value
    assert OmegaConf.is_readonly(source) is True
    assert source.sibling == "original"
    assert source_node._value() == source_value

    ancestor = result
    while (parent := ancestor._get_parent()) is not None:
        ancestor = parent
    assert ancestor is not source
    assert isinstance(ancestor, DictConfig)
    assert ancestor.sibling == "original"

    if isinstance(result, DictConfig):
        result_node = cast(Node, result._get_node("v"))
        assert result_node._value() == expected_value
        assert result.v == resolved_value
        with pytest.raises(ReadonlyConfigError):
            result.v = "changed"
    else:
        assert isinstance(result, Node)
        assert result._value() == expected_value
        assert result._dereference_node()._value() == resolved_value
        with pytest.raises(ReadonlyConfigError):
            result._set_value("changed")


@pytest.mark.parametrize(
    "copy_kind", ["container.copy", "container.deepcopy", "scalar.copy"]
)
def test_failed_transform_leaves_copied_nodes_unchanged(copy_kind: str) -> None:
    source = OmegaConf.create({"sibling": "original", "child": {"v": r"\${"}})
    source_node = cast(Node, source.child._get_node("v"))
    if copy_kind == "container.copy":
        copied = source.child.copy()
    elif copy_kind == "container.deepcopy":
        copied = copy.deepcopy(source.child)
    else:
        copied = copy.copy(source_node)

    original_parent = copied._get_parent()
    original_value = (
        cast(Node, copied._get_node("v"))._value()
        if isinstance(copied, DictConfig)
        else copied._value()
    )
    with pytest.raises(GrammarParseError):
        unescape_value(copied)

    assert copied._get_parent() is original_parent
    if isinstance(copied, DictConfig):
        assert cast(Node, copied._get_node("v"))._value() == original_value
    else:
        assert copied._value() == original_value
    assert source_node._value() == r"\${"
    assert source.sibling == "original"


def test_from_input_accepts_copied_argument_subtree() -> None:
    @dataclass
    class Input:
        text: str

    source = OmegaConf.create(
        {"sibling": "original", "arguments": {"text": "${..sibling}"}}
    )
    OmegaConf.set_readonly(source, True)
    arguments = source.arguments.copy()
    original_parent = arguments._get_parent()
    original_value = cast(Node, arguments._get_node("text"))._value()

    assert from_input(Input, arguments) == Input("${..sibling}")
    assert arguments._get_parent() is original_parent
    assert cast(Node, arguments._get_node("text"))._value() == original_value
    assert source.arguments.text == "original"
    assert source.sibling == "original"
    assert OmegaConf.is_readonly(source) is True


def test_structured_and_union_metadata_is_preserved(calls: list[str]) -> None:
    @dataclass(frozen=True)
    class Input:
        text: str = "${escaping_probe:}"
        choice: str | int = "${escaping_probe:}"
        required: str = MISSING

    source = OmegaConf.structured(Input)
    escaped = escape_value(source)
    assert OmegaConf.get_type(escaped) is Input
    assert escaped.text == escaped.choice == "${escaping_probe:}"
    assert OmegaConf.is_missing(escaped, "required")
    assert OmegaConf.structural_equality(source, unescape_value(escaped))
    assert calls == []


def test_unescaping_config_restores_active_syntax(calls: list[str]) -> None:
    escaped = OmegaConf.create(escape_value({"v": "${escaping_probe:}"}))
    decoded = unescape_value(escaped)
    assert calls == []
    assert decoded.v == "EXECUTED"
    assert calls == ["called"]
    assert escaped.v == "${escaping_probe:}"


def test_unescaping_config_can_restore_missing() -> None:
    escaped = OmegaConf.create(escape_value({"v": "???"}))
    decoded = unescape_value(escaped)
    assert OmegaConf.is_missing(decoded, "v")
    assert not OmegaConf.is_missing(escaped, "v")
    assert escaped.v == "???"


def test_unescaping_tuple_rejects_missing_elements() -> None:
    source = TupleConfig((r"\???",))
    with pytest.raises(ValidationError, match="TupleConfig elements cannot be missing"):
        unescape_value(source)
    assert source[0] == "???"
    assert not OmegaConf.is_missing(source, 0)


def test_failed_transform_does_not_change_source(calls: list[str]) -> None:
    source = OmegaConf.create(escape_value({"v": "${"}))
    OmegaConf.set_readonly(source, True)
    with pytest.raises(GrammarParseError):
        unescape_value(source)
    assert source.v == "${"
    assert OmegaConf.is_readonly(source) is True
    assert calls == []


@pytest.mark.parametrize("transform", [escape_value, unescape_value])
@pytest.mark.parametrize("factory", [list, dict, defaultdict])
def test_cycles_are_rejected(transform: Any, factory: Any) -> None:
    value = factory()
    if isinstance(value, dict):
        value["self"] = value
    else:
        value.append(value)
    with pytest.raises(ValidationError, match="recursive input"):
        transform(value)


@pytest.mark.parametrize("transform", [escape_value, unescape_value])
@pytest.mark.parametrize("factory", [list, tuple, dict])
def test_shared_native_containers_are_copied_once(transform: Any, factory: Any) -> None:
    source: Any = ["${x}"]
    for _ in range(8):
        source = (
            {"a": source, "b": source} if factory is dict else factory([source, source])
        )
    result = transform(source)
    assert result is not source
    for _ in range(8):
        first, second = result.values() if isinstance(result, dict) else result
        assert first is second
        result = first


def test_non_string_values_and_string_enums_are_preserved() -> None:
    class Text(str, Enum):
        VALUE = "${x}"

    value = [Text.VALUE, 5, True, None]
    escaped = escape_value(value)
    assert escaped == value
    assert escaped[0] is Text.VALUE
    assert unescape_value(escaped)[0] is Text.VALUE


@pytest.mark.parametrize(
    "payload",
    [
        {"nested": ["${escaping_probe:}"]},
        ["${escaping_probe:}"],
        ("${escaping_probe:}",),
    ],
)
@pytest.mark.parametrize("transform", [escape_value, unescape_value])
def test_native_payload_in_scalar_node_is_rejected(
    payload: Any, transform: Any, calls: list[str]
) -> None:
    source = AnyNode(payload, flags={"allow_objects": True})
    with pytest.raises(
        ValidationError, match="containers stored in scalar config nodes"
    ):
        transform(source)
    assert source._value() is payload
    assert calls == []


def test_recursive_payload_in_scalar_node_is_rejected() -> None:
    payload: list[Any] = []
    payload.append(payload)
    source = AnyNode(payload, flags={"allow_objects": True})
    for transform in [escape_value, unescape_value]:
        with pytest.raises(ValidationError, match="scalar config nodes"):
            transform(source)
    assert source._value() is payload


@pytest.mark.parametrize("transform", [escape_value, unescape_value])
def test_mixed_node_container_cycle_is_rejected(transform: Any) -> None:
    payload: list[Any] = []
    source = AnyNode(payload, flags={"allow_objects": True})
    payload.append(source)
    with pytest.raises(ValidationError, match="scalar config nodes"):
        transform(payload)
    assert payload[0] is source


@pytest.mark.parametrize("transform", [escape_value, unescape_value])
def test_opaque_payload_in_ancestor_context_is_rejected(transform: Any) -> None:
    payload = ["original"]
    source = OmegaConf.create(
        {
            "sibling": AnyNode(payload, flags={"allow_objects": True}),
            "child": {"text": r"\${..sibling}"},
        }
    )
    child = source.child.copy()
    with pytest.raises(ValidationError, match="scalar config nodes"):
        transform(child)
    assert source.sibling is payload
    assert child._get_parent() is source


@pytest.mark.parametrize("transform", [escape_value, unescape_value])
@pytest.mark.parametrize("structured", [dataclass, attr.define])
def test_raw_structured_payload_in_ancestor_context_is_rejected(
    transform: Any, structured: Any
) -> None:
    @structured
    class Payload:
        value: str = "original"

    payload = Payload()
    source = OmegaConf.create(
        {
            "sibling": AnyNode(payload, flags={"allow_objects": True}),
            "child": {"text": r"\${..sibling}"},
        }
    )
    with pytest.raises(ValidationError, match="raw structured config objects"):
        transform(source.child)
    assert source.sibling is payload


@dataclass
class TextInput:
    text: str

    def __post_init__(self) -> None:
        assert type(self.text) is str


def test_from_input_rejects_opaque_node_containers(calls: list[str]) -> None:
    @dataclass
    class Input:
        payload: Any

    payload = ["${escaping_probe:}", "???"]
    node = AnyNode(payload, flags={"allow_objects": True})
    with pytest.raises(ValidationError, match="scalar config nodes"):
        from_input(Input, {"payload": node})
    assert node._value() is payload
    assert payload == ["${escaping_probe:}", "???"]
    assert calls == []


@pytest.mark.parametrize("text", TEXTS)
def test_from_input_constructs_plain_strings(text: str, calls: list[str]) -> None:
    assert from_input(TextInput, {"text": text}) == TextInput(text)
    assert calls == []


def test_from_input_nested_defaults_and_conversions(calls: list[str]) -> None:
    @dataclass
    class Input:
        child: TextInput
        children: list[TextInput]
        mapping: dict[str, TextInput]
        pair: tuple[TextInput, str]
        number: int
        trusted: str = "default"
        optional: str | None = None
        generated: list[int] = field(default_factory=lambda: [7])

    args = {
        "child": {"text": "???"},
        "children": [{"text": "${"}],
        "mapping": {"a.b": {"text": "${escaping_probe:}"}},
        "pair": ({"text": r"\???"}, "Cost is ${price}"),
        "number": "5",
    }
    snapshot = copy.deepcopy(args)
    result = from_input(Input, args)
    assert result.child == TextInput("???")
    assert result.children == [TextInput("${")]
    assert result.mapping == {"a.b": TextInput("${escaping_probe:}")}
    assert result.pair == (TextInput(r"\???"), "Cost is ${price}")
    assert result.number == 5
    assert result.trusted == "default"
    assert result.optional is None and result.generated == [7]
    assert args == snapshot
    assert calls == []


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("config_input", [False, True])
def test_from_input_escapes_coerced_strings(
    text: str, config_input: bool, calls: list[str]
) -> None:
    arguments = {"text": Path(text)}
    supplied = OmegaConf.create(arguments) if config_input else arguments
    assert from_input(TextInput, supplied) == TextInput(str(Path(text)))
    assert calls == []


@pytest.mark.parametrize(
    "default",
    ["${escaping_probe:}", "${oc.env:HOME}", "${text}", "${${escaping_probe:}}"],
)
def test_from_input_rejects_active_defaults(default: str, calls: list[str]) -> None:
    @dataclass
    class Input:
        text: str
        trusted: str = default

    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(Input, {"text": "caller"})
    assert calls == []
    # A failed call must not change ordinary resolver behavior.
    assert OmegaConf.create({"text": "${escaping_probe:}"}).text == "EXECUTED"
    assert calls == ["called"]


def test_from_input_rejects_converted_schema_defaults(calls: list[str]) -> None:
    @dataclass
    class Input:
        text: str = field(default_factory=lambda: cast(str, Path("${escaping_probe:}")))

    @attr.define
    class AttrInput:
        text: str = attr.field(factory=lambda: cast(str, Path("${escaping_probe:}")))

    for schema in (
        Input,
        Input(),
        OmegaConf.structured(Input),
        AttrInput,
        AttrInput(),
        OmegaConf.structured(AttrInput),
    ):
        with pytest.raises(
            InterpolationResolutionError, match="disabled in from_input"
        ):
            from_input(schema, {})
        assert calls == []


def test_from_input_distinguishes_nested_defaults_from_caller(calls: list[str]) -> None:
    @dataclass
    class Child:
        text: str = field(default_factory=lambda: cast(str, Path("${escaping_probe:}")))

    @dataclass
    class Input:
        child: Child

    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(Input, {"child": {}})
    assert calls == []
    assert from_input(Input, {"child": {"text": Path("${escaping_probe:}")}}) == Input(
        Child("${escaping_probe:}")
    )
    assert calls == []


def test_from_input_allows_escaped_and_overwritten_defaults(calls: list[str]) -> None:
    @dataclass
    class Input:
        escaped: str = r"\${escaping_probe:}"
        overwritten: str = "${escaping_probe:}"

    assert from_input(Input, {"overwritten": "literal"}) == Input(
        "${escaping_probe:}", "literal"
    )
    assert calls == []


@pytest.mark.parametrize("container", [list, tuple, dict])
def test_from_input_blocks_nested_default_resolvers(
    container: Any, calls: list[str]
) -> None:
    @dataclass
    class Input:
        nested: Any = field(
            default_factory=lambda: (
                {"text": "${escaping_probe:}"}
                if container is dict
                else container(["${escaping_probe:}"])
            )
        )

    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(Input, {})
    assert calls == []


def test_from_input_blocks_cached_resolvers(calls: list[str]) -> None:
    @dataclass
    class Input:
        text: str = "${escaping_probe:}"

    schema = OmegaConf.structured(Input)
    OmegaConf.register_resolver(
        "escaping_probe",
        lambda: calls.append("cached") or "EXECUTED",
        use_cache=True,
        replace=True,
    )
    assert schema.text == "EXECUTED"
    calls.clear()
    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(schema, {})
    assert calls == []


def test_from_input_restores_conversion_behavior(calls: list[str]) -> None:
    value = Path("${escaping_probe:}")
    assert from_input(TextInput, {"text": value}) == TextInput(str(value))
    cfg = OmegaConf.merge(OmegaConf.structured(TextInput), {"text": value})
    assert cfg.text == "EXECUTED"
    assert calls == ["called"]


def test_from_input_preserves_enum_types(calls: list[str]) -> None:
    class Choice(str, Enum):
        TEXT = "ordinary"

    @dataclass
    class Input:
        choice: Choice

    result = from_input(Input, {"choice": Choice.TEXT})
    assert result.choice is Choice.TEXT
    assert calls == []


def test_from_input_rejects_raw_structured_caller_objects(calls: list[str]) -> None:
    @dataclass
    class Request:
        text: str

    @dataclass
    class Envelope:
        child: Request

    @attr.define
    class AttrRequest:
        text: str

    @attr.define
    class AttrEnvelope:
        child: AttrRequest

    cases = [
        (Request, Request("${escaping_probe:}")),
        (Envelope, {"child": Request("${escaping_probe:}")}),
        (AttrRequest, AttrRequest("${escaping_probe:}")),
        (AttrEnvelope, {"child": AttrRequest("${escaping_probe:}")}),
    ]
    for schema, arguments in cases:
        snapshot = copy.deepcopy(arguments)
        with pytest.raises(ValidationError, match="raw structured config objects"):
            from_input(schema, arguments)
        assert arguments == snapshot
        assert calls == []


@pytest.mark.parametrize("transform", [escape_value, unescape_value])
def test_transforms_reject_raw_structured_objects(
    transform: Any, calls: list[str]
) -> None:
    @dataclass
    class Request:
        text: str

    @attr.define
    class AttrRequest:
        text: str

    request = Request("${escaping_probe:}")
    attr_request = AttrRequest("${escaping_probe:}")
    for value in (
        request,
        attr_request,
        Request,
        AttrRequest,
        {"nested": [request]},
        (attr_request,),
    ):
        snapshot = copy.deepcopy(value)
        with pytest.raises(ValidationError, match="raw structured config objects"):
            transform(value)
        assert value == snapshot
        assert calls == []

    node = AnyNode(request, flags={"allow_objects": True})
    with pytest.raises(ValidationError, match="raw structured config objects"):
        transform(node)
    assert node._value() is request
    assert request.text == "${escaping_probe:}"
    assert calls == []


def test_from_input_attrs_schema() -> None:
    @attr.define
    class Input:
        text: str
        number: int = 7

    assert from_input(Input, {"text": "???", "number": "5"}) == Input("???", 5)


def test_from_input_literal_annotation() -> None:
    @dataclass
    class Input:
        text: Literal["???", "${x}"]

    assert from_input(Input, {"text": "???"}) == Input("???")
    assert from_input(Input, {"text": "${x}"}) == Input("${x}")


def test_from_input_rejects_missing_unknown_and_invalid_values(
    calls: list[str],
) -> None:
    @dataclass
    class Input:
        number: int

    with pytest.raises(MissingMandatoryValue):
        from_input(Input, {})
    with pytest.raises(ConfigKeyError):
        from_input(Input, {"number": 5, "unknown": "${escaping_probe:}"})
    for value in ["${escaping_probe:}", "???", "${", "bad"]:
        with pytest.raises(ValidationError):
            from_input(Input, {"number": value})
    assert calls == []


def test_from_input_keeps_schema_instance_and_config_input_unchanged() -> None:
    schema = TextInput("default")
    arguments = OmegaConf.create({"text": "${missing}"})
    OmegaConf.set_readonly(arguments, True)
    assert from_input(schema, arguments) == TextInput("${missing}")
    assert schema == TextInput("default")
    assert cast(Node, arguments._get_node("text"))._value() == "${missing}"
    assert OmegaConf.is_readonly(arguments) is True
