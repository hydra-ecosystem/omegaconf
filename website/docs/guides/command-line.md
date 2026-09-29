---
title: Apply command-line overrides
description: Parse key=value overrides and merge them with a base config.
---

`OmegaConf.from_dotlist()` parses `key=value` strings. It builds nested
containers from dotted paths and parses values as YAML. Merge the resulting
config after your defaults so it wins on conflicts:

```python
>>> from omegaconf import OmegaConf
>>> defaults = OmegaConf.create({
...     "server": {"port": 80},
...     "debug": False,
... })
>>> overrides = OmegaConf.from_dotlist(["server.port=8080", "debug=true"])
>>> cfg = OmegaConf.merge(defaults, overrides)
>>> cfg.server.port, cfg.debug
(8080, True)

```

`OmegaConf.from_cli()` reads the same format from the command-line arguments
in `sys.argv[1:]`. Call it without arguments in an application that receives
OmegaConf overrides directly. An argument parser may collect the strings and
pass them to `from_dotlist()` instead.

In 2.4, backslash-escape a literal dot, bracket, or equals sign in a key
path. For example, `r"a\.b=10"` addresses the key `a.b` rather than nested
keys `a` and `b`. Interpolation paths and `OmegaConf.select()` use the same
key-path escaping rules.

When passing an override through a shell, quote it so the backslash reaches
Python unchanged:

```sh
python app.py 'a\.b=10'
```
