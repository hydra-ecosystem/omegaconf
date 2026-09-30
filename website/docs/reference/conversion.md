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

## Request conversion explicitly

Use `OmegaConf.update()` when the input needs conversion to the destination
type. It applies the field's normal validation rules and raises
`ValidationError` if conversion is impossible:

```python
>>> OmegaConf.update(cfg, "port", "9000")
>>> cfg.port
9000

```

In 2.4, direct assignment and typed list or dict mutation still convert
compatible values, but emit `FutureWarning`. Supply the declared type or use
`OmegaConf.update()` when you intend conversion. Assigning a list to a
tuple-typed field, or a tuple to a list-typed field, also warns.

## Resolver results and interpolations

A resolver's return value and the destination field are checked separately.
In a typed field, an interpolation result is validated against the field type
on lazy access and on `OmegaConf.resolve()`. A typed container result is
validated against the destination's element and key types as well.

`oc.coerce` asks for a specific primitive type within an interpolation, before
destination validation. For example, `${oc.coerce:int,${oc.env:PORT}}`
converts an environment string to an integer even when the destination has no
type annotation. See [built-in resolvers](./built-in-resolvers).

A typed node interpolation uses the destination annotation when read. It
does not change the source value. `II("source")` is equivalent to
`SI("${source}")`; both let a static type checker accept an interpolation
expression as a typed field default.

```python
>>> from dataclasses import dataclass, field
>>> from omegaconf import OmegaConf, SI
>>> @dataclass
... class Ports:
...     source: list[str] = field(default_factory=lambda: ["80", "443"])
...     numbers: list[int] = SI("${source}")
>>> cfg = OmegaConf.structured(Ports)
>>> list(cfg.numbers)
[80, 443]
>>> list(cfg.source)
['80', '443']
>>> OmegaConf.resolve(cfg)
>>> list(cfg.numbers)
[80, 443]

```

An incompatible source raises `InterpolationValidationError` on access or
during `resolve()`. A source container that already matches the destination
type may be returned directly; do not rely on a copy being made.

## Unions

Union branch selection avoids implicit conversion because the intended
branch would be ambiguous. The value must match a declared branch. Once a
structured branch is selected, its own fields follow normal structured
config validation and conversion rules. See [supported types](./types) for
typed container and structured unions.
