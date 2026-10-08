---
title: Validation and conversion
description: Know when OmegaConf accepts a value, converts it, or rejects it.
---

An untyped config stores supported values without a declared field type. A
structured config uses its annotations to validate values at runtime. A value
already of the declared type can be assigned directly:

```python
>>> from dataclasses import dataclass
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Settings:
...     port: int = 80
>>> cfg = OmegaConf.structured(Settings)
>>> cfg.port = 8080
>>> cfg.port
8080

```

## Conversion to a declared type

OmegaConf 2.3 attempts conversion during assignment to a typed field. For
example, assigning a numeric string to an integer field stores an integer:

```python
>>> cfg.port = "9000"
>>> cfg.port
9000

```

`OmegaConf.update(cfg, "port", "9000")` applies the same destination
validation and conversion. Invalid values raise `ValidationError`.

## Interpolations and unions

An interpolation is resolved when read. A scalar typed destination validates
and, when possible, converts the result. `II("source")` creates
`${source}` for a typed field without assigning a string in Python source;
`SI("${source}")` is the other static-checker-friendly form.

```python
>>> from omegaconf import II
>>> @dataclass
... class InterpolatedPort:
...     source: str = "8080"
...     port: int = II("source")
>>> cfg = OmegaConf.structured(InterpolatedPort)
>>> cfg.port, cfg.source
(8080, '8080')

```

In 2.3, this validation is skipped for container node interpolations. A
container-typed field can therefore return a value that does not match its
annotation:

```python
>>> from typing import Dict
>>> @dataclass
... class NotValidated:
...     source: int = 0
...     mapping: Dict[str, str] = II("source")
>>> cfg = OmegaConf.structured(NotValidated)
>>> cfg.mapping
0

```

Union branch selection avoids implicit conversion because the intended
branch would be ambiguous: a value must match a declared branch. See
[supported types](./types).

The [2.4 conversion reference](/docs/reference/conversion) explains
warnings for implicit assignment conversion, typed container interpolation
validation, and the new `oc.coerce` resolver.
