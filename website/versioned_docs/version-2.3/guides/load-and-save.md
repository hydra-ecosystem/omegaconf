---
title: Load and save configs
description: Read and write YAML, and convert configs to Python data.
---

Use `OmegaConf.create()` for a YAML string and `OmegaConf.load()` for a YAML
file. Both return an OmegaConf config:

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create("""
... server:
...   port: 80
... """)
>>> cfg.server.port
80

```

## Save and load YAML

`OmegaConf.save(cfg, path)` writes YAML, and `OmegaConf.load(path)` reads it
back. Paths, filenames, and file objects are accepted. YAML preserves values
but not the Python schema of a
[structured config](../concepts/structured-configs). Use `OmegaConf.to_yaml(cfg)`
when you need a YAML string or
`OmegaConf.to_container(cfg)` when another Python API needs ordinary
dictionaries and lists.

```python
>>> yaml_text = OmegaConf.to_yaml(cfg)
>>> print(yaml_text, end="")
server:
  port: 80

```

The same operations accept file objects. Loading YAML does not restore a
structured config's dataclass or `attrs` type:

```python
>>> import io
>>> buffer = io.StringIO()
>>> OmegaConf.save(config=cfg, f=buffer)
>>> restored = OmegaConf.load(io.StringIO(buffer.getvalue()))
>>> restored == cfg
True

```

## Pickle

A Python-only pickle round trip retains more OmegaConf type information,
but the file may not work across OmegaConf versions and must come from a
trusted source. On Python 3.6, structured configs with complex type hints
cannot be pickled.

```python
>>> import pickle
>>> restored = pickle.loads(pickle.dumps(cfg))
>>> restored == cfg
True

```
