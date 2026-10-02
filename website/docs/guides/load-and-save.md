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
dictionaries, lists, and tuples.

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

## Convert config to YAML

`OmegaConf.to_yaml(cfg)` converts a config to a YAML string.
By default (`resolve=False`), it preserves interpolation expressions, even
if you have already accessed their resolved values. This keeps references
intact when you save and reload a config.

Pass `resolve=True` to include the resolved values in the YAML string:

```python {7,11}
>>> cfg = OmegaConf.create({"port": 80, "url": "http://localhost:${port}"})
>>> cfg.url
'http://localhost:80'
>>> # The default YAML output keeps the interpolation expression.
>>> print(OmegaConf.to_yaml(cfg), end="")
port: 80
url: http://localhost:${port}
>>> # Resolve the interpolation in the YAML output.
>>> print(OmegaConf.to_yaml(cfg, resolve=True), end="")
port: 80
url: http://localhost:80

```

`resolve=True` affects the returned YAML string; it does not replace the
interpolation in `cfg`. The config still resolves `url` using the current port:

```python
>>> cfg.port = 8080
>>> cfg.url
'http://localhost:8080'

```

To replace interpolations inside the config itself, use
[`OmegaConf.resolve()`](../concepts/interpolation#resolve-now).

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
