---
title: Inspect configs in a debugger
description: Use the PyDev.Debugger extension bundled with OmegaConf 2.3.
---

OmegaConf 2.3 includes a PyDev.Debugger extension in the `omegaconf`
package. It improves config inspection in PyCharm, VS Code, and other
debuggers powered by PyDev.Debugger; no separate OmegaConf plugin package
is required for this version.

It shows interpolation and missing-value information in the debugger.
The default `USER` view focuses on the config as application code sees it.
Set `OC_PYDEVD_RESOLVER=DEV` to inspect OmegaConf's internal data model, or
`OC_PYDEVD_RESOLVER=DISABLE` to turn the extension off. See the
[2.3 debugger integration reference](https://omegaconf.readthedocs.io/en/2.3_branch/usage.html#debugger-integration)
for the released documentation.
