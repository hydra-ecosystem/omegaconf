---
title: Inspect configs in a debugger
description: Enable OmegaConf-aware views in PyDev-based debuggers.
---

The optional `omegaconf-pydevd` package improves OmegaConf inspection in
PyCharm, VS Code, and other debuggers powered by PyDev.Debugger:

```sh
python -m pip install omegaconf-pydevd
```

It shows interpolation and missing-value information in the debugger.
The default `USER` view focuses on the config as application code sees it.
Set `OC_PYDEVD_RESOLVER=DEV` to inspect OmegaConf's internal data model, or
`OC_PYDEVD_RESOLVER=DISABLE` to turn the extension off. See the
[plugin README](https://github.com/hydra-ecosystem/omegaconf/tree/2.4_branch/subprojects/omegaconf-pydevd/README.md)
for setup and examples.
