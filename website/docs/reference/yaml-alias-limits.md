---
title: YAML alias limits
description: Understand and configure limits on YAML alias expansion.
---

OmegaConf limits the number of nodes produced by YAML alias expansion. This
protects applications from unexpectedly large input, including YAML bombs.
If a file from an untrusted source hits the limit, simplify its anchors,
aliases, or merge keys rather than disabling the protection.

For trusted YAML that legitimately needs more expansion, set a larger limit
at the call site:

```python
cfg = OmegaConf.load("config.yaml", max_yaml_expanded_nodes=50_000)
cfg = OmegaConf.create(yaml_string, max_yaml_expanded_nodes=50_000)
```

Passing `None` disables the limit for trusted input. If you do not control
the call site, set `OMEGACONF_MAX_YAML_EXPANDED_NODES` to a positive integer,
or `none` to disable the limit. An explicit function argument takes
precedence over the environment variable.

The default is 10,000 expanded nodes. OmegaConf also rejects documents over
1,000 expanded nodes when aliases make them more than 100 times larger than
the unexpanded document. Scalar keys and values, mappings, and lists all
count. Recursive aliases are rejected even if the expansion limit is
disabled.
