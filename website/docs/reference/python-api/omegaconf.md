---
title: OmegaConf symbols
description: OmegaConf 2.4.1.dev0 generated Python API
toc_max_heading_level: 2
---

API snapshot from OmegaConf 2.4.1.dev0 source. For task-based entry points, see the [Python API overview](../python-api).

OmegaConf module

## `II`

```python
II(interpolation: str) -> Any
```

Equivalent to ``${interpolation}``

**Parameters:**

- **interpolation** (<code>str</code>) – 

**Returns:**

- <code>Any</code> – input ``${node}`` with type Any

## `MISSING`

```python
MISSING: Any = '???'
```

## `OmegaConf`

```python
OmegaConf() -> None
```

OmegaConf primary class

### `can_select`

```python
can_select(
    cfg: Container,
    key: str,
    *,
    throw_on_resolution_failure: bool = True,
    throw_on_missing: bool = False
) -> bool
```

Return ``True`` if ``OmegaConf.select()`` can select a value from a config.

This uses the same key path syntax and behavior flag names as
``select()`` for convenience, but ``can_select()`` does not raise for
select failures. It returns ``False`` instead of raising or returning a
default when the path cannot be selected. A selected ``None`` value
counts as selectable.

**Parameters:**

- **cfg** (<code>Container</code>) – Config node to select from
- **key** (<code>str</code>) – Key path to select (dot/bracket notation, backslash-escapable)
- **throw_on_resolution_failure** (<code>bool</code>) – Treat an interpolation resolution error
as not selectable
- **throw_on_missing** (<code>bool</code>) – Treat selecting a missing key (with the value
'???') as not selectable

**Returns:**

- <code>bool</code> – ``True`` if the key can be selected, otherwise ``False``.

### `clear_cache`

```python
clear_cache(conf: BaseContainer) -> None
```

Clear the resolver cache for ``conf``.

**Parameters:**

- **conf** (<code>BaseContainer</code>) – An OmegaConf container.

### `clear_resolver`

```python
clear_resolver(name: str) -> bool
```

Clear(remove) any resolver only if it exists.

Returns a bool: True if resolver is removed and False if not removed.

> **Warning:** This method can remove default resolvers as well.

**Parameters:**

- **name** (<code>str</code>) – Name of the resolver.

**Returns:**

- <code>bool</code> – A bool (``True`` if resolver is removed, ``False`` if not found before removing).

### `clear_resolvers`

```python
clear_resolvers() -> None
```

Clear(remove) all OmegaConf resolvers, then re-register OmegaConf's default resolvers.

### `copy_cache`

```python
copy_cache(from_config: BaseContainer, to_config: BaseContainer) -> None
```

Copy the resolver cache from one config to another.

**Parameters:**

- **from_config** (<code>BaseContainer</code>) – Source container whose cache is copied.
- **to_config** (<code>BaseContainer</code>) – Destination container that receives the cache copy.

### `create`

```python
create(
    obj: Any = _DEFAULT_MARKER_,
    parent: BaseContainer | None = None,
    flags: dict[str, bool] | None = None,
    *,
    max_yaml_expanded_nodes: int | None = _DEFAULT_MAX_YAML_EXPANDED_NODES
) -> DictConfig | ListConfig | TupleConfig | None
```

Create an OmegaConf config from ``obj``.

``obj`` may be a YAML string, a dict, a list or tuple, a dataclass or attrs class (type or
instance), an existing ``DictConfig`` / ``ListConfig`` / ``TupleConfig``,
or ``None``.
Omitting ``obj`` (or passing ``{}`` explicitly) returns an empty ``DictConfig``.

**Parameters:**

- **obj** (<code>Any</code>) – Source object to build the config from.
- **parent** (<code>BaseContainer | None</code>) – Optional parent node.
- **flags** (<code>dict[str, bool] | None</code>) – Optional flags dict (e.g. ``{"readonly": True}``).
- **max_yaml_expanded_nodes** (<code>int | None</code>) – Maximum YAML nodes after alias expansion
when ``obj`` is a YAML string. By default, OmegaConf uses the
``OMEGACONF_MAX_YAML_EXPANDED_NODES`` environment variable if set,
otherwise ``10_000``. Explicit arguments override the environment.
Pass ``None`` only for trusted input. See
https://omegaconf.cli.dev/docs/reference/yaml-alias-limits/.

**Returns:**

- <code>DictConfig | ListConfig | TupleConfig | None</code> – A ``DictConfig``, ``ListConfig``, ``TupleConfig``, or ``None``.

### `from_cli`

```python
from_cli(args_list: list[str] | None = None) -> DictConfig
```

Create a config from command-line arguments (``sys.argv[1:]`` by default).

Each argument must be a dotlist-style string such as ``"foo.bar=1"``.

**Parameters:**

- **args_list** (<code>list[str] | None</code>) – Explicit list of dotlist strings; defaults to ``sys.argv[1:]``.

**Returns:**

- <code>DictConfig</code> – A ``DictConfig`` built from the arguments.

### `from_dotlist`

```python
from_dotlist(dotlist: list[str]) -> DictConfig
```

Creates a config from a list of dotlist-style strings (``"key=value"`` pairs).

Each entry is split on the first *unescaped* ``=``.  Everything before
it is the key path; everything after it is the value.  Key paths follow
the same dot/bracket syntax as :meth:`select` and :meth:`update`.

**Backslash escaping in keys:**
Use a backslash to include a literal special character in a key name.
The escapable characters are ``.``, ``[``, ``]``, and ``=``.

- ``r"a\.b=1"``    — key is ``"a.b"`` (dot is part of the key)
- ``r"a\=b=1"``    — key is ``"a=b"`` (``=`` is part of the key;
  the second ``=`` is the key/value separator)

Values may contain ``=`` freely; only the first unescaped ``=`` separates
key from value (e.g. ``"url=http://x?a=1"`` gives key ``url``,
value ``http://x?a=1``).

**CLI / shell note:** When using :meth:`from_cli`, arguments pass through
the shell before reaching Python.  A single backslash in a shell argument
is usually consumed by the shell, so you must double it (``\\``) or
quote the argument (``'a\.b=1'``) to preserve it.

**Parameters:**

- **dotlist** (<code>list[str]</code>) – A list of dotlist-style strings, e.g. ``["foo.bar=1", "baz=qux"]``.

**Returns:**

- <code>DictConfig</code> – A ``DictConfig`` object created from the dotlist.

### `get_cache`

```python
get_cache(conf: BaseContainer) -> dict[str, Any]
```

Return the resolver cache for ``conf``.

**Parameters:**

- **conf** (<code>BaseContainer</code>) – An OmegaConf container.

**Returns:**

- <code>dict[str, Any]</code> – The resolver cache dict (resolver name -> cached values).

### `get_type`

```python
get_type(obj: Any, key: str | None = None) -> type[Any] | None
```

Return the type of ``obj``, or of ``obj[key]`` when ``key`` is provided.

For structured configs this is the underlying dataclass or attrs class.
For plain containers it is ``dict``, ``list``, or ``tuple``.

**Parameters:**

- **obj** (<code>Any</code>) – An OmegaConf node or container.
- **key** (<code>str | None</code>) – Optional key within ``obj`` to inspect.

**Returns:**

- <code>type[Any] | None</code> – The Python type, or ``None`` if not determinable.

### `has_resolver`

```python
has_resolver(name: str) -> bool
```

Return ``True`` if a resolver with the given name is registered.

**Parameters:**

- **name** (<code>str</code>) – Resolver name to check.

**Returns:**

- <code>bool</code> – ``True`` if registered, ``False`` otherwise.

### `is_config`

```python
is_config(obj: Any) -> bool
```

Return ``True`` if ``obj`` is an OmegaConf container.

**Parameters:**

- **obj** (<code>Any</code>) – Object to test.

**Returns:**

- <code>bool</code> – ``True`` if ``obj`` is an OmegaConf container, ``False`` otherwise.

### `is_dict`

```python
is_dict(obj: Any) -> bool
```

Return ``True`` if ``obj`` is an OmegaConf ``DictConfig``.

**Parameters:**

- **obj** (<code>Any</code>) – Object to test.

**Returns:**

- <code>bool</code> – ``True`` if ``obj`` is a ``DictConfig``, ``False`` otherwise.

### `is_interpolation`

```python
is_interpolation(node: Any, key: int | str | None = None) -> bool
```

Return ``True`` if the target node is an interpolation (e.g. ``${foo.bar}``).

If ``key`` is provided, checks ``node[key]``; otherwise checks ``node`` itself.

**Parameters:**

- **node** (<code>Any</code>) – An OmegaConf node, or a container when ``key`` is given.
- **key** (<code>int | str | None</code>) – Optional key within ``node`` to inspect.

**Returns:**

- <code>bool</code> – ``True`` if the value is an interpolation, ``False`` otherwise.

### `is_list`

```python
is_list(obj: Any) -> bool
```

Return ``True`` if ``obj`` is an OmegaConf ``ListConfig``.

**Parameters:**

- **obj** (<code>Any</code>) – Object to test.

**Returns:**

- <code>bool</code> – ``True`` if ``obj`` is a ``ListConfig``, ``False`` otherwise.

### `is_missing`

```python
is_missing(cfg: Any, key: DictKeyType | object = _DEFAULT_MARKER_) -> bool
```

Return ``True`` if ``cfg[key]`` or a detached value is missing.

**Parameters:**

- **cfg** (<code>Any</code>) – An OmegaConf container.
- **key** (<code>DictKeyType | object</code>) – Optional key (str for DictConfig, int for a sequence) to check.

**Returns:**

- <code>bool</code> – ``True`` if the value is missing, ``False`` otherwise.

### `is_readonly`

```python
is_readonly(conf: Node) -> bool | None
```

Return the effective read-only flag of ``conf``.

**Parameters:**

- **conf** (<code>Node</code>) – An OmegaConf node.

**Returns:**

- <code>bool | None</code> – ``True`` if read-only, ``False`` if writable, ``None`` if not set
(inherits from parent).

### `is_sequence`

```python
is_sequence(obj: Any) -> bool
```

Return ``True`` for ``ListConfig`` and ``TupleConfig`` values only.

### `is_struct`

```python
is_struct(conf: Container) -> bool | None
```

Return the effective struct flag of ``conf``.

**Parameters:**

- **conf** (<code>Container</code>) – An OmegaConf container.

**Returns:**

- <code>bool | None</code> – ``True`` if struct mode is on, ``False`` if off, ``None`` if not set
(inherits from parent).

### `is_tuple`

```python
is_tuple(obj: Any) -> bool
```

Return ``True`` if ``obj`` is an OmegaConf ``TupleConfig``.

Native Python tuples return ``False``.

### `legacy_register_resolver`

```python
legacy_register_resolver(name: str, resolver: Resolver) -> None
```

Deprecated since version 2.4. Use ``OmegaConf.register_resolver()`` instead.

### `load`

```python
load(
    file_: str | pathlib.Path | IO[Any],
    *,
    max_yaml_expanded_nodes: int | None = _DEFAULT_MAX_YAML_EXPANDED_NODES
) -> DictConfig | ListConfig
```

Load a YAML config from a file path or file-like object.

**Parameters:**

- **file_** (<code>str | Path | IO[Any]</code>) – A file path (str or ``pathlib.Path``) or an open file object.
- **max_yaml_expanded_nodes** (<code>int | None</code>) – Maximum YAML nodes after alias expansion.
By default, OmegaConf uses the
``OMEGACONF_MAX_YAML_EXPANDED_NODES`` environment variable if set,
otherwise ``10_000``. Explicit arguments override the environment.
Pass ``None`` only for trusted input. See
https://omegaconf.cli.dev/docs/reference/yaml-alias-limits/.

**Returns:**

- <code>DictConfig | ListConfig</code> – A ``DictConfig`` or ``ListConfig`` parsed from the YAML content.

### `masked_copy`

```python
masked_copy(conf: DictConfig, keys: str | list[str]) -> DictConfig
```

Create a masked copy of of this config that contains a subset of the keys

**Parameters:**

- **conf** (<code>DictConfig</code>) – DictConfig object
- **keys** (<code>str | list[str]</code>) – keys to preserve in the copy

**Returns:**

- <code>DictConfig</code> – The masked ``DictConfig`` object.

### `merge`

```python
merge(
    *configs: DictConfig
    | ListConfig
    | TupleConfig
    | dict[DictKeyType, Any]
    | list[Any]
    | tuple[Any, ...]
    | Any
) -> ListConfig | TupleConfig | DictConfig
```

Merge a list of previously created configs into a single one

Note for maintainers: changes to merge behavior should also consider
whether OmegaConf.unsafe_merge() needs the same coverage.

**Parameters:**

- **configs** (<code>DictConfig | ListConfig | TupleConfig | dict[DictKeyType, Any] | list[Any] | tuple[Any, ...] | Any</code>) – Input configs

**Returns:**

- <code>ListConfig | TupleConfig | DictConfig</code> – the merged config object.

### `missing_keys`

```python
missing_keys(cfg: Any, *, resolve_custom_resolvers: bool = False) -> set[str]
```

Returns a set of missing keys in a dotlist style.

Node interpolations that dereference missing values are reported as missing
keys, whether they are the full value or part of a string.

**Parameters:**

- **cfg** (<code>Any</code>) – An ``OmegaConf.Container``,
or a convertible object via ``OmegaConf.create`` (dict, list, ...).
- **resolve_custom_resolvers** (<code>bool</code>) – If ``True``, custom resolver
interpolations are resolved and reported as missing when they
dereference missing values. If ``False`` (the default),
custom resolver interpolations are not resolved and are not
reported as missing keys.

**Returns:**

- <code>set[str]</code> – set of strings of the missing keys.

**Raises:**

- <code>ValueError</code> – On input not representing a config.

### `register_new_resolver`

```python
register_new_resolver(
    name: str,
    resolver: Resolver,
    *,
    replace: bool = False,
    use_cache: bool = False
) -> None
```

Deprecated since version 2.4. Use ``OmegaConf.register_resolver()`` instead.

### `register_resolver`

```python
register_resolver(
    name: str,
    resolver: Resolver,
    *,
    replace: bool = False,
    use_cache: bool = False,
    annotation_validation: Literal["off", "warn", "error"] = "warn"
) -> None
```

Register a resolver.

**Parameters:**

- **name** (<code>str</code>) – Name of the resolver.
- **resolver** (<code>Resolver</code>) – Callable whose arguments are provided in the interpolation,
e.g., with ${foo:x,0,${y.z}} these arguments are respectively "x" (str),
0 (int) and the value of ``y.z``.
- **replace** (<code>bool</code>) – If set to ``False`` (default), then a ``ValueError`` is raised if
an existing resolver has already been registered with the same name.
If set to ``True``, then the new resolver replaces the previous one.
NOTE: The cache on existing config objects is not affected, use
``OmegaConf.clear_cache(cfg)`` to clear it.
- **use_cache** (<code>bool</code>) – Whether the resolver's outputs should be cached. The cache is
based only on the string literals representing the resolver arguments, e.g.,
${foo:${bar}} will always return the same value regardless of the value of
``bar`` if the cache is enabled for ``foo``.
- **annotation_validation** (<code>Literal['off', 'warn', 'error']</code>) – Runtime policy for resolver parameter and return
annotations. ``"off"`` disables validation, ``"warn"`` emits
``UserWarning`` and preserves the value, and ``"error"`` rejects
registration problems with ``TypeError``. Validation mismatches during
interpolation resolution are exposed as ``InterpolationResolutionError``.
Defaults to ``"warn"`` in OmegaConf 2.4.

### `resolve`

```python
resolve(cfg: Container) -> None
```

Resolves all interpolations in the given config object in-place.

This function works correctly for configs that use only node interpolations
(``${key}``) with no custom resolvers. When custom resolvers are involved,
results may depend on the depth-first, key insertion order traversal, because
custom resolvers can do anything — they may be stateful, have side effects, or
return different values on each call — and this function has no way to account
for that.

**Parameters:**

- **cfg** (<code>Container</code>) – An OmegaConf container.

**Raises:**

- <code>ValueError</code> – If the input object is not an OmegaConf container.

### `save`

```python
save(
    config: Any, f: str | pathlib.Path | IO[Any], resolve: bool = False
) -> None
```

Save as configuration object to a file

**Parameters:**

- **config** (<code>Any</code>) – OmegaConf container to save.
- **f** (<code>str | Path | IO[Any]</code>) – filename or file object
- **resolve** (<code>bool</code>) – True to save a resolved config (defaults to False)

### `select`

```python
select(
    cfg: Container,
    key: str,
    *,
    default: Any = _DEFAULT_MARKER_,
    throw_on_resolution_failure: bool = True,
    throw_on_missing: bool = False
) -> Any
```

Select a value from a config using a key path.

The key path uses dot notation (``"a.b.c"``) or bracket notation
(``"a[b][c]"``), or a mix of both.

**Keys containing special characters** (``.``, ``[``, ``]``, ``=``)
can be expressed by escaping them with a backslash:

- ``r"a\.b"``   — selects the key ``"a.b"`` (single key with a literal dot)
- ``r"a\[0\]"`` — selects the key ``"a[0]"``
- ``r"a\=b"``   — selects the key ``"a=b"``

A backslash before any other character passes through unchanged
(``r"a\b"`` selects the key ``"a\\b"`` — a backslash followed by ``b``).

**Parameters:**

- **cfg** (<code>Container</code>) – Config node to select from
- **key** (<code>str</code>) – Key path to select (dot/bracket notation, backslash-escapable)
- **default** (<code>Any</code>) – Default value to return if key is not found
- **throw_on_resolution_failure** (<code>bool</code>) – Raise an exception if an interpolation
resolution error occurs, otherwise return None
- **throw_on_missing** (<code>bool</code>) – Raise an exception if an attempt to select a missing key (with the value '???')
is made, otherwise return None

**Returns:**

- <code>Any</code> – selected value or None if not found.

### `set_cache`

```python
set_cache(conf: BaseContainer, cache: dict[str, Any]) -> None
```

Replace the resolver cache for ``conf`` with a deep copy of ``cache``.

**Parameters:**

- **conf** (<code>BaseContainer</code>) – An OmegaConf container.
- **cache** (<code>dict[str, Any]</code>) – New cache dict to install (will be deep-copied).

### `set_readonly`

```python
set_readonly(conf: Node, value: bool | None) -> None
```

Set the read-only flag on ``conf``.

**Parameters:**

- **conf** (<code>Node</code>) – An OmegaConf node.
- **value** (<code>bool | None</code>) – ``True`` to make read-only, ``False`` to make writable,
``None`` to inherit from the parent.

### `set_struct`

```python
set_struct(conf: Container, value: bool | None) -> None
```

Set the struct flag on ``conf``.

When struct mode is enabled, accessing or setting keys that do not exist in the
config raises an exception.

**Parameters:**

- **conf** (<code>Container</code>) – An OmegaConf container.
- **value** (<code>bool | None</code>) – ``True`` to enable struct mode, ``False`` to disable it,
``None`` to inherit from the parent.

### `structural_equality`

```python
structural_equality(cfg1: Any, cfg2: Any) -> bool
```

Compare two configs by their unresolved container structure.

Interpolations and custom resolver expressions are compared as their raw
strings and are not resolved. Missing values do not raise. An escaped
literal ``???`` is distinct from a missing value.

**Parameters:**

- **cfg1** (<code>Any</code>) – First OmegaConf config to compare.
- **cfg2** (<code>Any</code>) – Second OmegaConf config to compare.

**Returns:**

- <code>bool</code> – ``True`` if both configs have the same unresolved structure.

### `structured`

```python
structured(
    obj: Any,
    parent: BaseContainer | None = None,
    flags: dict[str, bool] | None = None,
    *,
    max_yaml_expanded_nodes: int | None = _DEFAULT_MAX_YAML_EXPANDED_NODES
) -> Any
```

Alias for ``OmegaConf.create(obj)``. Accepts any input that ``create`` accepts,
though intended for structured config objects (dataclass or attrs types/instances).

**Parameters:**

- **obj** (<code>Any</code>) – Source object — typically a dataclass or attrs type or instance,
but any value accepted by ``OmegaConf.create`` is valid.
- **parent** (<code>BaseContainer | None</code>) – Optional parent node.
- **flags** (<code>dict[str, bool] | None</code>) – Optional flags dict (e.g. ``{"readonly": True}``).
- **max_yaml_expanded_nodes** (<code>int | None</code>) – Maximum YAML nodes after alias expansion
when ``obj`` is a YAML string. By default, OmegaConf uses the
``OMEGACONF_MAX_YAML_EXPANDED_NODES`` environment variable if set,
otherwise ``10_000``. Explicit arguments override the environment.
Pass ``None`` only for trusted input. See
https://omegaconf.cli.dev/docs/reference/yaml-alias-limits/.

**Returns:**

- <code>Any</code> – A ``DictConfig``, ``ListConfig``, ``TupleConfig``, or ``None``.

### `to_container`

```python
to_container(
    cfg: Any,
    *,
    resolve: bool = False,
    throw_on_missing: bool = False,
    enum_to_str: bool = False,
    structured_config_mode: SCMode = SCMode.DICT
) -> dict[DictKeyType, Any] | list[Any] | tuple[Any, ...] | str | Any | None
```

Recursively converts an OmegaConf config to a primitive container.

**Parameters:**

- **cfg** (<code>Any</code>) – the config to convert
- **resolve** (<code>bool</code>) – True to resolve all values
- **throw_on_missing** (<code>bool</code>) – When True, raise MissingMandatoryValue if any missing values are present.
When False (the default), replace missing values with the string "???" in the output container.
- **enum_to_str** (<code>bool</code>) – True to convert Enum keys and values to strings
- **structured_config_mode** (<code>SCMode</code>) – Specify how Structured Configs (DictConfigs backed by a dataclass) are handled.
  - By default (``structured_config_mode=SCMode.DICT``) structured configs are converted to plain dicts.
  - If ``structured_config_mode=SCMode.DICT_CONFIG``, structured config nodes will remain as DictConfig.
  - If ``structured_config_mode=SCMode.INSTANTIATE``, this function will instantiate structured configs
    (DictConfigs backed by a dataclass), by creating an instance of the underlying dataclass.

See also OmegaConf.to_object.

**Returns:**

- <code>dict[DictKeyType, Any] | list[Any] | tuple[Any, ...] | str | Any | None</code> – A dict, list, or tuple representing this config as a primitive container.

### `to_object`

```python
to_object(
    cfg: Any,
) -> dict[DictKeyType, Any] | list[Any] | tuple[Any, ...] | None | str | Any
```

Recursively converts an OmegaConf config to a primitive container.
Any DictConfig objects backed by dataclasses or attrs classes are instantiated
as instances of those backing classes.

This is an alias for OmegaConf.to_container(..., resolve=True, throw_on_missing=True,
                                            structured_config_mode=SCMode.INSTANTIATE)

**Parameters:**

- **cfg** (<code>Any</code>) – the config to convert

**Returns:**

- <code>dict[DictKeyType, Any] | list[Any] | tuple[Any, ...] | None | str | Any</code> – A dict, list, tuple, or dataclass representing this config.

### `to_yaml`

```python
to_yaml(
    cfg: Any,
    *,
    resolve: bool = False,
    sort_keys: bool = False,
    default_flow_style: bool | None = False
) -> str
```

returns a yaml dump of this config object.

**Parameters:**

- **cfg** (<code>Any</code>) – Config object, Structured Config type or instance
- **resolve** (<code>bool</code>) – if True, will return a string with the interpolations resolved, otherwise
interpolations are preserved
- **sort_keys** (<code>bool</code>) – If True, will print dict keys in sorted order. default False.
- **default_flow_style** (<code>bool | None</code>) – PyYAML default_flow_style setting. default False.

**Returns:**

- <code>str</code> – A string containing the yaml representation.

### `typed_dict`

```python
typed_dict(
    content: dict[Any, Any] | None = None,
    key_type: Any = Any,
    element_type: Any = Any,
) -> DictConfig
```

Create a DictConfig with explicit key and value types.

Useful for disambiguating assignment to a dict[str, X] | dict[str, Y]
field when the value is empty or otherwise matches multiple candidates.

### `typed_list`

```python
typed_list(
    content: list[Any] | None = None, element_type: Any = Any
) -> ListConfig
```

Create a ListConfig with an explicit element type.

Useful for disambiguating assignment to a list[X] | list[Y] field
when the value is empty or otherwise matches multiple candidates.

### `typed_tuple`

```python
typed_tuple(content: Any, tuple_type: Any = Tuple[Any, ...]) -> TupleConfig
```

Create and immediately validate a TupleConfig.

``content`` is required because TupleConfig is structurally immutable.
``tuple_type`` accepts complete fixed or variadic tuple annotations, such
as ``tuple[int, str]`` or ``tuple[int, ...]``.

### `unsafe_merge`

```python
unsafe_merge(
    *configs: DictConfig
    | ListConfig
    | TupleConfig
    | dict[DictKeyType, Any]
    | list[Any]
    | tuple[Any, ...]
    | Any
) -> ListConfig | TupleConfig | DictConfig
```

Merge a list of previously created configs into a single one
This is much faster than OmegaConf.merge() as the input configs are not copied.
However, the input configs must not be used after this operation as will become inconsistent.

**Parameters:**

- **configs** (<code>DictConfig | ListConfig | TupleConfig | dict[DictKeyType, Any] | list[Any] | tuple[Any, ...] | Any</code>) – Input configs

**Returns:**

- <code>ListConfig | TupleConfig | DictConfig</code> – the merged config object.

### `update`

```python
update(
    cfg: Container,
    key: str,
    value: Any = None,
    *,
    merge: bool = True,
    force_add: bool = False
) -> None
```

Update a value in a config using a key path.

The key path uses dot notation (``"a.b.c"``) or bracket notation
(``"a[b][c]"``), or a mix of both.

**Keys containing special characters** (``.``, ``[``, ``]``, ``=``)
can be expressed by escaping them with a backslash:

- ``r"a\.b"``   — targets the key ``"a.b"`` (single key with a literal dot)
- ``r"a\[0\]"`` — targets the key ``"a[0]"``
- ``r"a\=b"``   — targets the key ``"a=b"``

**Parameters:**

- **cfg** (<code>Container</code>) – input config to update
- **key** (<code>str</code>) – key path to update (dot/bracket notation, backslash-escapable)
- **value** (<code>Any</code>) – value to set, if value if a list or a dict it will be merged or set
depending on merge_config_values
- **merge** (<code>bool</code>) – If value is a dict or a list, True (default) to merge
into the destination, False to replace the destination.
- **force_add** (<code>bool</code>) – insert the entire path regardless of Struct flag or Structured Config nodes.

## `Resolver`

```python
Resolver = Callable[..., Any]
```

## `SI`

```python
SI(interpolation: str) -> Any
```

Use this for String interpolation, for example ``"http://${host}:${port}"``

**Parameters:**

- **interpolation** (<code>str</code>) – interpolation string

**Returns:**

- <code>Any</code> – input interpolation with type ``Any``

## `flag_override`

```python
flag_override(
    config: Node,
    names: list[str] | str,
    values: list[bool | None] | bool | None,
) -> Generator[Node, None, None]
```

Context manager that temporarily overrides one or more flags on ``config``.

The original flag values are restored on exit, even if an exception is raised.

**Parameters:**

- **config** (<code>Node</code>) – An OmegaConf node whose flags will be overridden.
- **names** (<code>list[str] | str</code>) – Flag name or list of flag names (e.g. ``"readonly"``, ``"struct"``).
- **values** (<code>list[bool | None] | bool | None</code>) – New value or list of values corresponding to ``names``.

**Returns:**

- <code>Generator[Node, None, None]</code> – Yields ``config`` with the overridden flags.

## `open_dict`

```python
open_dict(config: Container) -> Generator[Container, None, None]
```

Context manager that temporarily disables struct mode on ``config``.

While active, new keys can be added freely. The original struct state is restored
on exit, even if an exception is raised.

**Parameters:**

- **config** (<code>Container</code>) – An OmegaConf container.

**Returns:**

- <code>Generator[Container, None, None]</code> – Yields ``config`` with struct mode disabled.

## `read_write`

```python
read_write(config: Node) -> Generator[Node, None, None]
```

Context manager that temporarily makes ``config`` writable.

The original read-only state is restored on exit, even if an exception is raised.

**Parameters:**

- **config** (<code>Node</code>) – An OmegaConf node.

**Returns:**

- <code>Generator[Node, None, None]</code> – Yields ``config`` in a writable state.

