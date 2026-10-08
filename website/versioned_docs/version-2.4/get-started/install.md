---
title: Install OmegaConf
description: Install OmegaConf 2.4 and check that it works.
---

OmegaConf 2.4 requires Python 3.10 or newer. Install the stable release in
the environment where you run your Python project:

```sh
python -m pip install 'omegaconf>=2.4,<2.5'
```

Check the installed version:

```sh
python -m pip show omegaconf
```

For projects that require the earlier release, use the
[2.3 installation guide](/docs/2.3/get-started/install).
When you're ready, [create your first config](./first-config).
