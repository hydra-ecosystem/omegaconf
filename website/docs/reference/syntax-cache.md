---
title: Syntax cache controls
description: Configure the memory budget for interpolation syntax caching.
---

OmegaConf caches parsed interpolation syntax to speed up repeated reads. Values
and resolver results remain dynamic. Each thread has its own parser and syntax
cache; the cache stores syntax independently of the configuration using it.

Configure the global per-thread memory budget through `OmegaConf.control`:

```python
from omegaconf import OmegaConf

OmegaConf.control.set_syntax_cache_max_bytes(4 * 1024 * 1024)
assert OmegaConf.control.get_syntax_cache_max_bytes() == 4 * 1024 * 1024

# Disable syntax caching.
OmegaConf.control.set_syntax_cache_max_bytes(0)
```

### `set_syntax_cache_max_bytes`

```python
OmegaConf.control.set_syntax_cache_max_bytes(max_bytes: int) -> None
```

Set the accounted syntax-cache memory budget **per thread**. The default is
4 MiB. Pass a nonnegative integer number of bytes; zero disables syntax caching.
Booleans and non-integers raise `TypeError`; negative integers raise `ValueError`.

Admission and eviction depend on estimated retained parse-tree memory, including
tokens and input streams, rather than expression length. Trees exceeding 256 KiB
or the configured budget are parsed without being cached. The cache evicts least
recently used entries to fit the budget and keeps at most 256 entries.

New threads use the current setting. Existing threads apply changes on their
next syntax-cache operation, evicting entries to fit a smaller budget or clearing
their cache when disabled. Idle threads retain their entries until that operation
or thread exit. Operations already in progress may finish under the previous
setting. Concurrent setters are serialized; parsers and caches stay thread-local.

This is an accounted retained-cache budget, not a process RSS limit. Each live
thread has its own allowance. Allocator overhead, temporary parsing allocations,
uncollected objects, and the live parser's most recent input/tree are outside the
cache budget. Changing the setting does not immediately reclaim all memory.

### `get_syntax_cache_max_bytes`

```python
OmegaConf.control.get_syntax_cache_max_bytes() -> int
```

Return the global configured budget in bytes per thread. This is the setting,
not measured memory usage or the budget last observed by an idle thread.

These controls do not affect resolver-result caches enabled with
`OmegaConf.register_resolver(..., use_cache=True)`. Use
[`OmegaConf.clear_cache(cfg)`](./python-api/omegaconf#clear_cache) to clear those
cached results.
