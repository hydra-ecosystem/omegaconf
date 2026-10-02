---
title: OmegaConf has a new home
slug: omegaconf-has-a-new-home
description: The OmegaConf repository has moved from omry/omegaconf to hydra-ecosystem/omegaconf.
authors: [omry]
---

I'm happy to share that I've moved the repository from
[`omry/omegaconf`](https://github.com/omry/omegaconf) to
[`hydra-ecosystem/omegaconf`](https://github.com/hydra-ecosystem/omegaconf).

For years, OmegaConf's home has been my personal GitHub account. During that
time, people have helped it grow by contributing code, reporting bugs, asking
questions, and sharing how they use it. I'm grateful for that support.

<!-- truncate -->

## A shared home with Hydra

In August, I [wrote on my blog](https://yadan.net/blog/hydras-next-chapter/)
about [Hydra's move to independent stewardship](https://hydra.cc/blog/2026/08/13/independent-stewardship/).
I also mentioned that OmegaConf would join it in the
[Hydra Ecosystem organization](https://github.com/hydra-ecosystem).
That move is now complete.

In recent months, I've returned to actively maintaining Hydra and OmegaConf.
Hydra builds on OmegaConf, so work on one often goes hand in hand with work on
the other. Bringing their repositories together gives both projects a shared
long-term home.

## What this means for you

If you use OmegaConf, you can keep using it as you do today. The package is
still `omegaconf`, the imports are the same, and the move does not require an
upgrade or reinstall.

The existing repository was transferred with its commit history, issues, pull
requests, and releases. GitHub redirects the old address, so existing links
and Git remotes continue to work. For new issues and pull requests, please use
the [new repository](https://github.com/hydra-ecosystem/omegaconf).

If you have a local Git clone, you can update its remote at your convenience:

```sh
git remote set-url origin https://github.com/hydra-ecosystem/omegaconf.git
```

Thank you for the time and care you've put into OmegaConf. I'm looking forward
to continuing the work with you and keeping it useful for the people who
depend on it.
