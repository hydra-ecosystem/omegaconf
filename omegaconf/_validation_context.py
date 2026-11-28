from contextvars import ContextVar

# Scoped to the private validation graph; never stored in node flags or metadata.
# None disables validation; a bool marks strict, schema-only validation.
_schema_validation: ContextVar[bool | None] = ContextVar(
    "schema_validation", default=None
)

# None disables the from_input scope. False blocks interpolation while building
# schema defaults; True also escapes strings produced by caller conversion.
_literal_input: ContextVar[bool | None] = ContextVar("literal_input", default=None)
