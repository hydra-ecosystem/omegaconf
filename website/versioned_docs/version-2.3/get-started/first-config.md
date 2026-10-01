---
title: Your first config
description: Create a config, derive a value, and merge an override in a few lines.
---

Build a config from a Python dictionary, derive a URL, and apply an override.
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
... })

```

## 2. Derive a URL

Use `${...}` to reference other values in the config. OmegaConf resolves these
references when you access the value, so the URL follows its current host and port.

```python
>>> config.url = "http://${host}:${port}"
>>> config.url
'http://localhost:80'

```

## 3. Merge an override

`OmegaConf.merge()` takes one or more configs or dictionaries. Later values
win when the same key appears more than once.
Use `resolve=True` to expand the references in the YAML output.

```python
>>> override = OmegaConf.create({
...     "port": 8080,
...     "debug": True,
... })
>>> merged = OmegaConf.merge(config, override)
>>> print(OmegaConf.to_yaml(merged, resolve=True), end="")
host: localhost
port: 8080
url: http://localhost:8080
debug: true
>>> print(OmegaConf.to_yaml(config, resolve=True), end="")
host: localhost
port: 80
url: http://localhost:80

```

The merged config keeps `host` from the original, replaces `port`, and adds
`debug`. Its URL automatically uses the new port, while the original config
remains unchanged. Continue with
[config containers](../concepts/configs-and-values) to learn how to change
nested values and work with sequences.
