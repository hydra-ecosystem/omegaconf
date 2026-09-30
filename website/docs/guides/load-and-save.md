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

`to_yaml()` accepts PyYAML's `default_flow_style` option for controlling
compact sequence formatting.

```python
>>> matrix = OmegaConf.create({"rows": [[1, 0], [0, 1]]})
>>> print(OmegaConf.to_yaml(matrix, default_flow_style=None), end="")
rows:
- [1, 0]
- [0, 1]

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

For a Python-only round trip that retains OmegaConf type information, use
`pickle` with trusted data. The resulting file is not guaranteed to work
across OmegaConf versions:

```python
>>> import pickle
>>> restored = pickle.loads(pickle.dumps(cfg))
>>> restored == cfg
True

```
