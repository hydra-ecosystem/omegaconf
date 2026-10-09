# OmegaConf

|  | Description |
| --- | --- |
| Project | [![PyPI version](https://badge.fury.io/py/omegaconf.svg)](https://badge.fury.io/py/omegaconf)[![Downloads](https://pepy.tech/badge/omegaconf/month)](https://pepy.tech/project/omegaconf)![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue) |
| Code quality| [![CircleCI](https://dl.circleci.com/status-badge/img/gh/hydra-ecosystem/omegaconf/tree/main.svg?style=svg)](https://app.circleci.com/pipelines/github/hydra-ecosystem/omegaconf?branch=main)[![Coverage Status](https://coveralls.io/repos/github/hydra-ecosystem/omegaconf/badge.svg)](https://coveralls.io/github/hydra-ecosystem/omegaconf)|
| Docs, support, and ecosystem |[![Documentation Status](https://img.shields.io/github/actions/workflow/status/hydra-ecosystem/omegaconf/deploy-docs.yml?branch=main&label=docs)](https://omegaconf.cli.dev/)[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/hydra-ecosystem/omegaconf/main?filepath=legacy%2Frtd%2Fnotebook%2FTutorial.ipynb)[![Zulip chat](https://img.shields.io/badge/chat-Zulip-2e77d0?logo=zulip)](https://hydra-framework.zulipchat.com/)[![ecosystem: cli.dev](https://cli.dev/img/badges/cli-dev-ecosystem.svg)](https://cli.dev)|
| Backlog | [![Backlog Atlas dashboard](https://omry.github.io/backlog-atlas/badge.svg)](https://omry.github.io/backlog-atlas/) |


OmegaConf is a hierarchical configuration system, with support for merging configurations from multiple sources (YAML config files, dataclasses/objects and CLI arguments)
providing a consistent API regardless of how the configuration was created.

Legacy documentation is retained on [Read the Docs](https://omegaconf.readthedocs.io/),
with its sources under [`legacy/rtd/`](legacy/rtd/).

## Optional subprojects

- [`omegaconf-pydevd`](./subprojects/omegaconf-pydevd/README.md): optional `pydevd` debugger plugin for inspecting OmegaConf objects in supported debuggers.

## Releases

### Stable (2.4)
OmegaConf 2.4.0 is the current stable version and requires Python 3.10 or newer.
Released on October 9, 2026, it adds richer structured config typing, experimental
tuples, and improvements to interpolation, resolvers, merging, and validation.
Read the [release announcement](https://omegaconf.cli.dev/blog/omegaconf-2-4-0)
and review the upgrade guide before upgrading from 2.3.
* [What's new](https://github.com/hydra-ecosystem/omegaconf/releases/tag/v2.4.0)
* [Documentation](https://omegaconf.cli.dev/docs/)
* [Upgrade guide](https://omegaconf.cli.dev/docs/migration/2.4)
* [Source code](https://github.com/hydra-ecosystem/omegaconf/tree/2.4_branch)

Install with `pip install --upgrade omegaconf`

### Previous stable (2.3)
OmegaConf 2.3 is retained for projects that require the earlier release.
* [What's new](https://github.com/hydra-ecosystem/omegaconf/releases/tag/v2.3.0)
* [Documentation](https://omegaconf.cli.dev/docs/2.3/)
* [Source code](https://github.com/hydra-ecosystem/omegaconf/tree/2.3_branch)

Install with `pip install 'omegaconf<2.4'`
