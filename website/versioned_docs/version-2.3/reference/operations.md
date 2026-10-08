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
`OmegaConf.update()` writes at a key path and converts its input against a
typed destination.

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({
...     "server": {"port": 80},
... })
>>> OmegaConf.select(cfg, "server.port")
80
>>> OmegaConf.update(cfg, "server.port", 8080)
>>> cfg.server.port
8080

```

An absent or missing path returns `None` from `select()` unless you supply a
default. Use `throw_on_missing=True` when a missing marker should raise.

```python
>>> cfg = OmegaConf.create({"unset": "???"})
>>> OmegaConf.select(cfg, "unset", default="fallback")
'fallback'
>>> OmegaConf.select(cfg, "absent") is None
True

```

`update()` merges a container value by default; pass `merge=False` to
replace it. `force_add=True` can create a path even under the struct flag or
a structured config, so use it only when you intend to bypass that
restriction.

```python
>>> cfg = OmegaConf.create({"server": {"host": "localhost"}})
>>> OmegaConf.update(cfg, "server", {"port": 80})
>>> dict(cfg.server)
{'host': 'localhost', 'port': 80}
>>> OmegaConf.update(cfg, "server", {"port": 8080}, merge=False)
>>> dict(cfg.server)
{'port': 8080}

```

Paths accept dot and bracket notation. The [2.4 operations reference](/docs/reference/operations)
describes new backslash escaping for literal dots, brackets, and equals signs
in key names.

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
evaluates them in the returned plain Python data without modifying the
config. The default `structured_config_mode=SCMode.DICT` exports structured
configs as dictionaries. `SCMode.DICT_CONFIG` keeps their `DictConfig`
nodes, while `SCMode.INSTANTIATE` creates backing dataclass or `attrs`
instances and resolves interpolations inside them even with `resolve=False`.
`to_object()` is the shortcut for `resolve=True`, `throw_on_missing=True`,
and `SCMode.INSTANTIATE`.

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

## Inspect a config

`OmegaConf.is_config()`, `is_dict()`, and `is_list()` check container kinds.
`get_type()` reports a structured config's underlying schema.
`is_interpolation()` and `is_missing()` inspect nodes without resolving or
reading them. `missing_keys()` lists mandatory paths that are still missing.
In 2.3, call `OmegaConf.is_missing(cfg, "key")` to inspect a field.
`MISSING`, `II`, and `SI` are also documented in the
[generated API](./python-api/omegaconf).

```python
>>> cfg = OmegaConf.create({
...     "server": {"port": 80},
...     "required": "???",
... })
>>> sorted(OmegaConf.missing_keys(cfg))
['required']
>>> OmegaConf.to_container(OmegaConf.masked_copy(cfg, ["server"]))
{'server': {'port': 80}}

```

`missing_keys()` reports mandatory paths in dot/bracket form.
`masked_copy()` keeps only the selected top-level keys of a `DictConfig`.
