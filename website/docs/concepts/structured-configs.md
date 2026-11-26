---
title: Structured configs
description: Use dataclasses or attrs classes as runtime config schemas.
---

The examples use Python 3.10 or newer type annotation syntax.

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

A mapping assigned to a structured field uses that field's schema and defaults:

```python
>>> app.server = {"port": 8080}
>>> OmegaConf.to_object(app).server
Server(host='localhost', port=8080)

```

Structured configs reject unknown fields. A field can be
[missing](./missing-values) until supplied. The generated
[Python API](../reference/python-api) documents `OmegaConf.structured()`.

## Structured values in typed containers

When a list, dictionary, or tuple declares a structured value type, its
mapping values are validated against that schema. This applies to
construction, insertion or replacement where supported, and merging.
Schema defaults fill omitted fields, and unknown fields or invalid values
raise validation errors.

```python
>>> servers = OmegaConf.typed_list([{"port": 8080}], element_type=Server)
>>> OmegaConf.to_object(servers)
[Server(host='localhost', port=8080)]
>>> named = OmegaConf.typed_dict(
...     {"primary": {"port": 8443}}, key_type=str, element_type=Server
... )
>>> OmegaConf.to_object(named)
{'primary': Server(host='localhost', port=8443)}

```

Nested containers use their declared value types too. Frozen schemas retain
their read-only protection. Supplying an existing structured value preserves
its values without rerunning its unused default factories.

In 2.4, assigning a value that requires implicit conversion emits a
`FutureWarning`. Assign a value of the declared type, or use
`OmegaConf.update()` when requesting conversion explicitly. Normal assignment
of an `int` to an `int` field, as above, needs no conversion.

Next, learn how [field types](./field-types) describe containers, choices, and
alternatives.
