---
title: Experimental helpers
description: Escape keys and values, or validate caller input against a structured schema.
---

These functions live in `omegaconf.experimental`. Their contracts may change
without the compatibility guarantees of the stable API.

## Escape values recursively

`escape_value(value)` adds one escape layer to string values, including `${…}`
and literal `???`. It recursively copies dictionaries, lists, tuples and config
nodes. It leaves stored dictionary keys and ordinary non-string values unchanged.
Both value transforms return copies; they have no in-place variants.

```python
>>> from omegaconf import OmegaConf
>>> from omegaconf.experimental import escape_value, unescape_value
>>> raw = {"a.b": ["Cost is ${price}", "???"]}
>>> cfg = OmegaConf.create(escape_value(raw))
>>> OmegaConf.to_object(cfg) == raw
True
>>> unescape_value(escape_value(raw)) == raw
True

```

Escape caller text before its first config construction. A config node already
marked missing stays missing when escaped. Config transforms operate on stored
spellings, preserve node types and flags, and copy ancestor context for subtrees.
They do not evaluate expressions. Native container cycles are rejected.
String enums retain their enum identity.

Raw dataclass and attrs classes or instances are unsupported as values, including
when nested in a container or stored in a `ValueNode`. Both value transforms
raise `ValidationError` for these inputs. Use ordinary mappings, lists, or tuples
for caller values. When applied to config nodes, either transform can also raise
normal typed-validation errors if its result is incompatible with a node.

`unescape_value(value)` removes one value-escape layer. When passed a config, it
returns a copied config. Restored expressions can run on subsequent reads, and
restored `???` can become missing. Malformed decoded expressions or incompatible
typed values can raise normal config errors. The source remains unchanged if
the transform fails.

Escaping is not idempotent. Use one layer for one OmegaConf interpretation.
Normal reads and `to_object()` already decode that layer; do not unescape their
results again. Escaping does not preserve literal intent through arbitrary
additional resolution or reconstruction. Default unresolved YAML save/load
retains the escaped storage spelling.

## Escape a key segment for a path

`escape_key(key)` escapes punctuation in one literal key segment.
`unescape_key(key)` reverses recognized escapes without splitting a path.
Unknown escapes retain their backslash. These functions do not rename stored
dictionary keys.

```python
>>> from omegaconf.experimental import escape_key, unescape_key
>>> cfg = OmegaConf.create({"a.b": 7})
>>> path = escape_key("a.b")
>>> OmegaConf.select(cfg, path)
7
>>> unescape_key(path)
'a.b'

```

An empty key segment escapes to an empty string. To select a stored empty key,
use `[]`; an empty complete path selects the root. Key-path escapes differ from
value escapes, so use the function for the syntax you are constructing.

## Validate caller input and construct objects

`from_input(schema, arguments)` composes recursive value escaping, schema merge
and object conversion. It accepts a structured schema class or instance and
returns its constructed object. Neither input is mutated.

```python
>>> from dataclasses import dataclass
>>> from omegaconf.experimental import from_input
>>> @dataclass
... class Request:
...     text: str
...     count: int = 1
>>> from_input(Request, {"text": "${oc.env:HOME}", "count": "5"})
Request(text='${oc.env:HOME}', count=5)

```

Defaults, nested structured objects, normal conversion and required/unknown-field
checks remain active. Literal `${…}` text does not bypass numeric validation.
Trusted schema defaults keep their ordinary interpolation behavior; only caller
arguments are escaped.

Caller arguments may use mappings, lists, tuples, and OmegaConf nodes. Raw
dataclass or attrs classes and instances are rejected with `ValidationError`,
including when nested in caller arguments. Pass nested caller values as ordinary
containers; the schema may still be a dataclass or attrs class or instance.

This helper has the same one-interpretation boundary as `escape_value()`. If a
trusted schema resolver returns decoded caller strings inside a new typed
container, OmegaConf may interpret those strings again. The helper does not
guarantee literal behavior across such forwarding.
