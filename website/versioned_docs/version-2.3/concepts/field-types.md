---
title: Field types
description: Define typed containers, enum choices, and alternative types.
---

A [structured config](./structured-configs) checks values against its field
annotations. Beyond `int` and `str`, annotations can describe the contents of
containers, a fixed set of choices, or several accepted types.

## Lists and dictionaries

`List[int]` checks list elements; `Dict[str, int]` checks dictionary keys and
values. Use a `default_factory` for mutable defaults:

```python
>>> from dataclasses import dataclass, field
>>> from typing import Dict, List, Union
>>> from omegaconf import OmegaConf
>>> @dataclass
... class Inventory:
...     counts: List[int] = field(default_factory=lambda: [1, 2])
...     ports: Dict[str, int] = field(default_factory=lambda: {"web": 80})
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

## Fixed choices with Enum

Use an `Enum` when a field must hold one of several named members:

```python
>>> from enum import Enum
>>> class RunMode(Enum):
...     TRAIN = "train"
...     EVAL = "eval"
>>> @dataclass
... class Job:
...     mode: RunMode = RunMode.TRAIN
>>> job = OmegaConf.structured(Job)
>>> job.mode = RunMode.EVAL
>>> job.mode is RunMode.EVAL
True

```

When an Enum comes from text, `OmegaConf.update()` accepts its member name:

```python
>>> OmegaConf.update(job, "mode", "TRAIN")
>>> job.mode is RunMode.TRAIN
True

```

OmegaConf 2.3 does not accept the string value `"eval"` in place of the
member name `"EVAL"`. The 2.4 guide describes the expanded behavior.

## Alternative types with unions

Use a union when a field may hold values of different supported scalar types:

```python
>>> @dataclass
... class Choice:
...     value: Union[int, str] = 1
>>> choice = OmegaConf.structured(Choice)
>>> choice.value = "auto"
>>> choice.value
'auto'

```

Union selection is strict: OmegaConf does not convert a value merely to make
it match another branch. `Literal` fields and unions of typed containers are
supported in [OmegaConf 2.4](/docs/next/concepts/field-types).

Next, learn how an [optional field](./optional-fields) accepts `None`.
