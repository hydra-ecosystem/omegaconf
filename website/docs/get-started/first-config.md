---
title: Your first config
description: Create, read, and merge an OmegaConf config in a few lines.
---

Build a config from a Python dictionary, read a value, and apply an override.
You can run each example in a Python interpreter with OmegaConf installed.

> **By the end:** you'll have a merged config with a new port, while the
> original config stays unchanged.

## 1. Create a config

`OmegaConf.create()` turns a dictionary into a config. You can access its keys
as attributes or dictionary items.

```python
>>> from omegaconf import OmegaConf
>>> config = OmegaConf.create({
...     "host": "localhost",
...     "port": 80,
... })
>>> config.host
'localhost'

```

## 2. Read a value

Read `port` the same way. It is an integer in this config.

```python
>>> config.port
80

```

## 3. Merge an override

`OmegaConf.merge()` takes one or more configs or dictionaries. Later values
win when the same key appears more than once.

```python
>>> override = OmegaConf.create({"port": 8080})
>>> merged = OmegaConf.merge(config, override)
>>> merged.port
8080
>>> config.port
80

```

You now have two configs: `config` still uses port 80, and `merged` uses 8080.
Continue with [config containers](../concepts/configs-and-values) to learn how
to change nested values and work with sequences.
