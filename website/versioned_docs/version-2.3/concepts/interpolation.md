---
title: Node interpolation
description: Reference another config value, lazily or all at once.
---

An interpolation stores an expression and evaluates it when you read the
value. `${server.port}` reads another node in the same config:

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({
...     "server": {
...         "host": "localhost",
...         "port": 80,
...     },
...     "client": {
...         "port": "${server.port}",
...         "url": "http://${server.host}:${server.port}",
...     },
... })
>>> cfg.client.port
80
>>> cfg.server.port = 8080
>>> cfg.client.port
8080

```

An interpolation occupying the whole value retains the referenced value's
type, so `cfg.client.port` is an integer. Embedding node references in text
produces a string:

```python
>>> cfg.client.url
'http://localhost:8080'

```

Paths may use dots or brackets. A colon in a key is parsed as resolver syntax
in a node interpolation; [`oc.select`](../reference/built-in-resolvers#ocselect)
can select such a key. The 2.4 backslash escapes for literal path punctuation
are not available in 2.3. See the
[interpolation grammar](../reference/grammar) for the complete syntax.

## Relative references

One leading dot starts at the current container; each additional dot moves
up one level:

```python
>>> cfg = OmegaConf.create({
...     "server": {
...         "port": 80,
...         "selected": "${.port}",
...     },
... })
>>> cfg.server.selected
80

```

## Nested references

An interpolation can select part of another interpolation's path:

```python
>>> cfg = OmegaConf.create({
...     "plans": {
...         "A": "plan A",
...         "B": "plan B",
...     },
...     "selected": "A",
...     "plan": "${plans[${selected}]}",
... })
>>> cfg.plan
'plan A'
>>> cfg.selected = "B"
>>> cfg.plan
'plan B'

```

Avoid cycles: an interpolation cannot eventually refer back to itself.

## Resolve now

`OmegaConf.resolve(cfg)` replaces interpolations in a config with their
resolved values. It mutates the config, so copy it first if you need to keep
the original lazy expressions.

Next, learn how [resolver calls](./resolvers) compute values instead of
referencing another node.
