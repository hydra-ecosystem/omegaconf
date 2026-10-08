---
title: Write a custom resolver
description: Register custom resolvers and configure caching.
---

A resolver is a Python callable used in a
[resolver interpolation](../concepts/resolvers). Register it once
with a name, then use that name in `${name:arguments}`:

```python
>>> from omegaconf import OmegaConf
>>> OmegaConf.register_new_resolver("plus_ten_docs", lambda value: value + 10)
>>> cfg = OmegaConf.create({"result": "${plus_ten_docs:32}"})
>>> cfg.result
42

```

Resolver arguments are parsed from the interpolation expression. The resolver
runs when the node is accessed. Nested interpolation lets an argument come
from another config value, and a resolver may return a scalar, container, or
config node. Names may be namespaced (such as `myapp.add`), and an
interpolation may even select part of a resolver name.

If the callable declares keyword-only `_parent_` or `_root_` parameters,
OmegaConf supplies the interpolation's parent container or config root,
respectively. This is useful when a
resolver needs to inspect neighboring values without requiring them as
explicit interpolation arguments.

```python
>>> def add_neighbors(left, right, *, _parent_):
...     return _parent_.get(left, 0) + _parent_.get(right, 0)
>>> OmegaConf.register_new_resolver("add_neighbors_docs", add_neighbors)
>>> cfg = OmegaConf.create({
...     "group": {
...         "a": 1,
...         "b": 2,
...         "total": "${add_neighbors_docs:a,b}",
...         "with_absent": "${add_neighbors_docs:a,absent}",
...     },
... })
>>> cfg.group.total, cfg.group.with_absent
(3, 1)

```

The name `absent` is passed as text; the resolver handles its absence
through `_parent_`. If a nested interpolation references an absent key or a
mandatory missing value, evaluation fails before the resolver is called.

## Replace or cache a resolver

Registering a name that already exists raises `ValueError`. Pass
`replace=True` when deliberately replacing it. `use_cache=True` reuses a
result for the same literal argument strings, even if a nested interpolation
would now resolve to a different value; leave caching off when the function
depends on changing external state.

```python
>>> OmegaConf.register_new_resolver(
...     "cached_docs", lambda value: value * 2, use_cache=True
... )
>>> cfg = OmegaConf.create({
...     "source": 2,
...     "result": "${cached_docs:${source}}",
... })
>>> cfg.result
4
>>> cfg.source = 3
>>> cfg.result  # the same literal argument expression uses the cache
4

```

## Remove resolvers

### Clear one

`OmegaConf.clear_resolver(name)` returns `True` if it removed a registration
and `False` if the name was absent. It can remove a built-in, so check the
name before calling it.

```python
>>> OmegaConf.register_new_resolver("temporary_docs", lambda: 1)
>>> OmegaConf.clear_resolver("temporary_docs")
True
>>> OmegaConf.has_resolver("temporary_docs")
False

```

### Clear all

`OmegaConf.clear_resolvers()` removes custom registrations but retains the
built-ins:

```python
>>> OmegaConf.clear_resolvers()
>>> OmegaConf.has_resolver("oc.env")
True

```

The [2.4 resolver guide](/docs/guides/custom-resolvers) describes the
new `OmegaConf.register_resolver()` API and annotation validation.
See [built-in resolvers](../reference/built-in-resolvers) for `oc.env`,
`oc.select`, and other resolvers provided by OmegaConf.
