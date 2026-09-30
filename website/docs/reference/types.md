---
title: Supported types
description: Type annotations accepted by structured configs in OmegaConf 2.4.
---

Structured configs use dataclass or `attrs` field annotations to validate
values. They support primitive values, typed containers, other structured
configs, and several combinations of those types.
For runnable examples, see [field types](../concepts/field-types).

## Primitive types

`int`, `float`, `bool`, `str`, `bytes`, `pathlib.Path`, and subclasses of
`enum.Enum` are supported. Dictionary keys can be `str`, `int`, `bool`,
`float`, `bytes`, or enum members. `Any` accepts any supported value.
See the [Enum example](../concepts/field-types#fixed-choices-with-literal-and-enum).

## Lists

`list[T]` and `typing.List[T]` create typed `ListConfig` fields. Their
elements are validated when inserted or replaced. `T` can itself be a
supported container or structured config type.

## Tuples

`tuple[T1, T2]` defines a fixed-length tuple with positional types;
`tuple[T, ...]` defines a variable-length homogeneous tuple. Both create
immutable `TupleConfig` fields. Replace the whole tuple through its parent
when an update is needed. See the [tuple migration guide](../migration/2.4-tuples).

## Dictionaries

`dict[K, V]` and `typing.Dict[K, V]` create typed `DictConfig` fields. Keys
use the supported dictionary key types above; values can be any supported
type. Nested forms such as `dict[str, list[int]]` are valid.

## Nested containers

Each level retains its declared type, so later mutations are validated too:

```python
>>> from dataclasses import dataclass, field
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Ports:
...     groups: dict[str, list[int]] = field(
...         default_factory=lambda: {"web": [80]}
...     )
>>> cfg = OmegaConf.structured(Ports)
>>> cfg.groups["web"].append(443)
>>> list(cfg.groups["web"])
[80, 443]

```

## Literal

`typing.Literal[...]` restricts a field to a fixed set of values. Literals
also work inside containers and unions. See the
[field-types example](../concepts/field-types#fixed-choices-with-literal-and-enum).
When a value matches both a `Literal` member and a broader scalar member of
a union, the `Literal` branch wins regardless of annotation order.

## Optional types

`T | None` (equivalent to `Optional[T]`) permits `None` in a typed field. See
[optional fields](../concepts/optional-fields) for an example. A field's
type and its [missing state](../concepts/missing-values) are independent.

## Unions

`typing.Union[...]` can combine primitive, literal, typed container, or
structured config types. Union selection is strict: OmegaConf does not
convert an assigned value merely to make it match one of several branches.
If a union includes `Any`, it is equivalent to `Any`. Wrapping any branch in
`Optional` makes the whole union optional.
On Python 3.12 or newer, PEP 695 `type` aliases are transparent wherever
their expanded annotations are supported.

For `Union[list[int], list[str]]`, an empty list is ambiguous. Supply an
explicitly typed container to choose the intended branch:

```python
>>> from dataclasses import dataclass, field
>>> from typing import Union
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Items:
...     value: Union[list[int], list[str]] = field(default_factory=lambda: [1])
>>> cfg = OmegaConf.structured(Items)
>>> cfg.value = OmegaConf.typed_list([], element_type=str)
>>> cfg.value.append("hello")
>>> list(cfg.value)
['hello']

```

`OmegaConf.typed_dict()` performs the same role for dictionary branches.
The same rule applies to other values accepted by more than one container
branch: OmegaConf rejects the ambiguity instead of choosing the first branch.
After selection, element and key validation follow the selected branch. A
plain list or dict can select a branch when exactly one branch accepts it.

### Unions of structured configs

Pass a typed instance when multiple structured branches could accept a plain
mapping. OmegaConf selects the most specific declared branch for a typed
value according to its class hierarchy; it does not infer a class by matching
mapping keys.

```python
>>> from omegaconf import MISSING
>>> @dataclass
... class Dog:
...     name: str = MISSING
...     breed: str = MISSING
>>> @dataclass
... class Cat:
...     name: str = MISSING
...     indoor: bool = MISSING
>>> @dataclass
... class Owner:
...     pet: Dog | Cat = MISSING
>>> owner = OmegaConf.structured(Owner)
>>> owner.pet = Dog(name="Rex", breed="Lab")
>>> OmegaConf.get_type(owner, "pet") is Dog
True
>>> OmegaConf.update(owner, "pet", {"name": "Fido"}, merge=False)
>>> OmegaConf.get_type(owner, "pet") is Dog
True
>>> OmegaConf.is_missing(owner.pet, "breed")
True

```

The explicit replacement retains the selected `Dog` branch. A typed value can
switch to `Cat`. A merge from the same typed branch combines fields
recursively; a merge from a different typed branch replaces it. If no branch
is selected and multiple structured or dictionary branches accept a mapping,
supply a typed value to resolve the ambiguity. Once selected, the branch's
fields retain their ordinary structured-config validation and conversion
rules.

YAML does not carry a tag for the selected structured branch. After a
`to_yaml()` / `load()` round trip, restore the type with a typed value rather
than expecting OmegaConf to infer it from mapping keys.
