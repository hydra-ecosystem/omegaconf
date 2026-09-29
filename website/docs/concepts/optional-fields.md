---
title: Optional fields
description: Allow None in a structured config field.
---

A [structured config](./structured-configs) uses a field's type annotation to
check assigned values. `T | None` means that the field accepts either a value
of type `T` or `None`:

```python
>>> from dataclasses import dataclass
>>> from omegaconf import MISSING, OmegaConf
>>> @dataclass
... class Service:
...     token: str | None = None
...     host: str = "localhost"
>>> cfg = OmegaConf.structured(Service)
>>> cfg.token is None
True
>>> cfg.token = "secret"
>>> cfg.token
'secret'
>>> OmegaConf.update(cfg, "host", None)
Traceback (most recent call last):
...
omegaconf.errors.ValidationError: field 'host' is not Optional
    full_key: host
    object_type=Service

```

Optionality and [missing values](./missing-values) answer different questions.
`T | None` permits `None`; `MISSING` means no value has been supplied yet.
An optional field can start out missing and later receive `None`:

```python
>>> @dataclass
... class Credentials:
...     token: str | None = MISSING
>>> credentials = OmegaConf.structured(Credentials)
>>> OmegaConf.is_missing(credentials, "token")
True
>>> credentials.token = None
>>> OmegaConf.is_missing(credentials, "token")
False

```

To apply a schema to external data, continue with
[Validate data with a schema](../guides/schema-validation).
