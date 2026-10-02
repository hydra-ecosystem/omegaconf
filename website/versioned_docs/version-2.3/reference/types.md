---
title: Supported types
description: Type annotations accepted by structured configs in OmegaConf 2.3.
---

Structured configs use dataclass or `attrs` field annotations to validate
values. They support primitive values, typed containers, other structured
configs, and several combinations of those types.
For runnable examples, see [field types](../concepts/field-types).

## Primitive types

`int`, `float`, `bool`, `str`, `bytes`, `pathlib.Path`, and subclasses of
`enum.Enum` are supported. Dictionary keys can be `str`, `int`, `bool`,
`float`, `bytes`, or enum members. `Any` accepts any supported value.
See the [Enum example](../concepts/field-types#fixed-choices-with-enum).

## Lists

`typing.List[T]` creates a typed `ListConfig` field. On Python 3.9 or newer,
the equivalent `list[T]` spelling is also available. Their
elements are validated when inserted or replaced. `T` can itself be a
supported container or structured config type.

## Tuple annotations

`typing.Tuple[...]` is accepted in 2.3, but the config value is represented
as a mutable `ListConfig`. Native tuple inputs are also converted to
`ListConfig`. This representation changes in
[OmegaConf 2.4](/docs/next/migration/2.4#tuple-inputs-no-longer-become-mutable-lists).

## Dictionaries

`typing.Dict[K, V]` creates a typed `DictConfig` field. On Python 3.9 or newer,
the equivalent `dict[K, V]` spelling is also available. Keys
use the supported dictionary key types above; values can be any supported
type. Nested forms such as `typing.Dict[str, typing.List[int]]` are valid.

## Nested containers

Each level retains its declared type, so later mutations are validated too:

```python
>>> from dataclasses import dataclass, field
>>> from typing import Dict, List
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Ports:
...     groups: Dict[str, List[int]] = field(
...         default_factory=lambda: {"web": [80]}
...     )
>>> cfg = OmegaConf.structured(Ports)
>>> cfg.groups["web"].append(443)
>>> list(cfg.groups["web"])
[80, 443]

```

## Optional types

`Optional[T]` permits `None` in a typed field. See
[optional fields](../concepts/optional-fields) for an example. A field's
type and its [missing state](../concepts/missing-values) are independent.

## Unions

`typing.Union[...]` can combine supported scalar types. Union selection is
strict: OmegaConf does not convert an assigned value merely to make it match
one of several branches. Wrapping a branch in `Optional` makes the whole
union optional.

```python
>>> from dataclasses import dataclass
>>> from typing import Union
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Choice:
...     value: Union[str, float] = 10.1
>>> cfg = OmegaConf.structured(Choice)
>>> cfg.value, type(cfg.value).__name__
(10.1, 'float')
>>> cfg.value = "10.1"
>>> cfg.value, type(cfg.value).__name__
('10.1', 'str')

```

Assigning an `int` here is rejected; it is not converted to `float` just
to find a union branch.

The [2.4 type reference](/docs/next/reference/types) describes new `Literal`,
typed container union, structured union, and `TupleConfig` behavior.
