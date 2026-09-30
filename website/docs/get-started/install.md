---
title: Install OmegaConf
description: Install the 2.4 prerelease and check that it works.
---

OmegaConf 2.4 requires Python 3.10 or newer. Install the release candidate in
the environment where you run your Python project:

```sh
python -m pip install --pre 'omegaconf>=2.4.0rc1,<2.5'
```

Check the installed version:

```sh
python -m pip show omegaconf
```

For the current stable release, use the [2.3 installation guide](/docs/get-started/install)
instead. When you're ready, [create your first config](./first-config).
