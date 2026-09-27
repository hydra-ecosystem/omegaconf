from typing import Any


class _EscapedMissing(str):
    """A decoded literal ending in ``???`` that must not become missing."""


def _has_missing_spelling(value: str) -> bool:
    prefix = value[:-3]
    return value.endswith("???") and prefix == "\\" * len(prefix)


def _decode_missing_escape(value: Any) -> Any:
    if isinstance(value, _EscapedMissing) or not isinstance(value, str):
        return value
    if len(value) > 3 and _has_missing_spelling(value):
        return _EscapedMissing(value[1:])
    return value
