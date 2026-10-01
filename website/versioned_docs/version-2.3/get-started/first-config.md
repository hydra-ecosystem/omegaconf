---
title: Your first config
description: Create a config, use string interpolation, and merge configs.
---

Create a config from a Python dictionary, use string interpolation, and merge
configs.
You can run each example in a Python interpreter with OmegaConf 2.3 installed.

> **By the end:** you'll have a merged config that preserves a default, changes
> another value, and adds a new setting while the original stays unchanged.

## 1. Create a config

`OmegaConf.create()` turns a dictionary into a config.

```python
>>> from omegaconf import OmegaConf
>>> config = OmegaConf.create({
...     "host": "localhost",
...     "port": 80,
...     "url": "http://${host}:${port}",
... })

```

## 2. String interpolation

The `url` value uses string interpolation: `${host}` and `${port}` reference
other values in the config. OmegaConf resolves these references when you
access `url`:

```python
>>> config.url
'http://localhost:80'

```

## 3. Merge configs

`OmegaConf.merge()` takes one or more configs or dictionaries. Later values
win when the same key appears more than once.

```python
>>> # Merge a different port and a new debug setting.
>>> merged = OmegaConf.merge(config, {"port": 8080, "debug": True})
>>> # The interpolation uses the merged port.
>>> merged.url
'http://localhost:8080'
>>> # The merged config includes the new setting.
>>> merged.debug
True
>>> # The original config is unchanged.
>>> config.url
'http://localhost:80'

```

The merged config keeps `host` from the original, replaces `port`, and adds
`debug`. The interpolated `url` automatically uses the new port, while the
original config remains unchanged.

OmegaConf 2.4 adds `|` to create a merged dictionary config and `|=` to merge
into an existing one. These operators are unavailable in 2.3; see
[Merge configs in 2.4](/docs/next/guides/merge#dictionary-union-operators).

Continue with
[config containers](../concepts/configs-and-values) to learn how to change
nested values and work with sequences.
