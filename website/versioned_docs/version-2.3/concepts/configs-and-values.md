---
title: Config containers
description: Read and change mapping and sequence configs.
---

`OmegaConf.create()` with no argument makes an empty `DictConfig`. A
dictionary also becomes a `DictConfig`, while a list becomes a `ListConfig`.
These containers can be nested. Values are stored as nodes; attribute or
item access returns their values. For example:

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({
...     "server": {
...         "host": "localhost",
...         "port": 80,
...     },
...     "users": ["a", "b"],
... })
>>> cfg.server.port
80
>>> cfg["server"]["port"]
80
>>> cfg.users[0]
'a'

```

Use attribute access for keys that work as Python attributes. Item access also
works for other keys and for list positions. You can change a value or add a
key to a `DictConfig` created from a plain dictionary:

```python
>>> cfg.server.port = 8080
>>> cfg.server["public-host"] = "example.org"
>>> cfg.server["public-host"]
'example.org'

```

Use `.get("key", default)` when a mapping key may not exist. To pass a config
to code expecting plain Python containers, use
[`OmegaConf.to_container()`](../reference/operations#convert-or-resolve).

Dictionary keys may be `str`, `int`, `bool`, `float`, `bytes`, or Enum members.

## Sequence containers

Lists become mutable `ListConfig` values. In 2.3, native tuples also become
mutable `ListConfig` values. This changes in
[OmegaConf 2.4](/docs/next/migration/2.4-tuples).

Next, learn how to [mark a value as missing](./missing-values) when it must be
provided later.
