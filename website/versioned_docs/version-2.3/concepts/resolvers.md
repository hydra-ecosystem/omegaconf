---
title: Resolver calls
description: Compute a config value with a named resolver.
---

[Node interpolation](./interpolation) reads another value in the config. A
resolver call computes a value. Its syntax has a colon:
`${name:arguments}`. OmegaConf evaluates the call when you read the value.

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
and resolver calls can be materialized with
[`OmegaConf.resolve()`](./interpolation#resolve-now).

Next, learn how [structured configs](./structured-configs) validate values.
