---
title: Field types
description: Define typed containers, fixed choices, and alternative types.
---

A [structured config](./structured-configs) checks values against its field
annotations. Beyond `int` and `str`, annotations can describe the contents of
containers, a fixed set of choices, or several accepted types.

## Lists and dictionaries

`list[int]` checks list elements; `dict[str, int]` checks dictionary keys and
values. Use a `default_factory` for mutable defaults:

```python
>>> from dataclasses import dataclass, field
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Inventory:
...     counts: list[int] = field(default_factory=lambda: [1, 2])
...     ports: dict[str, int] = field(default_factory=lambda: {"web": 80})
>>> cfg = OmegaConf.structured(Inventory)
>>> cfg.counts.append(3)
>>> list(cfg.counts)
[1, 2, 3]
>>> cfg.ports["admin"] = 8080
>>> cfg.ports["admin"]
8080

```

OmegaConf keeps these fields as typed `ListConfig` and `DictConfig` containers,
so later changes are checked too. Container element types may themselves be
supported container or structured config types.

## Fixed choices with `Literal` and Enum

`Literal` limits a field to the values listed in its annotation:

```python
>>> from typing import Literal
>>> @dataclass
... class Job:
...     mode: Literal["train", "eval"] = "train"
>>> job = OmegaConf.structured(Job)
>>> job.mode = "eval"
>>> job.mode
'eval'

```

Use an `Enum` when the choices should be reusable named members in Python:

```python
>>> from enum import Enum
>>> class RunMode(Enum):
...     TRAIN = "train"
...     EVAL = "eval"
>>> @dataclass
... class EnumJob:
...     mode: RunMode = RunMode.TRAIN
>>> enum_job = OmegaConf.structured(EnumJob)
>>> enum_job.mode = RunMode.EVAL
>>> enum_job.mode is RunMode.EVAL
True

```

When a string-valued Enum comes from text, `OmegaConf.update()` accepts
either the member name or its value:

```python
>>> OmegaConf.update(enum_job, "mode", "TRAIN")
>>> enum_job.mode is RunMode.TRAIN
True
>>> OmegaConf.update(enum_job, "mode", "eval")
>>> enum_job.mode is RunMode.EVAL
True

```

## Alternative types with unions

Use a union when a field may hold values of different types:

```python
>>> @dataclass
... class Choice:
...     value: int | str = 1
>>> choice = OmegaConf.structured(Choice)
>>> choice.value = "auto"
>>> choice.value
'auto'

```

Union selection is strict: OmegaConf does not convert a value merely to make
it match another branch. For ambiguous unions of typed containers, see the
[supported types reference](../reference/types#unions).

Next, learn how an [optional field](./optional-fields) accepts `None`.
