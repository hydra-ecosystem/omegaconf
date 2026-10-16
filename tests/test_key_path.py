from itertools import product
from typing import Any

from pytest import mark, raises

from omegaconf import DictConfig, OmegaConf, ValidationError
from omegaconf._key_path import _escape_key, _unescape_key, split_key
from omegaconf.errors import GrammarParseError


@mark.parametrize(
    ("key", "escaped"),
    [
        ("", ""),
        ("plain", "plain"),
        ("café", "café"),
        ("a.b", r"a\.b"),
        ("a[b", r"a\[b"),
        ("a]b", r"a\]b"),
        ("a:b", r"a\:b"),
        ("a=b", r"a\=b"),
        (r"a\b", r"a\\b"),
        ("a\\", "a\\\\"),
        (r"a\.b", r"a\\\.b"),
        (".[]:=\\", r"\.\[\]\:\=\\"),
        ("a b", r"a\ b"),
        ("a\tb", "a\\\tb"),
        ("{}()", r"\{\}\(\)"),
        ("'\"", "\\'\\\""),
        ("${key}", r"$\{key\}"),
    ],
)
def test_key_escaping(key: str, escaped: str) -> None:
    assert _escape_key(key) == escaped
    assert _unescape_key(escaped) == key


@mark.parametrize("characters", list(product("a\\.[]:={}()'\" \t$", repeat=2)))
def test_key_escape_round_trip(characters: tuple[str, ...]) -> None:
    key = "".join(characters)
    assert _unescape_key(_escape_key(key)) == key


@mark.parametrize("key", [r"a\q", r"a\$", "a\\", "a b", "${key}"])
def test_key_unescape_preserves_other_characters(key: str) -> None:
    assert _unescape_key(key) == key


@mark.parametrize("default", [None, False, 0, "fallback", object()])
@mark.parametrize(
    "path",
    [
        "a[b",
        "[a",
        "a[b][",
        "a[b]junk",
        "a[b]junk.c",
        "a[b]]",
        r"\a[b]junk",
        "missing[b",
        "....a[b",
    ],
)
def test_malformed_path_does_not_select_or_update_prefix(
    path: str, default: Any
) -> None:
    original = {"a": {"b": 1}, r"\a": {"b": 2}}
    cfg = OmegaConf.create(original)
    with raises(GrammarParseError, match="Invalid key path"):
        OmegaConf.select(cfg, path)
    assert OmegaConf.select(cfg, path, default=default) is default
    with raises(GrammarParseError, match="Invalid key path"):
        OmegaConf.update(cfg, path, 999)
    assert cfg == original
    assert not OmegaConf.can_select(cfg, path)


@mark.parametrize("entry", ["a[b=3", "a[b]junk=3", "a[b]junk.c=3", r"\a[b=3", "a[b"])
def test_dotlist_validates_all_paths_before_updates(entry: str) -> None:
    original = {"existing": 0, "a": {"b": 1}}
    cfg = OmegaConf.create(original)
    with raises(GrammarParseError, match="Invalid key path"):
        cfg.merge_with_dotlist(["existing=2", entry])
    assert cfg == original


def test_dotlist_type_error_preserves_earlier_updates() -> None:
    cfg = OmegaConf.create({"existing": 0})
    invalid_entry: Any = 42
    with raises(ValueError, match="Input list must be a list or a tuple of strings"):
        cfg.merge_with_dotlist(["existing=2", invalid_entry])
    assert cfg == {"existing": 2}


def test_dotlist_malformed_path_prevents_updates_with_non_string_entry() -> None:
    original = {"existing": 0, "a": {"b": 1}}
    cfg = OmegaConf.create(original)
    invalid_entry: Any = 42
    with raises(GrammarParseError, match="Invalid key path"):
        cfg.merge_with_dotlist(["existing=2", invalid_entry, "a[b=3"])
    assert cfg == original


def test_dotlist_value_error_preserves_earlier_updates() -> None:
    cfg = DictConfig({"a": 0, "b": 0}, element_type=int)
    with raises(ValidationError):
        cfg.merge_with_dotlist(["a=2", "b=invalid"])
    assert cfg == {"a": 2, "b": 0}


def test_from_dotlist_and_cli_reject_malformed_paths() -> None:
    with raises(GrammarParseError, match="Invalid key path"):
        OmegaConf.from_dotlist(["a[b=1"])
    with raises(GrammarParseError, match="Invalid key path"):
        OmegaConf.from_cli(["a[b=1"])


@mark.parametrize(
    ("path", "parts"),
    [
        ("a]b", ["a]b"]),
        ("a[b[c]", ["a", "b[c"]),
        (r"\a[b[c]", [r"\a", "b[c"]),
        (r"a\[b", ["a[b"]),
        ("a[]", ["a", ""]),
        ("a..b", ["a", "", "b"]),
        ("a.[b]", ["a", "", "b"]),
    ],
)
def test_existing_literal_path_spellings(path: str, parts: list[str]) -> None:
    assert split_key(path) == parts
    cfg = OmegaConf.create({})
    OmegaConf.update(cfg, path, 123)
    assert OmegaConf.select(cfg, path) == 123
    node = cfg
    for part in parts[:-1]:
        node = node[part]
    assert node[parts[-1]] == 123
