"""Parsing and escaping of config key paths."""

import re
from dataclasses import dataclass

from .errors import GrammarParseError


@dataclass(frozen=True)
class NodeInterpolationKey:
    raw: str
    parts: tuple[str, ...]
    relative_dots: int


# Fast path for keys without backslashes.
KEY_PATH_HEAD = re.compile(r"(\.)*[^.[]*")
KEY_PATH_OTHER = re.compile(r"\.([^.[]*)|\[(.*?)\]")

# Characters recognised after a backslash in key paths and dotlist entries.
# \. -> literal dot, \[ -> literal [, \] -> literal ], \= -> literal =
# Any other character after \ passes through unchanged (including \ itself).
_ESCAPABLE = frozenset(".[]=")


def _escape_key(key: str) -> str:
    """Escape path punctuation in one interpolation key segment."""
    return re.sub(r"([\\.\[\]:={}()'\" \t])", r"\\\1", key)


def _unescape_key(key: str) -> str:
    """Remove recognized escapes from one interpolation key segment."""
    return re.sub(r"\\([\\.\[\]:={}()'\" \t])", r"\1", key)


def split_key(key: str) -> list[str]:
    r"""
    Split a full key path into its individual components.

    This is similar to `key.split(".")` but also works with the bracket syntax:
        "a.b"       -> ["a", "b"]
        "a[b]"      -> ["a", "b"]
        "[a].b"     -> ["a", "b"]

    Backslash escaping allows literal special characters inside a key name.
    Special characters are: . [ ] =
    Any other character after a backslash passes through unchanged (including
    the backslash itself, since backslash is not a special character).

        r"a\.b"     -> ["a.b"]     \. -> literal dot; no split at that dot
        r"a\[0\]"   -> ["a[0]"]   \[ and \] -> literal brackets
        r"a\=b"     -> ["a=b"]    \= -> literal equals (useful in dotlists)
        r"a\b"      -> [r"a\b"]   \b -> passthrough: backslash + b, not special
        r"a\\.b"    -> [r"a\.b"]  first \\ -> passthrough \, then \. -> literal .
                                   result key contains a backslash followed by a dot

    Malformed paths raise GrammarParseError instead of returning a prefix.
    """
    # Fast path: no backslash in the key means no escaping needed.
    # Keys without backslashes (the vast majority) take this path.
    if "\\" not in key:
        first = KEY_PATH_HEAD.match(key)
        assert first is not None
        first_stop = first.span()[1]
        tokens = key[0:first_stop].split(".")
        if first_stop == len(key):
            return tokens
        if key[first_stop] == "[" and not tokens[-1]:
            tokens.pop()
        stop = first_stop
        for match in KEY_PATH_OTHER.finditer(key, first_stop):
            if match.start() != stop:
                raise GrammarParseError(f"Invalid key path: {key!r}")
            dot_key, bracket_key = match.groups()
            tokens.append(dot_key if dot_key is not None else bracket_key)
            stop = match.end()
        if stop != len(key):
            raise GrammarParseError(f"Invalid key path: {key!r}")
        return tokens

    # Slow path: backslash present, parse character by character.
    # Escape rules: \. -> literal '.', \[ -> literal '[', \] -> literal ']',
    # \= -> literal '=', \x (anything else) -> literal '\x' (passthrough).
    tokens: list[str] = []
    i = 0
    n = len(key)

    # Parse a dot-mode segment: reads until '.', '[', or end of string.
    def _read_dot_seg() -> str:
        nonlocal i
        seg: list[str] = []
        while i < n and key[i] not in (".", "["):
            if key[i] == "\\" and i + 1 < n and key[i + 1] in _ESCAPABLE:
                seg.append(key[i + 1])
                i += 2
            else:
                seg.append(key[i])
                i += 1
        return "".join(seg)

    # Parse a bracket-mode segment: reads until unescaped ']' or end of string.
    def _read_bracket_seg() -> str:
        nonlocal i
        seg: list[str] = []
        while i < n and key[i] != "]":
            if key[i] == "\\" and i + 1 < n and key[i + 1] in _ESCAPABLE:
                seg.append(key[i + 1])
                i += 2
            else:
                seg.append(key[i])
                i += 1
        if i < n:  # found closing ']', consume it
            i += 1
            return "".join(seg)
        raise GrammarParseError(f"Invalid key path: {key!r}")

    # First segment: skip if key starts with '[' (bracket at head, no dot segment).
    if i == n or key[i] != "[":
        tokens.append(_read_dot_seg())

    # Remaining segments: each started by '.' or '['.
    while i < n:
        if key[i] == ".":
            i += 1  # consume '.'
            tokens.append(_read_dot_seg())
        elif key[i] == "[":
            i += 1  # consume '['
            tokens.append(_read_bracket_seg())
        else:
            raise GrammarParseError(f"Invalid key path: {key!r}")

    return tokens
