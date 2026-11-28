from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

# Scoped to the private validation graph; never stored in node flags or metadata.
# None disables validation; a bool marks strict, schema-only validation.
_schema_validation: ContextVar[bool | None] = ContextVar(
    "schema_validation", default=None
)

# None disables the from_input scope. False blocks interpolation while building
# schema defaults; True also escapes strings produced by caller conversion.
_literal_input: ContextVar[bool | None] = ContextVar("literal_input", default=None)


@contextmanager
def _literal_input_context(mode: bool | None) -> Iterator[None]:
    """Set literal-input mode for this scope and restore it on exit."""
    token = _literal_input.set(mode)
    try:
        yield
    finally:
        _literal_input.reset(token)
