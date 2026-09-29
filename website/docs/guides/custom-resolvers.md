---
title: Write a custom resolver
description: Add a computed interpolation and control its caching and validation.
---

A resolver is a Python callable used in a
[resolver call](../concepts/resolvers). Register it once
with a name, then use that name in `${name:arguments}`:

```python
>>> from omegaconf import OmegaConf
>>> OmegaConf.register_resolver("plus_ten_docs", lambda value: value + 10)
>>> cfg = OmegaConf.create({"result": "${plus_ten_docs:32}"})
>>> cfg.result
42

```

Resolver arguments are parsed from the interpolation expression. The resolver
runs when the node is accessed. Nested interpolation lets an argument come
from another config value, and a resolver may return a scalar, container, or
config node. Names may be namespaced (such as `myapp.add`), and an
interpolation may even select part of a resolver name.

For compatibility, a direct `???` argument reaches the resolver as text. If
an argument interpolates a missing field, evaluation fails before the
resolver runs. A resolver returning plain `"???"` makes its result missing;
return `r"\???"` to produce literal text instead. See
[missing values](../concepts/missing-values) for the escape rule.

If the callable declares the special keyword-only parameters `_parent_`,
`_node_`, or `_root_`, OmegaConf supplies the interpolation's parent
container, its value node, or the config root, respectively. This is useful
when a resolver needs to inspect its context without receiving that context
as explicit interpolation arguments.

```python
>>> def add_neighbors(left, right, *, _parent_):
...     return _parent_.get(left, 0) + _parent_.get(right, 0)
>>> OmegaConf.register_resolver("add_neighbors_docs", add_neighbors)
>>> cfg = OmegaConf.create({
...     "group": {
...         "a": 1,
...         "b": 2,
...         "total": "${add_neighbors_docs:a,b}",
...         "with_absent": "${add_neighbors_docs:a,absent}",
...     },
... })
>>> cfg.group.total, cfg.group.with_absent
(3, 1)

```

The name `absent` is passed as text; the resolver handles its absence through
`_parent_`. By contrast, `${add_neighbors_docs:${absent},b}` would fail while
evaluating the nested interpolation, before calling the resolver.

## Replace or cache a resolver

Registering a name that already exists raises `ValueError`. Pass
`replace=True` when deliberately replacing it. `use_cache=True` reuses a
result for the same literal argument strings, even if a nested interpolation
would now resolve to a different value; leave caching off when the function
depends on changing external state.

```python
>>> OmegaConf.register_resolver(
...     "cached_docs", lambda value: value * 2, use_cache=True
... )
>>> cfg = OmegaConf.create({
...     "source": 2,
...     "result": "${cached_docs:${source}}",
... })
>>> cfg.result
4
>>> cfg.source = 3
>>> cfg.result  # same literal argument expression, so the cached result wins
4

```

The older `register_new_resolver()` and `legacy_register_resolver()` methods
are deprecated in 2.4.

## Remove resolvers

### Clear one

`OmegaConf.clear_resolver(name)` returns `True` if it removed a registration
and `False` if the name was absent. It can remove a built-in, so check the
name before calling it.

```python
>>> OmegaConf.register_resolver("temporary_docs", lambda: 1)
>>> OmegaConf.clear_resolver("temporary_docs")
True
>>> OmegaConf.has_resolver("temporary_docs")
False

```

### Clear all

`OmegaConf.clear_resolvers()` removes custom registrations but retains the
built-ins:

```python
>>> OmegaConf.clear_resolvers()
>>> OmegaConf.has_resolver("oc.env")
True

```

## Validate annotations

OmegaConf 2.4 can check annotated resolver arguments and return values at
runtime. `annotation_validation="warn"` is the default in 2.4; use
`"error"` to reject mismatches or `"off"` to disable checking. Validation
does not convert values. With `"warn"`, a mismatch emits `UserWarning` and the
original value passes through; with `"error"`, a mismatch while evaluating a
config interpolation surfaces as `InterpolationResolutionError` caused by a
`TypeError`. Annotation problems discovered during registration also fail in
`"error"` mode. In `"warn"` mode, an uninspectable callable or an annotation
that cannot be resolved or checked emits a warning and registers the resolver
without annotation validation. OmegaConf 2.5 will change the default to
`"error"`; an explicit mode keeps the same behavior across versions. These
checks apply to the resolver's own call, separate from any validation imposed
by the destination config field.

```python
>>> def double_docs(value: int) -> int:
...     return value * 2
>>> OmegaConf.register_resolver(
...     "double_docs", double_docs, annotation_validation="error"
... )
>>> cfg = OmegaConf.create({
...     "value": 21,
...     "result": "${double_docs:${value}}",
... })
>>> cfg.result
42

```

With `"error"`, an argument that does not match its annotation prevents the
resolver from running. Accessing the interpolation raises
`InterpolationResolutionError` and preserves the validation failure in the
message:

```python
>>> invalid = OmegaConf.create({
...     "result": "${double_docs:not-a-number}",
... })
>>> invalid.result  # doctest: +ELLIPSIS
Traceback (most recent call last):
...
omegaconf.errors.InterpolationResolutionError: TypeError raised while resolving interpolation: Resolver 'double_docs' parameter 'value' expected int, got str at full key 'result'
    full_key: result
    object_type=dict

```

If `"warn"` cannot resolve or check an annotation during registration, it
emits one warning and registers the resolver with annotation validation
disabled. The resolver still runs, including for values that would not match
its remaining annotations:

```python
>>> import warnings
>>> def unchecked_docs(value: "UnavailableDocsType") -> int:
...     return value
>>> with warnings.catch_warnings(record=True) as caught:
...     warnings.simplefilter("always")
...     OmegaConf.register_resolver(
...         "unchecked_docs", unchecked_docs, annotation_validation="warn"
...     )
>>> len(caught)
1
>>> "cannot resolve annotations" in str(caught[0].message)
True
>>> cfg = OmegaConf.create({"result": "${unchecked_docs:text}"})
>>> cfg.result
'text'

```

Parameter validation runs after nested arguments are evaluated and before
cache lookup. Return values are checked before caching, including on cache
hits. Supported annotations include runtime-checkable classes, unions,
`Optional`, `Literal`, and `Annotated` (whose metadata is ignored).
Parameterized containers are checked only at their outer runtime type:
`list[int]` checks that a value is a Python `list`, not each element. A
`ListConfig` is not a Python `list`; annotate `ListConfig | list` if both are
intended. Injected `_parent_`, `_node_`, and `_root_` parameters are exempt
from annotation validation.

See [built-in resolvers](../reference/built-in-resolvers) for `oc.env`,
`oc.select`, and other resolvers provided by OmegaConf.
