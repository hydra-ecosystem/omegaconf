---
title: Structured configs
description: Use dataclasses or attrs classes as runtime config schemas.
---

A structured config uses a dataclass or `attrs` class to define fields,
defaults, and types. `OmegaConf.structured()` creates a config with that
schema. Its fields validate assignments at runtime:

```python
>>> from dataclasses import dataclass
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Server:
...     host: str = "localhost"
...     port: int = 80
>>> cfg = OmegaConf.structured(Server)
>>> cfg.port = 8080
>>> cfg.port
8080
>>> cfg.port = "oops"
Traceback (most recent call last):
...
omegaconf.errors.ValidationError: Value 'oops' of type 'str' could not be converted to Integer
    full_key: port
    object_type=Server

```

The resulting object is a `DictConfig`, not an instance of `Server`.
`OmegaConf.get_type(cfg)` returns its schema class. The field annotations can
also help a static type checker when you annotate the variable as `Server`.
That annotation does not change the runtime object.

## Nested structured configs

A field can be annotated with another structured config class. Use a
`default_factory` when the field has a mutable default:

```python
>>> from dataclasses import field
>>> @dataclass
... class App:
...     server: Server = field(default_factory=Server)
>>> app = OmegaConf.structured(App)
>>> app.server.port
80

```

Structured configs reject unknown fields. A field can be
[missing](./missing-values) until supplied. The generated
[Python API](../reference/python-api) documents `OmegaConf.structured()`.

In 2.4, assigning a value that requires implicit conversion emits a
`FutureWarning`. Assign a value of the declared type, or use
`OmegaConf.update()` when requesting conversion explicitly. Normal assignment
of an `int` to an `int` field, as above, needs no conversion.

Next, learn how [field types](./field-types) describe containers, choices, and
alternatives.
