---
title: Common operations
description: Find the OmegaConf operation for access, conversion, updates, and inspection.
---

The [generated Python API](./python-api/omegaconf) has exact signatures and
parameters. This page groups the common operations by what you need to do.

## Create and combine

| Task | Operation |
| --- | --- |
| Create from Python values or YAML text | `OmegaConf.create()` |
| Create from a dataclass or `attrs` schema | `OmegaConf.structured()` |
| Read or write a YAML file | `OmegaConf.load()` / `OmegaConf.save()` |
| Parse `key=value` overrides | `OmegaConf.from_dotlist()` / `OmegaConf.from_cli()` |
| Combine configs without changing the inputs | `OmegaConf.merge()` |
| Combine configs while consuming the inputs | `OmegaConf.unsafe_merge()` |

See [load and save](../guides/load-and-save), [merge](../guides/merge), and
[command-line overrides](../guides/command-line) for examples.

## Select and update a path

`OmegaConf.select()` reads a nested key path and may return a default.
`OmegaConf.can_select()` answers whether a path can produce a value, without
returning one. `OmegaConf.update()` writes at a key path and can explicitly
convert its input against a typed destination.

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({
...     "server": {"port": 80},
... })
>>> OmegaConf.select(cfg, "server.port")
80
>>> OmegaConf.can_select(cfg, "server.port")
True
>>> OmegaConf.update(cfg, "server.port", 8080)
>>> cfg.server.port
8080

```

An absent or missing path returns `None` from `select()` unless you supply a
default. Set `throw_on_missing=True` when a missing marker should raise.
`can_select()` returns `False` for paths that cannot be read, including a
broken interpolation; a selected `None` value counts as selectable.

```python
>>> cfg = OmegaConf.create({
...     "unset": "???",
...     "empty": None,
... })
>>> OmegaConf.select(cfg, "unset", default="fallback")
'fallback'
>>> OmegaConf.can_select(cfg, "unset")
False
>>> OmegaConf.can_select(cfg, "empty")
True

```

For a container value, `update()` merges by default. Pass `merge=False` to
replace it. `force_add=True` can create a path even under the struct flag or a
structured config, so use it only when you intend to bypass that restriction.

```python
>>> cfg = OmegaConf.create({"server": {"host": "localhost"}})
>>> OmegaConf.update(cfg, "server", {"port": 80})
>>> dict(cfg.server)
{'host': 'localhost', 'port': 80}
>>> OmegaConf.update(cfg, "server", {"port": 8080}, merge=False)
>>> dict(cfg.server)
{'port': 8080}

```

If an intermediate path is a node interpolation to a container, `update()`
changes the referenced container and leaves the interpolation intact.

```python
>>> cfg = OmegaConf.create({
...     "base": {"x": 1},
...     "alias": "${base}",
... })
>>> OmegaConf.update(cfg, "alias.y", 2)
>>> OmegaConf.to_container(cfg, resolve=False)
{'base': {'x': 1, 'y': 2}, 'alias': '${base}'}

```

### Key paths

Paths accept dot and bracket notation. In 2.4, backslash-escape dots,
brackets, or equals signs that belong to the key itself. For example,
`r"a\.b"` selects one key named `a.b`:

```python
>>> cfg = OmegaConf.create({"a.b": 10})
>>> OmegaConf.select(cfg, r"a\.b")
10

```

## Convert or resolve

| Task | Operation |
| --- | --- |
| Produce a YAML string | `OmegaConf.to_yaml()` |
| Produce plain Python containers | `OmegaConf.to_container()` |
| Instantiate structured config objects | `OmegaConf.to_object()` |
| Resolve interpolations in place | `OmegaConf.resolve()` |
| Make a config with selected keys | `OmegaConf.masked_copy()` |

`to_container()` can raise on missing values with `throw_on_missing=True`.
Choose `structured_config_mode` when structured configs need special
handling. `resolve()` mutates its input; copy first if you need to retain
the original interpolations.

`to_container(resolve=False)` keeps interpolation expressions; `resolve=True`
evaluates them in the returned plain Python data without modifying the config.
The default `structured_config_mode=SCMode.DICT` exports structured configs as
dictionaries. `SCMode.DICT_CONFIG` keeps their `DictConfig` nodes, while
`SCMode.INSTANTIATE` creates backing dataclass or `attrs` instances and
resolves their interpolations even with `resolve=False`. `to_object()` is the
shortcut for `resolve=True`, `throw_on_missing=True`, and
`SCMode.INSTANTIATE`.

```python
>>> from dataclasses import dataclass
>>> from omegaconf import SCMode
>>> @dataclass
... class Server:
...     port: int = 80
>>> cfg = OmegaConf.create({
...     "server": OmegaConf.structured(Server),
...     "selected_port": "${server.port}",
... })
>>> OmegaConf.to_container(cfg)["selected_port"]
'${server.port}'
>>> OmegaConf.to_container(cfg, resolve=True)["selected_port"]
80
>>> isinstance(OmegaConf.to_container(
...     cfg, structured_config_mode=SCMode.INSTANTIATE
... )["server"], Server)
True

```

Plain-container export cannot distinguish missing `???` from escaped literal
`\???`: both become the string `"???"`. Use YAML when that distinction must
survive a round trip. When custom resolvers have side effects or depend on
changing state, `resolve()` can depend on depth-first key traversal order;
prefer lazy access or `to_container(resolve=True)` when you do not need to
materialize the config in place. When a resolver returns a plain container,
`resolve()` materializes it as an OmegaConf container and resolves its children.

## Inspect a config

`OmegaConf.is_config()`, `is_dict()`, `is_list()`, `is_tuple()`, and
`is_sequence()` check container kinds. `get_type()` reports a structured
config's underlying schema. `is_interpolation()` and `is_missing()` inspect
nodes without resolving or reading them. `missing_keys()` lists mandatory
paths that are still missing; `structural_equality()` compares unresolved
structure rather than resolved values. `MISSING`, `II`, and `SI` are also
documented in the [generated API](./python-api/omegaconf).

```python
>>> cfg = OmegaConf.create({
...     "required": "???",
...     "derived": "${required}",
... })
>>> sorted(OmegaConf.missing_keys(cfg))
['derived', 'required']
>>> missing = OmegaConf.create({"value": "???"})
>>> literal = OmegaConf.create({"value": r"\???"})
>>> OmegaConf.structural_equality(missing, literal)
False
>>> cfg = OmegaConf.create({"server": {"port": 80}, "debug": False})
>>> OmegaConf.to_container(OmegaConf.masked_copy(cfg, ["server"]))
{'server': {'port': 80}}

```

`masked_copy(cfg, keys)` keeps only selected top-level keys from a
`DictConfig`. `missing_keys()` returns dot/bracket paths, including node
interpolations that lead to a missing value. It skips custom resolvers by
default; use `resolve_custom_resolvers=True` when their results must also be
checked.

Use `OmegaConf.is_missing(cfg, "key")` to inspect a config field. In 2.4,
`OmegaConf.is_missing(value)` also checks a detached value; this matters for
an escaped literal `???`, which compares equal to a normal string.

Config containers are unhashable because their values can change, even when
the read-only flag is set.
