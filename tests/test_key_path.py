from itertools import product

from pytest import mark

from omegaconf._key_path import _escape_key, _unescape_key


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
    ],
)
def test_key_escaping(key: str, escaped: str) -> None:
    assert _escape_key(key) == escaped
    assert _unescape_key(escaped) == key


@mark.parametrize("characters", product("a\\.[]:=", repeat=2))
def test_key_escape_round_trip(characters: tuple[str, ...]) -> None:
    key = "".join(characters)
    assert _unescape_key(_escape_key(key)) == key


@mark.parametrize("key", [r"a\q", r"a\$", "a\\", "a b", "${key}"])
def test_key_unescape_preserves_other_characters(key: str) -> None:
    assert _unescape_key(key) == key
