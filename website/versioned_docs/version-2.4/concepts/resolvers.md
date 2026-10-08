---
title: Resolver interpolation
description: Call named resolvers from config values.
---

[Node interpolation](./interpolation) references another value in the config.
Resolver interpolation uses `${name:arguments}` to call a named resolver,
a Python callable that computes a value. OmegaConf resolves the interpolation
when you access its value.

For example, the built-in `oc.env` resolver reads an environment variable:

```python
>>> import os
>>> from omegaconf import OmegaConf
>>> os.environ["OC_DOCS_COLOR"] = "blue"
>>> cfg = OmegaConf.create({"color": "${oc.env:OC_DOCS_COLOR}"})
>>> cfg.color
'blue'
>>> del os.environ["OC_DOCS_COLOR"]

```

Resolver arguments can themselves contain interpolations. Read the
[built-in resolver reference](../reference/built-in-resolvers) for available
names and argument rules. To register your own Python function, see
[Write a custom resolver](../guides/custom-resolvers). Both node references
and resolver interpolations can be resolved in place with
[`OmegaConf.resolve()`](./interpolation#resolve-now).

Next, learn how [structured configs](./structured-configs) validate values.
