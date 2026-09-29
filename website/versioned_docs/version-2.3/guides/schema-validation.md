---
title: Validate data with a schema
description: Merge YAML or overrides into a structured config.
---

Define a dataclass with the fields and types your application expects, then
merge external values into `OmegaConf.structured()` output. Validation runs
as the values are merged:

```python
>>> from dataclasses import dataclass, field
>>> from omegaconf import MISSING, OmegaConf
>>> @dataclass
... class Server:
...     host: str = "localhost"
...     port: int = MISSING
>>> schema = OmegaConf.structured(Server)
>>> cfg = OmegaConf.merge(schema, {"port": 8080})
>>> cfg.port
8080
>>> OmegaConf.merge(schema, {"port": "not a port"})
Traceback (most recent call last):
...
omegaconf.errors.ValidationError: Value 'not a port' of type 'str' could not be converted to Integer
    full_key: port
    object_type=Server

```

This works with configs loaded from YAML as well as Python dictionaries.
Mark required fields with `MISSING`; reading them before supplying a value
raises `MissingMandatoryValue`. The resulting config retains its schema for
later validation.

To keep a dataclass field outside the config, set
`metadata={"omegaconf_ignore": True}` on its `dataclasses.field()` (or the
equivalent `attrs` field):

```python
>>> @dataclass
... class Example:
...     port: int = 80
...     runtime_only: int = field(default=1, metadata={"omegaconf_ignore": True})
>>> cfg = OmegaConf.structured(Example)
>>> list(cfg.keys())
['port']

```

See [structured configs](../concepts/structured-configs) for the schema model.
