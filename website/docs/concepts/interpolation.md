---
title: Node and string interpolation
description: Reference config values with node and string interpolation.
---

Node interpolation references another value in the config. OmegaConf resolves
interpolations lazily, when you access the value. `${server.port}` references
the `server.port` node:

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

A node interpolation occupying the whole value retains the referenced value's
type, so `cfg.client.port` is an integer.

## String interpolation

String interpolation combines interpolation expressions with literal text
to produce a string:

```python
>>> cfg.client.url
'http://localhost:8080'

```

Paths may use dots or brackets; escape special characters when they belong to
a key rather than the path. See the
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
resolved values. This is useful before passing data to code that should not
depend on later config changes. It mutates the config, so copy it first if
you need to keep the original lazy expressions.

Next, learn how [resolver interpolation](./resolvers) computes values instead of
referencing another node.
