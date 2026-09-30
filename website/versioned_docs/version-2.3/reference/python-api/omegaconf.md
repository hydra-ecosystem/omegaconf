---
title: OmegaConf symbols
description: OmegaConf 2.3.1 generated Python API
toc_max_heading_level: 2
---

API snapshot from OmegaConf 2.3.1 source. For task-based entry points, see the [Python API overview](../python-api).

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

### `clear_cache`

```python
clear_cache(conf: BaseContainer) -> None
```

### `clear_resolver`

```python
clear_resolver(name: str) -> bool
```

Clear(remove) any resolver only if it exists.

Returns a bool: True if resolver is removed and False if not removed.

> **Warning:** This method can remove deafult resolvers as well.

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

### `create`

```python
create(
    obj: Any = _DEFAULT_MARKER_,
    parent: Optional[BaseContainer] = None,
    flags: Optional[Dict[str, bool]] = None,
) -> Union[DictConfig, ListConfig]
```

### `from_cli`

```python
from_cli(args_list: Optional[List[str]] = None) -> DictConfig
```

### `from_dotlist`

```python
from_dotlist(dotlist: List[str]) -> DictConfig
```

Creates config from the content sys.argv or from the specified args list of not None

**Parameters:**

- **dotlist** (<code>List[str]</code>) – A list of dotlist-style strings, e.g. ``["foo.bar=1", "baz=qux"]``.

**Returns:**

- <code>DictConfig</code> – A ``DictConfig`` object created from the dotlist.

### `get_cache`

```python
get_cache(conf: BaseContainer) -> Dict[str, Any]
```

### `get_type`

```python
get_type(obj: Any, key: Optional[str] = None) -> Optional[Type[Any]]
```

### `has_resolver`

```python
has_resolver(name: str) -> bool
```

### `is_config`

```python
is_config(obj: Any) -> bool
```

### `is_dict`

```python
is_dict(obj: Any) -> bool
```

### `is_interpolation`

```python
is_interpolation(node: Any, key: Optional[Union[int, str]] = None) -> bool
```

### `is_list`

```python
is_list(obj: Any) -> bool
```

### `is_missing`

```python
is_missing(cfg: Any, key: DictKeyType) -> bool
```

### `is_readonly`

```python
is_readonly(conf: Node) -> Optional[bool]
```

### `is_struct`

```python
is_struct(conf: Container) -> Optional[bool]
```

### `legacy_register_resolver`

```python
legacy_register_resolver(name: str, resolver: Resolver) -> None
```

### `load`

```python
load(file_: Union[str, pathlib.Path, IO[Any]]) -> Union[DictConfig, ListConfig]
```

### `masked_copy`

```python
masked_copy(conf: DictConfig, keys: Union[str, List[str]]) -> DictConfig
```

Create a masked copy of of this config that contains a subset of the keys

**Parameters:**

- **conf** (<code>DictConfig</code>) – DictConfig object
- **keys** (<code>Union[str, List[str]]</code>) – keys to preserve in the copy

**Returns:**

- <code>DictConfig</code> – The masked ``DictConfig`` object.

### `merge`

```python
merge(
    *configs: Union[
        DictConfig,
        ListConfig,
        Dict[DictKeyType, Any],
        List[Any],
        Tuple[Any, ...],
        Any,
    ]
) -> Union[ListConfig, DictConfig]
```

Merge a list of previously created configs into a single one

**Parameters:**

- **configs** (<code>Union[DictConfig, ListConfig, Dict[DictKeyType, Any], List[Any], Tuple[Any, ...], Any]</code>) – Input configs

**Returns:**

- <code>Union[ListConfig, DictConfig]</code> – the merged config object.

### `missing_keys`

```python
missing_keys(cfg: Any) -> Set[str]
```

Returns a set of missing keys in a dotlist style.

**Parameters:**

- **cfg** (<code>Any</code>) – An ``OmegaConf.Container``,
or a convertible object via ``OmegaConf.create`` (dict, list, ...).

**Returns:**

- <code>Set[str]</code> – set of strings of the missing keys.

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

### `register_resolver`

```python
register_resolver(name: str, resolver: Resolver) -> None
```

### `resolve`

```python
resolve(cfg: Container) -> None
```

Resolves all interpolations in the given config object in-place.

**Parameters:**

- **cfg** (<code>Container</code>) – An OmegaConf container (DictConfig, ListConfig)
Raises a ValueError if the input object is not an OmegaConf container.

### `save`

```python
save(
    config: Any, f: Union[str, pathlib.Path, IO[Any]], resolve: bool = False
) -> None
```

Save as configuration object to a file

**Parameters:**

- **config** (<code>Any</code>) – omegaconf.Config object (DictConfig or ListConfig).
- **f** (<code>Union[str, Path, IO[Any]]</code>) – filename or file object
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



**Parameters:**

- **cfg** (<code>Container</code>) – Config node to select from
- **key** (<code>str</code>) – Key to select
- **default** (<code>Any</code>) – Default value to return if key is not found
- **throw_on_resolution_failure** (<code>bool</code>) – Raise an exception if an interpolation
resolution error occurs, otherwise return None
- **throw_on_missing** (<code>bool</code>) – Raise an exception if an attempt to select a missing key (with the value '???')
is made, otherwise return None

**Returns:**

- <code>Any</code> – selected value or None if not found.

### `set_cache`

```python
set_cache(conf: BaseContainer, cache: Dict[str, Any]) -> None
```

### `set_readonly`

```python
set_readonly(conf: Node, value: Optional[bool]) -> None
```

### `set_struct`

```python
set_struct(conf: Container, value: Optional[bool]) -> None
```

### `structured`

```python
structured(
    obj: Any,
    parent: Optional[BaseContainer] = None,
    flags: Optional[Dict[str, bool]] = None,
) -> Any
```

### `to_container`

```python
to_container(
    cfg: Any,
    *,
    resolve: bool = False,
    throw_on_missing: bool = False,
    enum_to_str: bool = False,
    structured_config_mode: SCMode = SCMode.DICT
) -> Union[Dict[DictKeyType, Any], List[Any], None, str, Any]
```

Resursively converts an OmegaConf config to a primitive container (dict or list).

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

- <code>Union[Dict[DictKeyType, Any], List[Any], None, str, Any]</code> – A dict or a list representing this config as a primitive container.

### `to_object`

```python
to_object(cfg: Any) -> Union[Dict[DictKeyType, Any], List[Any], None, str, Any]
```

Resursively converts an OmegaConf config to a primitive container (dict or list).
Any DictConfig objects backed by dataclasses or attrs classes are instantiated
as instances of those backing classes.

This is an alias for OmegaConf.to_container(..., resolve=True, throw_on_missing=True,
                                            structured_config_mode=SCMode.INSTANTIATE)

**Parameters:**

- **cfg** (<code>Any</code>) – the config to convert

**Returns:**

- <code>Union[Dict[DictKeyType, Any], List[Any], None, str, Any]</code> – A dict or a list or dataclass representing this config.

### `to_yaml`

```python
to_yaml(cfg: Any, *, resolve: bool = False, sort_keys: bool = False) -> str
```

returns a yaml dump of this config object.

**Parameters:**

- **cfg** (<code>Any</code>) – Config object, Structured Config type or instance
- **resolve** (<code>bool</code>) – if True, will return a string with the interpolations resolved, otherwise
interpolations are preserved
- **sort_keys** (<code>bool</code>) – If True, will print dict keys in sorted order. default False.

**Returns:**

- <code>str</code> – A string containing the yaml representation.

### `unsafe_merge`

```python
unsafe_merge(
    *configs: Union[
        DictConfig,
        ListConfig,
        Dict[DictKeyType, Any],
        List[Any],
        Tuple[Any, ...],
        Any,
    ]
) -> Union[ListConfig, DictConfig]
```

Merge a list of previously created configs into a single one
This is much faster than OmegaConf.merge() as the input configs are not copied.
However, the input configs must not be used after this operation as will become inconsistent.

**Parameters:**

- **configs** (<code>Union[DictConfig, ListConfig, Dict[DictKeyType, Any], List[Any], Tuple[Any, ...], Any]</code>) – Input configs

**Returns:**

- <code>Union[ListConfig, DictConfig]</code> – the merged config object.

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

Updates a dot separated key sequence to a value

**Parameters:**

- **cfg** (<code>Container</code>) – input config to update
- **key** (<code>str</code>) – key to update (can be a dot separated path)
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
    names: Union[List[str], str],
    values: Union[List[Optional[bool]], Optional[bool]],
) -> Generator[Node, None, None]
```

## `open_dict`

```python
open_dict(config: Container) -> Generator[Container, None, None]
```

## `read_write`

```python
read_write(config: Node) -> Generator[Node, None, None]
```

