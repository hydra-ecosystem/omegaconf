---
title: Merge config sources
description: Combine defaults, environment settings, and overrides.
---

`OmegaConf.merge()` combines configs from left to right. Later values win
when the same key has a concrete value. Dictionaries merge recursively, while
a later list replaces an earlier list. The input configs are unchanged.

```python
>>> from omegaconf import OmegaConf
>>> defaults = OmegaConf.create({
...     "server": {
...         "host": "localhost",
...         "port": 80,
...     },
...     "users": ["a"],
... })
>>> override = OmegaConf.create({
...     "server": {
...         "port": 8080,
...     },
...     "users": ["b"],
... })
>>> environment = OmegaConf.create({
...     "server": {
...         "host": "service.internal",
...     },
... })
>>> merged = OmegaConf.merge(defaults, environment, override)
>>> OmegaConf.to_container(merged)
{'server': {'host': 'service.internal', 'port': 8080}, 'users': ['b']}
>>> defaults.server.port
80

```

## Missing values

A missing value (`???`) on the source side means “no value to apply,” so it
does not replace an existing concrete value. Merging in the opposite direction
fills the missing destination:

```python
>>> concrete = OmegaConf.create({
...     "server": {
...         "port": 80,
...     },
... })
>>> required = OmegaConf.create({
...     "server": {
...         "port": "???",
...     },
... })
>>> OmegaConf.merge(concrete, required).server.port
80
>>> OmegaConf.merge(required, concrete).server.port
80

```

This lets a schema declare a required field without erasing a value supplied
by another source. See [missing values](../concepts/missing-values) for how to
inspect a mandatory field.

## Faster destructive merging

`OmegaConf.unsafe_merge()` uses the same merge rules and can be faster, but it
consumes its input configs. Do not access those inputs after the call. Use
ordinary `merge()` unless this tradeoff matters:

```python
>>> base = OmegaConf.create({
...     "server": {
...         "host": "localhost",
...     },
... })
>>> override = OmegaConf.create({
...     "server": {
...         "port": 8080,
...     },
... })
>>> combined = OmegaConf.unsafe_merge(base, override)
>>> OmegaConf.to_container(combined)
{'server': {'host': 'localhost', 'port': 8080}}

```

The `DictConfig` union operators `|` and `|=` are introduced in
[OmegaConf 2.4](/docs/next/guides/merge).
