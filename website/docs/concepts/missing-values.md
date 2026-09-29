---
title: Missing values
description: Mark a value that must be supplied before it can be read.
---

Use `???` for a value that must be supplied later. Reading it raises
`MissingMandatoryValue`; `OmegaConf.is_missing()` lets you check it without
reading it:

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({
...     "host": "???",
...     "port": 80,
... })
>>> OmegaConf.is_missing(cfg, "host")
True
>>> cfg.host
Traceback (most recent call last):
...
omegaconf.errors.MissingMandatoryValue: Missing mandatory value: host
    full_key: host
    object_type=dict

```

`MISSING` is the Python spelling of the same marker. `None` is an ordinary
value, not a missing marker.

## Literal `???` text

In 2.4, prefix `???` with a backslash to store those three characters as
literal text. YAML quoting alone does not change the missing marker:

```python
>>> cfg = OmegaConf.create({
...     "required": "???",
...     "literal": r"\???",
... })
>>> OmegaConf.is_missing(cfg, "required")
True
>>> cfg.literal == "???"
True
>>> OmegaConf.is_missing(cfg, "literal")
False

```

The literal value retains a marker internally so it remains literal through
interpolation and serialization. When checking a detached value, use
`OmegaConf.is_missing(value)` instead of comparing it with the string `???`.
For a literal backslash followed by `???`, write `\\???` in the config input.

Next, learn how [merging config sources](../guides/merge) treats missing values.
