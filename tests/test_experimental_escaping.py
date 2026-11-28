import copy
import io
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, cast

import attr
import pytest

from omegaconf import MISSING, OmegaConf, TupleConfig
from omegaconf.errors import (
    ConfigKeyError,
    GrammarParseError,
    InterpolationResolutionError,
    MissingMandatoryValue,
    ValidationError,
)
from omegaconf.experimental import (
    escape_key,
    escape_value,
    from_input,
    unescape_key,
    unescape_value,
)
from omegaconf.nodes import AnyNode, StringNode

EXPRESSION = "${escaping_probe:}"


@dataclass
class Text:
    text: str

    def __post_init__(self) -> None:
        assert type(self.text) is str


@attr.define
class AttrText:
    text: str


class Choice(str, Enum):
    NORMAL = "ordinary"
    EXPRESSION = EXPRESSION
    MISSING = "???"


@pytest.fixture
def calls() -> Any:
    seen: list[str] = []
    OmegaConf.register_resolver(
        "escaping_probe", lambda: seen.append("called") or "EXECUTED", replace=True
    )
    yield seen
    OmegaConf.clear_resolver("escaping_probe")


@pytest.mark.parametrize(
    "text",
    ["", EXPRESSION, r"\${x}", r"\\${x}", "???", r"\???", "${", "a ${x}${y}\\"],
)
def test_value_escape_round_trip(text: str, calls: list[str]) -> None:
    escaped = escape_value(text)
    assert unescape_value(escaped) == text
    assert OmegaConf.create({"text": escaped}).text == text
    assert calls == []


def test_long_backslash_boundary() -> None:
    text = "\\" * 16_384 + " text ${x}"
    assert OmegaConf.create({"text": escape_value(text)}).text == text


def test_recursive_values_and_yaml(calls: list[str]) -> None:
    raw = {"a.b": [EXPRESSION, ("???", None, 5)], EXPRESSION: "${"}
    escaped = escape_value(raw)
    assert escaped is not raw and escaped["a.b"] is not raw["a.b"]
    assert unescape_value(escaped) == raw
    cfg = OmegaConf.create(escaped)
    assert OmegaConf.to_object(cfg) == raw
    stream = io.StringIO()
    OmegaConf.save(cfg, stream)
    assert OmegaConf.to_object(OmegaConf.load(io.StringIO(stream.getvalue()))) == {
        "a.b": [EXPRESSION, ["???", None, 5]],
        EXPRESSION: "${",
    }
    assert calls == []


def test_key_helpers() -> None:
    key = "a.b[c]:=\\ "
    assert unescape_key(escape_key(key)) == key
    assert OmegaConf.select(OmegaConf.create({key: 7}), escape_key(key)) == 7
    assert escape_key("") == unescape_key("") == ""
    assert unescape_key(r"a\q") == r"a\q"


def test_scalar_boundaries() -> None:
    assert unescape_value(r"a\q") == r"a\q"
    assert unescape_value(r"\\${x}") == r"\\${x}"
    assert escape_value(Choice.EXPRESSION) is Choice.EXPRESSION
    decoded = unescape_value(OmegaConf.create({"text": r"\???"}).text)
    assert decoded == "???" and type(decoded) is str
    node = StringNode(EXPRESSION)
    assert unescape_value(escape_value(node))._value() == node._value() == EXPRESSION


def test_config_metadata_and_missing_are_preserved(calls: list[str]) -> None:
    @dataclass(frozen=True)
    class Schema:
        text: str = EXPRESSION
        choice: str | int = EXPRESSION
        required: str = MISSING

    source = OmegaConf.create(
        {"schema": OmegaConf.structured(Schema), "values": [EXPRESSION, (r"\???",)]}
    )
    OmegaConf.set_readonly(source, True)
    OmegaConf.set_struct(source, True)
    escaped = escape_value(source)
    assert escaped.schema.text == escaped.schema.choice == EXPRESSION
    assert OmegaConf.get_type(escaped.schema) is Schema
    assert OmegaConf.is_missing(escaped.schema, "required")
    assert escaped["values"][1][0] == r"\???"
    restored = unescape_value(escaped)
    assert OmegaConf.structural_equality(source, restored)
    assert OmegaConf.is_readonly(restored) and OmegaConf.is_struct(restored)
    assert calls == []


@pytest.mark.parametrize("scalar", [False, True])
def test_detached_copies_keep_independent_ancestor_context(scalar: bool) -> None:
    source = OmegaConf.create(
        {"sibling": "original", "child": {"text": r"\${..sibling}"}}
    )
    OmegaConf.set_readonly(source, True)
    node = copy.copy(source.child._get_node("text")) if scalar else source.child.copy()
    parent = node._get_parent()
    original = node._value() if scalar else node._get_node("text")._value()
    result = unescape_value(node)
    assert result._get_parent() is not parent
    assert node._get_parent() is parent
    assert (node._value() if scalar else node._get_node("text")._value()) == original
    text = result._dereference_node()._value() if scalar else result.text
    assert text == "original"
    assert OmegaConf.is_readonly(result)
    assert source.child._get_node("text")._value() == r"\${..sibling}"


def test_failed_unescape_leaves_source_unchanged() -> None:
    root = OmegaConf.create({"child": {"text": r"\${"}})
    source = root.child.copy()
    parent = source._get_parent()
    with pytest.raises(GrammarParseError):
        unescape_value(source)
    assert source._get_parent() is parent
    assert OmegaConf.to_container(source, resolve=False) == {"text": r"\${"}
    assert OmegaConf.to_container(root, resolve=False) == {"child": {"text": r"\${"}}
    with pytest.raises(ValidationError, match="TupleConfig elements cannot be missing"):
        unescape_value(TupleConfig((r"\???",)))


def test_shared_native_copies_and_cycles() -> None:
    child = [EXPRESSION]
    source = {"pair": (child, child), "alias": child}
    result = escape_value(source)
    assert result["pair"][0] is result["pair"][1] is result["alias"]
    assert result["alias"] is not child
    assert unescape_value(result) == source
    recursive: dict[str, Any] = defaultdict(list)
    recursive["self"] = recursive
    with pytest.raises(ValidationError, match="recursive input"):
        escape_value(recursive)


@pytest.mark.parametrize(
    "payload, message",
    [([EXPRESSION], "scalar config nodes"), (Text(EXPRESSION), "raw structured")],
)
def test_unsupported_payload_in_ancestor_context(payload: Any, message: str) -> None:
    source = OmegaConf.create(
        {
            "sibling": AnyNode(payload, flags={"allow_objects": True}),
            "child": {"text": r"\${..sibling}"},
        }
    )
    with pytest.raises(ValidationError, match=message):
        unescape_value(source.child)
    assert source.sibling is payload


def test_from_input_nested_validation_and_context_reset(calls: list[str]) -> None:
    @dataclass
    class Request:
        child: Text
        texts: list[str]
        count: int = 1
        choice: Choice = Choice.NORMAL
        generated: list[int] = field(default_factory=lambda: [7])
        missing_choice: Choice = Choice.NORMAL

    args = {
        "child": {"text": "???"},
        "texts": [EXPRESSION, "${"],
        "count": "5",
        "choice": Choice.NORMAL,
        "missing_choice": "???",
    }
    snapshot = copy.deepcopy(args)
    result = from_input(Request, args)
    assert result == Request(
        Text("???"), [EXPRESSION, "${"], 5, missing_choice=Choice.MISSING
    )
    assert result.choice is Choice.NORMAL
    assert result.missing_choice is Choice.MISSING
    assert from_input(AttrText, {"text": "???"}) == AttrText("???")
    assert args == snapshot and calls == []
    cfg = OmegaConf.merge(OmegaConf.structured(Text), {"text": Path(EXPRESSION)})
    assert cfg.text == "EXECUTED" and calls == ["called"]


def test_interpolation_string_enum_remains_literal(calls: list[str]) -> None:
    escaped = escape_value({"choice": Choice.EXPRESSION})
    assert escaped["choice"] is Choice.EXPRESSION
    exported = cast(dict[str, Any], OmegaConf.to_object(OmegaConf.create(escaped)))
    assert exported["choice"] is Choice.EXPRESSION

    @dataclass
    class Request:
        choice: Choice

    result = from_input(Request, {"choice": Choice.EXPRESSION})
    assert result.choice is Choice.EXPRESSION
    assert calls == []


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ({"text": Path(EXPRESSION)}, EXPRESSION),
        (OmegaConf.create({"text": Path(EXPRESSION)}), EXPRESSION),
        ({"text": Path("???")}, "???"),
    ],
)
def test_from_input_escapes_converted_caller_text(
    arguments: Any, expected: str, calls: list[str]
) -> None:
    assert from_input(Text, arguments) == Text(expected)
    assert calls == []


@pytest.mark.parametrize(
    "default", [EXPRESSION, "${oc.env:UNUSED_ENV,fallback}", "${text}"]
)
def test_from_input_blocks_active_defaults_and_restores_context(
    default: str, calls: list[str]
) -> None:
    @dataclass
    class Request:
        text: str = "caller"
        active: str = default

    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(Request, {})
    assert calls == []
    assert OmegaConf.create({"text": EXPRESSION}).text == "EXECUTED"


@dataclass
class PathDefault:
    text: str = field(default_factory=lambda: cast(str, Path(EXPRESSION)))


@attr.define
class AttrPathDefault:
    text: str = attr.field(factory=lambda: cast(str, Path(EXPRESSION)))


@pytest.mark.parametrize(
    "schema",
    [PathDefault, PathDefault(), OmegaConf.structured(PathDefault), AttrPathDefault],
)
def test_from_input_rejects_converted_schema_defaults(
    schema: Any, calls: list[str]
) -> None:
    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(schema, {})
    assert calls == []


def test_nested_defaults_and_caller_conversions_are_distinct(calls: list[str]) -> None:
    @dataclass
    class Request:
        child: PathDefault

    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(Request, {"child": {}})
    assert from_input(Request, {"child": {"text": Path(EXPRESSION)}}) == Request(
        PathDefault(EXPRESSION)
    )
    assert calls == []


def test_escaped_overwritten_and_cached_defaults(calls: list[str]) -> None:
    assert from_input(Text(r"\${escaping_probe:}"), {}) == Text(EXPRESSION)
    assert from_input(Text(EXPRESSION), {"text": "caller"}) == Text("caller")
    assert calls == []
    OmegaConf.register_resolver(
        "escaping_probe",
        lambda: calls.append("called") or "EXECUTED",
        use_cache=True,
        replace=True,
    )
    schema = OmegaConf.structured(Text(EXPRESSION))
    assert schema.text == "EXECUTED"
    calls.clear()
    with pytest.raises(InterpolationResolutionError, match="disabled in from_input"):
        from_input(schema, {})
    assert calls == []


@pytest.mark.parametrize(
    "value, message",
    [
        (Text(EXPRESSION), "raw structured"),
        (AttrText(EXPRESSION), "raw structured"),
        (AnyNode([EXPRESSION], flags={"allow_objects": True}), "scalar config nodes"),
    ],
)
def test_rejects_unsupported_caller_values(
    value: Any, message: str, calls: list[str]
) -> None:
    with pytest.raises(ValidationError, match=message):
        escape_value(value)
    with pytest.raises(ValidationError, match=message):
        from_input(Text, {"text": value})
    assert calls == []


def test_from_input_keeps_validation_and_literal_annotations(calls: list[str]) -> None:
    @dataclass
    class Request:
        count: int
        text: Literal["???", "${x}"] = "???"

    assert from_input(Request, {"count": "5", "text": "${x}"}) == Request(5, "${x}")
    with pytest.raises(MissingMandatoryValue):
        from_input(Request, {})
    with pytest.raises(ConfigKeyError):
        from_input(Request, {"count": 5, "unknown": EXPRESSION})
    with pytest.raises(ValidationError):
        from_input(Request, {"count": EXPRESSION})
    assert calls == []


def test_from_input_preserves_schema_and_copied_arguments() -> None:
    schema = Text("default")
    source = OmegaConf.create(
        {"sibling": "original", "arguments": {"text": "${..sibling}"}}
    )
    OmegaConf.set_readonly(source, True)
    arguments = source.arguments.copy()
    assert from_input(schema, arguments) == Text("${..sibling}")
    assert schema == Text("default")
    assert arguments._get_parent() is source
    assert source.arguments._get_node("text")._value() == "${..sibling}"
    assert OmegaConf.is_readonly(source)
