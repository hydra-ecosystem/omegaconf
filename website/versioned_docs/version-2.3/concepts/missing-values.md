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

In OmegaConf 2.3, the string `???` is always interpreted as missing when
stored in a config, even if it was quoted in YAML. The
[2.4 documentation](/docs/next/concepts/missing-values) describes the new
escape form for literal text.

Next, learn how [merging config sources](../guides/merge) treats missing values.
