from contextvars import ContextVar

# Scoped to the private validation graph; never stored in node flags or metadata.
# None disables validation; a bool marks strict, schema-only validation.
_schema_validation: ContextVar[bool | None] = ContextVar(
    "schema_validation", default=None
)
