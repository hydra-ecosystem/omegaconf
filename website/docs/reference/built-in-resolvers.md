---
title: Built-in resolvers
description: Look up the oc.env, oc.create, oc.coerce, and other built-in resolvers.
---

[Resolver interpolations](../concepts/resolvers) use `${name:arguments}` and
resolve when their node is accessed. They can be nested. These resolvers are available
without registration:

| Resolver | Use |
| --- | --- |
| `oc.env` | Read an environment variable, with an optional default. |
| `oc.create` | Convert a resolver result or YAML string to a config node. |
| `oc.deprecated` | Warn on an old key and forward to a replacement. |
| `oc.coerce` | Convert to an explicit primitive node type. |
| `oc.decode` | Parse a string with OmegaConf's interpolation grammar. |
| `oc.select` | Select a key, optionally returning a default. |
| `oc.dict.keys` / `oc.dict.values` | View dictionary keys or values as a list config. |

## `oc.env`

`${oc.env:NAME,default}` reads an environment variable. The default is
stringified unless it is `null`, which produces `None`. Environment values
are strings; use `oc.coerce` or `oc.decode` when you need another type.

```python
>>> import os
>>> from omegaconf import OmegaConf
>>> os.environ["OC_DOCS_PORT"] = "8080"
>>> cfg = OmegaConf.create({
...     "raw": "${oc.env:OC_DOCS_PORT}",
...     "converted": "${oc.coerce:int,${oc.env:OC_DOCS_PORT}}",
... })
>>> cfg.raw, cfg.converted
('8080', 8080)
>>> del os.environ["OC_DOCS_PORT"]

```

## `oc.create`

`${oc.create:${some_resolver:}}` turns a returned dictionary, list, or YAML
string into an OmegaConf container. This makes its nested values accessible
as config nodes.

```python
>>> OmegaConf.register_resolver("make_docs_mapping", lambda: {"answer": 42})
>>> cfg = OmegaConf.create({
...     "plain": "${make_docs_mapping:}",
...     "created": "${oc.create:${make_docs_mapping:}}",
... })
>>> type(cfg.plain).__name__, type(cfg.created).__name__
('dict', 'DictConfig')
>>> cfg.created.answer
42

```

## `oc.deprecated`

`${oc.deprecated:new_key}` warns when the old key is read and returns the new
key's value. An optional second argument customizes the warning text; `$OLD_KEY`
and `$NEW_KEY` are replaced in that text.

```python
>>> import warnings
>>> cfg = OmegaConf.create({
...     "old": "${oc.deprecated:new}",
...     "new": 42,
... })
>>> with warnings.catch_warnings(record=True) as emitted:
...     warnings.simplefilter("always")
...     value = cfg.old
>>> value, len(emitted)
(42, 1)

```

## `oc.coerce`

`${oc.coerce:int,${oc.env:PORT}}` converts the environment string to an
integer before the destination field validates it. Bare `int`, `float`,
`bool`, `str`, and `bytes` are supported. A fully qualified import path can
name those types, `pathlib.Path`, `types.NoneType`, or an importable enum.
Unknown or non-importable paths fail when accessed. Importing a path can run
module top-level code, so use this feature with trusted configs.

## `oc.decode`

`${oc.decode:${oc.env:PORT}}` parses a string using the interpolation grammar.
It recognizes numbers, booleans, lists, and dictionaries. Quote input
strings containing grammar punctuation. `null` is the only non-string input
and returns `None`.

```python
>>> cfg = OmegaConf.create({
...     "ports": "${oc.decode:'[80, 443]'}",
...     "disabled": "${oc.decode:null}",
... })
>>> cfg.ports, cfg.disabled
([80, 443], None)

```

## `oc.select`

`${oc.select:path,default}` reads a path and supplies a default when the path
is absent or missing. Unlike ordinary node interpolation, it can return a
default instead of raising. Quote paths containing resolver punctuation.

```python
>>> cfg = OmegaConf.create({
...     "required": "???",
...     "fallback": "${oc.select:required,localhost}",
...     "unfilled": "${oc.select:required}",
... })
>>> cfg.fallback, cfg.unfilled
('localhost', None)

```

## `oc.dict.keys` and `oc.dict.values`

`${oc.dict.keys:workers}` returns a `ListConfig` of dictionary keys;
`${oc.dict.values:workers}` returns a `ListConfig` whose elements track the
dictionary values. Both accept a path to a `DictConfig`.

```python
>>> cfg = OmegaConf.create({
...     "workers": {"first": "host-a"},
...     "names": "${oc.dict.keys:workers}",
...     "hosts": "${oc.dict.values:workers}",
... })
>>> list(cfg.names), list(cfg.hosts)
(['first'], ['host-a'])
>>> cfg.workers.first = "host-b"
>>> list(cfg.hosts)
['host-b']

```
