---
title: Python API
description: Find the OmegaConf operations you need.
---

OmegaConf's public API centers on the `OmegaConf` class. Start with an
operation below, then follow the link to its generated signature, parameters,
and return value.

| I want to… | Start with |
| --- | --- |
| Create a config from Python data or YAML | [`OmegaConf.create()`](./python-api/omegaconf#create) |
| Combine configs, with later values taking precedence | [`OmegaConf.merge()`](./python-api/omegaconf#merge) |
| Read a nested value by path | [`OmegaConf.select()`](./python-api/omegaconf#select) |
| Write a nested value by path | [`OmegaConf.update()`](./python-api/omegaconf#update) |
| Convert a config to a Python container | [`OmegaConf.to_container()`](./python-api/omegaconf#to_container) |
| Serialize a config to a YAML string | [`OmegaConf.to_yaml()`](./python-api/omegaconf#to_yaml) |
| Resolve interpolations in place | [`OmegaConf.resolve()`](./python-api/omegaconf#resolve) |

### Types and helpers

Use [`MISSING`](./python-api/omegaconf#missing) to mark a mandatory missing value,
[`II`](./python-api/omegaconf#ii) and [`SI`](./python-api/omegaconf#si) for
interpolations, and [`open_dict`](./python-api/omegaconf#open_dict),
[`read_write`](./python-api/omegaconf#read_write), or
[`flag_override`](./python-api/omegaconf#flag_override) for temporary flag
changes.

For explicit container types in 2.4, see
[`typed_list`](./python-api/omegaconf#typed_list),
[`typed_dict`](./python-api/omegaconf#typed_dict), and
[`typed_tuple`](./python-api/omegaconf#typed_tuple).

[Browse every public symbol →](./python-api/omegaconf)
