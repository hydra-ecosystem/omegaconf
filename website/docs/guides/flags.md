---
title: Control config changes
description: Use read-only and struct flags, and temporarily override them.
---

Config flags can be set on a container and inherited by its children. The
default for both flags is off.

## Read-only

`OmegaConf.set_readonly(cfg, True)` prevents modification. Use `read_write()`
for a scoped update without leaving the config writable afterward:

```python
>>> from omegaconf import OmegaConf, read_write
>>> cfg = OmegaConf.create({"port": 80})
>>> OmegaConf.set_readonly(cfg, True)
>>> with read_write(cfg):
...     cfg.port = 8080
>>> cfg.port
8080
>>> OmegaConf.is_readonly(cfg)
True

```

## Struct

`OmegaConf.set_struct(cfg, True)` prevents adding unknown keys. Existing
keys remain writable unless the config is also read-only. Use `open_dict()`
for a scoped addition:

```python
>>> from omegaconf import open_dict
>>> cfg = OmegaConf.create({"port": 80})
>>> OmegaConf.set_struct(cfg, True)
>>> with open_dict(cfg):
...     cfg.host = "localhost"
>>> cfg.host
'localhost'
>>> OmegaConf.is_struct(cfg)
True

```

Frozen [structured config](../concepts/structured-configs) classes also
produce read-only config values.
Use the [Python API](../reference/python-api) for `set_readonly`,
`set_struct`, and the context managers.
