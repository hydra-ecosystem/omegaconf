## 2.4.0rc1 (2026-09-28)

### Introduction

OmegaConf 2.4.0rc1 previews the first feature release since 2.3.0 in 2022. It
fixes all open bug reports, delivers a broad set of new features, and refreshes
the roadmap for work beyond this release. Highlights include richer structured
config typing with ``Literal``, container unions, and experimental tuples,
alongside improvements to interpolation, resolvers, merging, and validation.

This release includes compatibility changes. Python 3.10 or newer is required;
native tuples now become immutable ``TupleConfig`` values; and some implicit
conversions during assignment now warn. Review the API changes below and report
regressions before the final release.

### Features

- Add support for the `|` and `|=` operators on `DictConfig`. `cfg1 | cfg2` returns a new merged config (equivalent to `OmegaConf.merge(cfg1, cfg2)`), and `cfg1 |= cfg2` merges in place (equivalent to `cfg1.merge_with(cfg2)`). These operators are not supported on `ListConfig` and will raise a `TypeError`. ([#1006](https://github.com/hydra-ecosystem/omegaconf/issues/1006))
- OmegaConf.to_yaml() now accepts default_flow_style to control YAML collection flow style. ([#1075](https://github.com/hydra-ecosystem/omegaconf/issues/1075))
- Added ``OmegaConf.can_select()`` for checking if a select-style key path can produce a value without returning a default or raising. ([#1129](https://github.com/hydra-ecosystem/omegaconf/issues/1129))
- The YAML parser will now use `yaml.CSafeLoader` instead of `yaml.SafeLoader` whenever possible to speed up parsing ([#1150](https://github.com/hydra-ecosystem/omegaconf/issues/1150))
- The YAML dumper will now use `yaml.CDumper` instead of `yaml.Dumper` whenever possible to speed up dumping ([#1152](https://github.com/hydra-ecosystem/omegaconf/issues/1152))
- Added support for assigning string-valued enums in structured configs from either the enum member name or the enum value. ([#1182](https://github.com/hydra-ecosystem/omegaconf/issues/1182))
- When accessing a missing key, OmegaConf now suggests similar key names if any exist (e.g. "Did you mean: 'missing'?"). ([#1221](https://github.com/hydra-ecosystem/omegaconf/issues/1221))
- Support ``typing.Literal`` annotations in structured configs, including as members of unions. ([#1228](https://github.com/hydra-ecosystem/omegaconf/issues/1228), [#1271](https://github.com/hydra-ecosystem/omegaconf/issues/1271))
- Key paths in ``OmegaConf.update()``, ``OmegaConf.select()``, ``OmegaConf.from_dotlist()``, and ``OmegaConf.from_cli()`` now support backslash escaping so that keys whose names contain literal dots, brackets, or equals signs can be addressed (e.g. ``r"a\.b"`` selects the key ``"a.b"``). ([#1230](https://github.com/hydra-ecosystem/omegaconf/issues/1230))
- Structured configs now support unions of typed containers (e.g. ``Union[List[int], Dict[str, int]]``). ``OmegaConf.typed_list([], element_type=str)`` creates an empty list typed as ``List[str]``, selecting that branch of ``Union[List[int], List[str]]``; ``OmegaConf.typed_dict()`` similarly specifies dictionary key and value types. ([#1261](https://github.com/hydra-ecosystem/omegaconf/issues/1261))
- Support structured config types as members of unions, with type-driven branch selection and explicit handling for ambiguous mappings. ([#1275](https://github.com/hydra-ecosystem/omegaconf/issues/1275))
- Added OmegaConf.structural_equality() for comparing configs by unresolved container structure. ([#1326](https://github.com/hydra-ecosystem/omegaconf/issues/1326))
- Add the ``oc.coerce`` resolver to explicitly convert values using OmegaConf primitive node types before destination validation. ([#1332](https://github.com/hydra-ecosystem/omegaconf/issues/1332))
- Node interpolations can address keys containing literal dots, brackets, colons, or backslashes. ([#1335](https://github.com/hydra-ecosystem/omegaconf/issues/1335))
- Support ``Any`` in Union annotations and transparent PEP 695 type aliases. ([#144](https://github.com/hydra-ecosystem/omegaconf/issues/144))
- Custom resolvers can now validate runtime arguments and return values against their annotations using explicit ``"off"``, ``"warn"``, and ``"error"`` policies. OmegaConf 2.4 defaults to advisory warnings. ([#612](https://github.com/hydra-ecosystem/omegaconf/issues/612))

### Bug Fixes

- Fix merging an interpolation into a structured config field failing with InterpolationKeyError or ValidationError; the interpolation is now kept unresolved and resolved lazily against the merged result. ([#1020](https://github.com/hydra-ecosystem/omegaconf/issues/1020))
- Preserve structured list element types when merging a plain list into a missing structured config list field. ([#1058](https://github.com/hydra-ecosystem/omegaconf/issues/1058))
- Fixed a crash in `OmegaConf.unsafe_merge` when merging structured configs containing union types. ([#1087](https://github.com/hydra-ecosystem/omegaconf/issues/1087))
- Fix merging enum names into nested lists in structured configs. ([#1095](https://github.com/hydra-ecosystem/omegaconf/issues/1095))
- Fixed `OmegaConf.merge()` and `OmegaConf.unsafe_merge()` with nested readonly structured configs. ([#1102](https://github.com/hydra-ecosystem/omegaconf/issues/1102))
- Fix `OmegaConf.missing_keys()` raising when an interpolation dereferences a missing value, and add a `resolve_custom_resolvers` flag to opt into custom resolver evaluation. ([#1118](https://github.com/hydra-ecosystem/omegaconf/issues/1118))
- Improved missing-key errors for relative interpolations by showing both the original interpolation key and the resolved lookup path. ([#1126](https://github.com/hydra-ecosystem/omegaconf/issues/1126))
- Fixed `OmegaConf.select` and `oc.select` to return the provided default when a relative key climbs above the config root. ([#1127](https://github.com/hydra-ecosystem/omegaconf/issues/1127))
- ``OmegaConf.create()`` now supports ``collections.OrderedDict`` as both a top-level input and a nested value. ([#1156](https://github.com/hydra-ecosystem/omegaconf/issues/1156))
- Fixed ``OmegaConf.resolve()`` raising ``UnsupportedValueType`` when a custom resolver returns a ``dict`` or ``list``. ([#1165](https://github.com/hydra-ecosystem/omegaconf/issues/1165))
- Fixed validation for union-typed values nested in structured config containers during merges and interpolation resolution. ([#1166](https://github.com/hydra-ecosystem/omegaconf/issues/1166))
- Fixed structured config support for forward references inside container
  annotations on Python 3.10 and older. ([#1174](https://github.com/hydra-ecosystem/omegaconf/issues/1174))
- Preserve container identity when assigning a config node to itself. ([#1177](https://github.com/hydra-ecosystem/omegaconf/issues/1177))
- Fix duplicate key handling during YAML anchor merge operations ([#1194](https://github.com/hydra-ecosystem/omegaconf/issues/1194))
- Changed `OmegaConf.create(None)` to return literal `None` instead of a `DictConfig(None)` wrapper. This is a breaking change for code that relied on getting a config object back from `create(None)`. ([#1196](https://github.com/hydra-ecosystem/omegaconf/issues/1196))
- Fixed a bug where merging a missing structured config into an unresolved interpolation could replace the interpolation with the structured type's default value instead of preserving the interpolation. ([#1205](https://github.com/hydra-ecosystem/omegaconf/issues/1205))
- Fix `OmegaConf.resolve()` raising `RuntimeError` on Python 3.12+ when a custom resolver returns a `DictConfig`. ([#1239](https://github.com/hydra-ecosystem/omegaconf/issues/1239))
- ``OmegaConf.update()`` now raises a ``ConfigTypeError`` with a clear message when navigating through a structured ``Optional`` node that is ``None``, instead of an ``AssertionError``. ([#1280](https://github.com/hydra-ecosystem/omegaconf/issues/1280))
- Fix OmegaConf exceptions retaining caller frame locals through traceback reference cycles. ([#1295](https://github.com/hydra-ecosystem/omegaconf/issues/1295), [#1314](https://github.com/hydra-ecosystem/omegaconf/issues/1314))
- Fix `ListConfig` iteration leaking `UnionNode` wrappers for `List[Union[...]]`; iteration now yields the selected concrete values, matching indexing. ([#1310](https://github.com/hydra-ecosystem/omegaconf/issues/1310))
- ``OmegaConf.update()`` now follows intermediate node interpolations whose
  reference chains end at existing config containers, applying nested updates to
  the referenced container while preserving the interpolation. ([#1329](https://github.com/hydra-ecosystem/omegaconf/issues/1329))
- Keep the failing key and object type on interpolation errors raised through `OmegaConf.resolve()`, so they match the errors raised by direct node access. ([#1330](https://github.com/hydra-ecosystem/omegaconf/issues/1330))
- ``OmegaConf.resolve()`` now resolves nested interpolations in resolver-returned containers in one call, including when another field refers to the container before its field is visited. ([#1334](https://github.com/hydra-ecosystem/omegaconf/issues/1334))
- Inherited flags are now updated correctly for containers selected by a union type. ([#1340](https://github.com/hydra-ecosystem/omegaconf/issues/1340))
- Select matching Literal members before broader scalar members in unions, regardless of annotation order. ([#1357](https://github.com/hydra-ecosystem/omegaconf/issues/1357))
- ``OmegaConf.merge()`` and ``OmegaConf.unsafe_merge()`` no longer fail with an ``AttributeError`` when merging into a null dictionary root, including optional Structured Config fields. ([#1360](https://github.com/hydra-ecosystem/omegaconf/issues/1360))
- Removed the internal `flags` argument from `_ensure_container` and made merge conversion preserve `allow_objects` explicitly. ([#580](https://github.com/hydra-ecosystem/omegaconf/issues/580))
- Integer interpolation segments and integer-looking string paths used by ``OmegaConf.select()`` and ``OmegaConf.update()`` can now resolve integer dictionary keys. Configurations reject ambiguous pairs such as ``1`` and ``"1"``. ([#651](https://github.com/hydra-ecosystem/omegaconf/issues/651))
- Report the complete key path when creating a nested Structured Config fails. ([#702](https://github.com/hydra-ecosystem/omegaconf/issues/702))
- Fix structured config creation for dataclasses inheriting from `typing.Generic`. ([#731](https://github.com/hydra-ecosystem/omegaconf/issues/731))
- `ListConfig.insert()` now follows Python list semantics for negative and out-of-range indices and leaves the list unchanged when validation fails. ([#750](https://github.com/hydra-ecosystem/omegaconf/issues/750))
- Align `ListConfig` negative index behavior more closely with Python lists by supporting negative list-index interpolations and by fixing negative slicing edge cases such as `cfg.xs[:-1]` on empty lists. ([#755](https://github.com/hydra-ecosystem/omegaconf/issues/755))
- Limited YAML alias expansion by default to avoid excessive config growth from crafted YAML input, with an environment override for trusted configurations. ([#794](https://github.com/hydra-ecosystem/omegaconf/issues/794))
- Fixed `OmegaConf.masked_copy` losing typed leaf node classes at the top level of the copy. ([#813](https://github.com/hydra-ecosystem/omegaconf/issues/813))
- Fixed OmegaConf.structured() mutating existing OmegaConf nodes passed as structured config field values. ([#908](https://github.com/hydra-ecosystem/omegaconf/issues/908))
- Fix handling of `attrs` classes that use a default factory (`attrs.Factory`). ([#945](https://github.com/hydra-ecosystem/omegaconf/issues/945))
- Preserve structured child type metadata when merging a missing dict-annotated field over an existing structured config. ([#998](https://github.com/hydra-ecosystem/omegaconf/issues/998))

### API changes and deprecations

- Support for Python 3.6, 3.7, 3.8 and 3.9 has been dropped. OmegaConf now requires Python 3.10+ ([#1109](https://github.com/hydra-ecosystem/omegaconf/issues/1109))
- ``OmegaConf.resolve()`` now raises ``InterpolationToMissingValueError`` when an interpolation dereferences to a missing (``???``) value, instead of silently overwriting the node with ``???``. This restores the invariant that working with a resolved config gives the same results as working with the unresolved config. ([#1131](https://github.com/hydra-ecosystem/omegaconf/issues/1131))
- A backslash immediately before a key path delimiter (``\.`` ``\[`` ``\]`` ``\=``) now escapes that character rather than being treated as a literal backslash followed by an active delimiter. This affects only the rare case of keys whose names end with a backslash: ``OmegaConf.select(cfg, r"a\.b")`` previously navigated to key ``"a\"`` then ``"b"``; it now resolves to the single key ``"a.b"``. Keys ending in a backslash are not idiomatic in YAML and this change is unlikely to be encountered in practice. ([#1230](https://github.com/hydra-ecosystem/omegaconf/issues/1230))
- ``OmegaConf.to_container(..., resolve=True)`` now resolves each custom resolver at most once within a single conversion pass, even when multiple interpolations reference the same resolved node. This brings its behavior in line with ``OmegaConf.resolve()`` for such cases. ([#1243](https://github.com/hydra-ecosystem/omegaconf/issues/1243))
- Support escaped literal `???` values with `\???` across interpolation, resolvers, and YAML. Plain `???` returned by a resolver is now missing on access. ([#1302](https://github.com/hydra-ecosystem/omegaconf/issues/1302))
- Typed container and union interpolations now validate and convert against their destination type on lazy access, matching eager resolution. ([#1332](https://github.com/hydra-ecosystem/omegaconf/issues/1332))
- Make ``DictConfig`` and ``ListConfig`` unhashable, preventing their use as dictionary keys or set elements. ([#1333](https://github.com/hydra-ecosystem/omegaconf/issues/1333))
- Breaking change: Native tuples now create a public, structurally immutable ``TupleConfig`` instead of being converted to a mutable ``ListConfig``. Code that expects tuple input to support list mutation, checks only ``OmegaConf.is_list()``, or expects ``OmegaConf.to_container()`` to return a list for tuple input must be updated. Use ``OmegaConf.is_tuple()`` for tuple-specific behavior, ``OmegaConf.is_sequence()`` when either sequence type is accepted, or pass a list explicitly when mutation is required. Tuple annotations support fixed positional and homogeneous variadic types, complete replacement merges, typed container unions, native tuple conversion, and tuple-style sequence operations. Tuple semantics are experimental in OmegaConf 2.4 and feedback is welcome. ([#392](https://github.com/hydra-ecosystem/omegaconf/issues/392))
- Direct assignment and typed-container mutation now warn when they implicitly convert a value to another type. Use ``OmegaConf.update()`` for explicit conversion. Assigning structured-config objects or classes to structured-config fields retains its existing behavior. ([#459](https://github.com/hydra-ecosystem/omegaconf/issues/459))
- Change ``OmegaConf.get_type()`` to return ``NoneType`` for OmegaConf nodes containing ``None``, and validate ``None``/``NoneType`` annotations. ([#928](https://github.com/hydra-ecosystem/omegaconf/issues/928))
- Undeprecated ``OmegaConf.register_resolver()`` as the canonical custom resolver API, and deprecated ``OmegaConf.register_new_resolver()`` and ``OmegaConf.legacy_register_resolver()``. ([#969](https://github.com/hydra-ecosystem/omegaconf/issues/969))

### Improved Documentation

- Update documentation about merging lists examples. ([#1176](https://github.com/hydra-ecosystem/omegaconf/issues/1176))
- Add docstrings to public OmegaConf methods: ``create``, ``structured``, ``load``, ``from_cli``, ``has_resolver``, ``get_cache``, ``set_cache``, ``clear_cache``, ``copy_cache``, ``set_readonly``, ``is_readonly``, ``set_struct``, ``is_struct``, ``is_missing``, ``is_interpolation``, ``is_list``, ``is_dict``, ``is_config``, ``get_type``, ``flag_override``, ``read_write``, and ``open_dict``. ([#1222](https://github.com/hydra-ecosystem/omegaconf/issues/1222))
- Documented `OmegaConf.merge` behavior with `MISSING` values: a missing value on the source side does not overwrite a non-missing value on the target. ([#771](https://github.com/hydra-ecosystem/omegaconf/issues/771))

### Miscellaneous changes

- `antlr4` runtime is now vendored to prevent conflicts with other dependencies. ([#1091](https://github.com/hydra-ecosystem/omegaconf/issues/1091))
## 2.3.0 (2022-12-06)
### Features

- Support python3.11 ([#1023](https://github.com/omry/omegaconf/issues/1023))
- Support interpolation to keys that contain a non-leading dash character ([#880](https://github.com/omry/omegaconf/issues/880))
- OmegaConf now inspects the metadata of structured config fields and ignores fields where `metadata["omegaconf_ignore"]` is `True`. ([#984](https://github.com/omry/omegaconf/issues/984))

### Bug Fixes

- Fix an issue where merging of nested structured configs could incorrectly result in an exception ([#1003](https://github.com/omry/omegaconf/issues/1003))


## 2.2.3 (2022-08-18)
### Bug Fixes

- Revert an accidental behavior change where implicit conversion from `Path` to `str` was disallowed. ([#934](https://github.com/omry/omegaconf/issues/934))
- ListConfig sliced assignment now avoids partial updates upon error ([#950](https://github.com/omry/omegaconf/issues/950))
- Fix a bug that caused OmegaConf to crash when processing attr classes whose field annotations contained forward-references. ([#963](https://github.com/omry/omegaconf/issues/963))
- Improve error message when certain illegal type annotations (such as `typing.Sequence`) are used in structured configs. ([#991](https://github.com/omry/omegaconf/issues/991))
- When parsing yaml: Disallow numbers with trailing underscore from being converted to float. ([#838](https://github.com/omry/omegaconf/issues/838))

### API changes and deprecations

- In structured config type hints, OmegaConf now treats `tuple` as equivalent to `typing.Tuple`, and likewise for `dict`/`Dict` and `list`/`List`. ([#973](https://github.com/omry/omegaconf/issues/973))


## 2.2.2 (2022-05-26)
### Bug Fixes

- Revert an accidental behavior change where implicit conversion from `Path` to `str` was disallowed. ([#934](https://github.com/omry/omegaconf/issues/934))
- Revert a behavior change where namedtuples and list subclasses were coerced to ListConfig. ([#939](https://github.com/omry/omegaconf/issues/939))
- Fix a bug where the `oc.dict.values` resolver failed when passed a relative dotpath ([#942](https://github.com/omry/omegaconf/issues/942))


## 2.2.1 (2022-05-17)
OmegaConf 2.2 is a major release. The most significant area of improvement in
2.2 is support for more flexible type hints in structured configs. In addition,
OmegaConf now natively supports two new primitive types, `bytes` and `pathlib.Path`.

### Features

- Support unions of primitive types in structured config type hints (`typing.Union`) ([#144](https://github.com/omry/omegaconf/issues/144))
- Support nested container type hints in structured configs, e.g. dict-of-dict and list-of-list ([#427](https://github.com/omry/omegaconf/issues/427))
- Improve support for optional element types in structured config container type hints (`typing.Optional`) ([#460](https://github.com/omry/omegaconf/issues/460))
- Add support for `bytes`-typed values ([#844](https://github.com/omry/omegaconf/issues/844))
- Add support for `pathlib.Path`-typed values ([#97](https://github.com/omry/omegaconf/issues/97))
- `ListConfig` now implements slice assignment ([#736](https://github.com/omry/omegaconf/issues/736))
- Enable adding a `ListConfig` to a `list` via the `ListConfig.__radd__` dunder method ([#849](https://github.com/omry/omegaconf/issues/849))
- Add `OmegaConf.missing_keys()`, a method that returns the missing keys in a config object ([#720](https://github.com/omry/omegaconf/issues/720))
- Add `OmegaConf.clear_resolver()`, a method to remove interpolation resolvers by name ([#769](https://github.com/omry/omegaconf/issues/769))
- Enable the use of a pipe symbol `|` in unquoted strings in OmegaConf interpolations ([#799](https://github.com/omry/omegaconf/issues/799))

### Bug Fixes

- `OmegaConf.to_object` now works properly with structured configs that have `init=False` fields ([#789](https://github.com/omry/omegaconf/issues/789))
- Fix bugs related to creation of structured configs from dataclasses having fields with a default_factory ([#831](https://github.com/omry/omegaconf/issues/831))
- Fix default value initialization for structured configs created from subclasses of dataclasses ([#817](https://github.com/omry/omegaconf/issues/817))

### API changes and deprecations

- Removed support for `OmegaConf.is_none(cfg, "key")`.  Please use `cfg.key is None` instead. ([#547](https://github.com/omry/omegaconf/issues/547))
- Removed support for `${env}` interpolations.  `${oc.env}` should be used instead. ([#573](https://github.com/omry/omegaconf/issues/573))
- Removed `OmegaConf.get_resolver()`.  Please use `OmegaConf.has_resolver()` instead. ([#608](https://github.com/omry/omegaconf/issues/608))
- Removed support for `OmegaConf.is_optional()`. ([#698](https://github.com/omry/omegaconf/issues/698))
- Improved error message when assigning an invalid value to int or float config nodes ([#743](https://github.com/omry/omegaconf/issues/743))
- To conform with the `MutableMapping` API, the `DictConfig.items` method now returns an object of type `ItemsView`, and `DictConfig.keys` will now always return a `KeysView` ([#848](https://github.com/omry/omegaconf/issues/848))


## 2.1.1 (2021-08-17)
### Features

- Add a throw_on_missing keyword argument to the signature of OmegaConf.to_container, which controls whether MissingMandatoryValue exceptions are raised. ([#501](https://github.com/omry/omegaconf/issues/501))

### Miscellaneous changes

- Update pyyaml dependency specification for compatibility with PEP440 ([#758](https://github.com/omry/omegaconf/issues/758))
- Fix a packaging issue (missing sdist dependency) ([#772](https://github.com/omry/omegaconf/issues/772))


## 2.1.0 (2021-06-07)


### Bug Fixes

- `ListConfig.append()` now copies input config nodes ([#601](https://github.com/omry/omegaconf/issues/601))
- Fix loading of OmegaConf 2.0 pickled configs ([#718](https://github.com/omry/omegaconf/issues/718))


## 2.1.0.rc1 (2021-05-12)
OmegaConf 2.1 is a major release introducing substantial new features, and introducing some incompatible changes.
The biggest area of improvement in 2.1 is interpolations and resolvers. In addition - OmegaConf containers are now
much more compatible with their plain Python container counterparts (dict and list).

### Features
#### API Enhancements
- OmegaConf.select() now takes an optional default value to return if a key is not found ([#228](https://github.com/omry/omegaconf/issues/228))
- flag_override can now override multiple flags at the same time ([#400](https://github.com/omry/omegaconf/issues/400))
- Add the OmegaConf.to_object method, which converts Structured Configs to native instances of the underlying `@dataclass` or `@attr.s` class. ([#472](https://github.com/omry/omegaconf/issues/472))
- Add OmegaConf.unsafe_merge(), a fast merge variant that destroys the input configs ([#482](https://github.com/omry/omegaconf/issues/482))
- New function `OmegaConf.has_resolver()` allows checking whether a resolver has already been registered. ([#608](https://github.com/omry/omegaconf/issues/608))
- Adds OmegaConf.resolve(cfg) for in-place interpolation resolution on cfg ([#640](https://github.com/omry/omegaconf/issues/640))
- force_add flag added to OmegaConf.update(), ensuring that the path is created even if it will result in insertion of new values into struct nodes. ([#664](https://github.com/omry/omegaconf/issues/664))
- Add DictConfig support for keys of type int, float and bool ([#149](https://github.com/omry/omegaconf/issues/149)), ([#483](https://github.com/omry/omegaconf/issues/483))
- Structured Configs fields without a value are now automatically treated as `OmegaConf.MISSING` ([#390](https://github.com/omry/omegaconf/issues/390))
- Add minimal support for typing.TypedDict ([#473](https://github.com/omry/omegaconf/issues/473))
- OmegaConf.to_container now takes a `structured_config_mode` keyword argument. Setting `structured_config_mode=SCMode.DICT_CONFIG` causes `to_container` to not convert Structured Config objects to python dicts (it leaves them as DictConfig objects). ([#548](https://github.com/omry/omegaconf/issues/548))
#### Interpolation and resolvers
- Support for relative interpolation ([#48](https://github.com/omry/omegaconf/issues/48))
- Add ability to nest interpolations, e.g. ${foo.${bar}}}, ${oc.env:{$var1},${var2}}, or ${${func}:x1,x2} ([#445](https://github.com/omry/omegaconf/issues/445))
- Custom resolvers can now access the parent and the root config nodes ([#266](https://github.com/omry/omegaconf/issues/266))
- For `OmegaConf.{update, select}` and in interpolations, bracketed keys may be used as an alternative form to dot notation,
  e.g. foo.1 is equivalent to foo[1], [foo].1 and [foo][1]. ([#179](https://github.com/omry/omegaconf/issues/179))
- Custom resolvers may take non string arguments as input, and control whether to use the cache. ([#445](https://github.com/omry/omegaconf/issues/445))
- Dots may now be used in resolver names to denote namespaces (e.g: `${namespace.my_func:123}`) ([#539](https://github.com/omry/omegaconf/issues/539))
- New resolver `oc.select`, enabling node selection with a default value to use if the node cannot be selected ([#541](https://github.com/omry/omegaconf/issues/541))
- New resolver `oc.decode` that can be used to automatically convert a string to bool, int, float, dict, list, etc. ([#574](https://github.com/omry/omegaconf/issues/574))
- New resolvers `oc.dict.keys` and `oc.dict.values` provide a list view of the keys or values of a DictConfig node. ([#643](https://github.com/omry/omegaconf/issues/643))
- New resolver `oc.create` can be used to dynamically generate config nodes ([#645](https://github.com/omry/omegaconf/issues/645))
- New resolver `oc.deprecated`, that enables deprecating config nodes ([#681](https://github.com/omry/omegaconf/issues/681))
- The dollar character `$` is now allowed in interpolated key names, e.g. `${$var}` ([#600](https://github.com/omry/omegaconf/issues/600))
#### Misc
- New PyDev.Debugger resolver plugin for easier debugging in PyCharm and VSCode ([#214](https://github.com/omry/omegaconf/issues/214))
- OmegaConf now supports Python 3.9 ([#447](https://github.com/omry/omegaconf/issues/447))
- Support for Python 3.10 postponed annotation evaluation ([#303](https://github.com/omry/omegaconf/issues/303))
- Experimental support for enabling objects in config via "allow_objects" flag ([#382](https://github.com/omry/omegaconf/issues/382))

### Bug Fixes

- Fix support for forward declarations in Dict and Lists ([#378](https://github.com/omry/omegaconf/issues/378))
- Fix bug that allowed instances of Structured Configs to be assigned to DictConfig with different element type. ([#386](https://github.com/omry/omegaconf/issues/386))
- Fix exception raised when checking for the existence of a key with an incompatible type in DictConfig ([#394](https://github.com/omry/omegaconf/issues/394))
- Fix loading of an empty file via a file-pointer to return an empty dictionary ([#403](https://github.com/omry/omegaconf/issues/403))
- Fix pickling of Structured Configs with fields annotated as Dict[KT, VT] or List[T] on Python 3.6. ([#407](https://github.com/omry/omegaconf/issues/407))
- Assigning a primitive type to a Subscripted Dict now raises a descriptive message. ([#409](https://github.com/omry/omegaconf/issues/409))
- Fix assignment of an invalid value to a DictConfig to raise an exception without modifying the config object ([#409](https://github.com/omry/omegaconf/issues/409))
- Assigning a Structured Config to a Dict annotation now raises a descriptive error message. ([#410](https://github.com/omry/omegaconf/issues/410))
- OmegaConf.to_container() raises a ValueError on invalid input ([#418](https://github.com/omry/omegaconf/issues/418))
- Fix ConfigKeyError in some cases when merging lists containing interpolation values ([#422](https://github.com/omry/omegaconf/issues/442))
- DictConfig.get() in struct mode return None like standard Dict for non-existing keys ([#425](https://github.com/omry/omegaconf/issues/425))
- Fix bug where interpolations were unnecessarily resolved during merge ([#431](https://github.com/omry/omegaconf/issues/431))
- Fix bug where assignment of an invalid value to a ListConfig raised an exception but left the object modified. ([#433](https://github.com/omry/omegaconf/issues/433))
- When initializing a Structured Config with an incorrectly-typed value, the resulting ValidationError now properly reports the offending value in its error message. ([#435](https://github.com/omry/omegaconf/issues/435))
- Fix assignment of a Container to itself causing it to clear its content ([#449](https://github.com/omry/omegaconf/issues/449))
- Fix bug where DictConfig's shallow copy didn't work properly in some cases. ([#450](https://github.com/omry/omegaconf/issues/450))
- Fix support for merge tags in YAML files ([#470](https://github.com/omry/omegaconf/issues/470))
- Fix merge into a custom resolver node that raises an exception ([#486](https://github.com/omry/omegaconf/issues/486))
- Fix merge when element type is a Structured Config ([#496](https://github.com/omry/omegaconf/issues/496))
- Fix ValidationError when setting to None an optional field currently interpolated to a non-optional one ([#524](https://github.com/omry/omegaconf/issues/524))
- Fix OmegaConf.to_yaml(cfg) when keys are of Enum type ([#531](https://github.com/omry/omegaconf/issues/531))
- When a DictConfig has enum-typed keys, `__delitem__` can now be called with a string naming the enum member to be deleted. ([#554](https://github.com/omry/omegaconf/issues/554))
- `OmegaConf.select()` of a missing (`???`) node from a ListConfig with `throw_on_missing` set to True now raises the intended exception. ([#563](https://github.com/omry/omegaconf/issues/563))
- `DictConfig.{get(),pop()}` now return `None` when the accessed key evaluates to `None`, instead of the specified default value (for consistency with regular Python dictionaries). ([#583](https://github.com/omry/omegaconf/issues/583))
- `ListConfig.get()` now return `None` when the accessed key evaluates to `None`, instead of the specified default value (for consistency with DictConfig). ([#583](https://github.com/omry/omegaconf/issues/583))
- Fix creation of structured config from a dict subclass: data from the dict is no longer thrown away. ([#584](https://github.com/omry/omegaconf/issues/584))
- Assignment of a dict/list to an existing node in a parent in struct mode no longer raises ValidationError ([#586](https://github.com/omry/omegaconf/issues/586))
- Nested flag_override now properly restore the original state ([#589](https://github.com/omry/omegaconf/issues/589))
- Fix OmegaConf.create() to set the provided `parent` when creating a config from a YAML string. ([#648](https://github.com/omry/omegaconf/issues/648))
- OmegaConf.select now returns None when attempting to select a child of a value or None node ([#678](https://github.com/omry/omegaconf/issues/678))
- Improve error message when creating a config from a Structured Config that fails type validation ([#697](https://github.com/omry/omegaconf/issues/697))

### API changes and deprecations

- DictConfig `__getattr__` access, e.g. `cfg.foo`, is now raising a AttributeError if the key "foo" does not exist ([#515](https://github.com/omry/omegaconf/issues/515))
- DictConfig `__getitem__` access, e.g. `cfg["foo"]`, is now raising a KeyError if the key "foo" does not exist ([#515](https://github.com/omry/omegaconf/issues/515))
- DictConfig get access, e.g. `cfg.get("foo")`, now returns `None` if the key "foo" does not exist ([#527](https://github.com/omry/omegaconf/issues/527))
- `Omegaconf.select(cfg, key, default, throw_on_missing)` now requires keyword arguments for everything after `key` ([#228](https://github.com/omry/omegaconf/issues/228))
- Structured Configs with nested Structured config field that does not specify a default value are now interpreted as MISSING (`???`) instead of auto-expanding ([#411](https://github.com/omry/omegaconf/issues/411))
- OmegaConf.update() is now merging dict/list values into the destination node by default. Call with merge=False to replace instead. ([#667](https://github.com/omry/omegaconf/issues/667))
- `register_resolver()` is deprecated in favor of `register_new_resolver()`, allowing resolvers to (i) take non-string arguments like int, float, dict, interpolations, etc. and (ii) control the cache behavior (now disabled by default) ([#426](https://github.com/omry/omegaconf/issues/426))
- Merging a MISSING value onto an existing value no longer changes the target value to MISSING. ([#462](https://github.com/omry/omegaconf/issues/462))
- When resolving an interpolation of a config value with a primitive type, the interpolated value is validated and possibly converted based on the node's type. ([#488](https://github.com/omry/omegaconf/issues/488))
- DictConfig and ListConfig shallow copy is now performing a deepcopy ([#492](https://github.com/omry/omegaconf/issues/492))
- `OmegaConf.select()`, `DictConfig.{get(),pop()}`, `ListConfig.{get(),pop()}` no longer return the specified default value when the accessed key is an interpolation that cannot be resolved: instead, an exception is raised. ([#543](https://github.com/omry/omegaconf/issues/543))
- OmegaConf.{merge, unsafe_merge, to_yaml} now raises a ValueError when called on a str input. Previously an AssertionError was raised. ([#560](https://github.com/omry/omegaconf/issues/560))
- All exceptions raised during the resolution of an interpolation are either `InterpolationResolutionError` or a subclass of it. ([#561](https://github.com/omry/omegaconf/issues/561))
- `key in cfg` now returns True when `key` is an interpolation even if the interpolation target is a missing ("???") value. ([#562](https://github.com/omry/omegaconf/issues/562))
- `OmegaConf.select()` as well as container methods `get()` and `pop()` do not return their default value anymore when the accessed key is an interpolation that cannot be resolved: instead, an exception is raised. ([#565](https://github.com/omry/omegaconf/issues/565))
- Implicitly empty resolver arguments (e.g., `${foo:a,}`) are deprecated in favor of explicit quoted strings (e.g., `${foo:a,""}`) ([#572](https://github.com/omry/omegaconf/issues/572))
- The `env` resolver is deprecated in favor of `oc.env`, which keeps the string representation of environment variables, does not cache the resulting value, and handles "null" as default value. ([#573](https://github.com/omry/omegaconf/issues/573))
- `OmegaConf.get_resolver()` is deprecated: use the new `OmegaConf.has_resolver()` to check for the existence of a resolver. ([#608](https://github.com/omry/omegaconf/issues/608))
- Interpolation cycles are now forbidden and will trigger an InterpolationResolutionError on access. ([#662](https://github.com/omry/omegaconf/issues/662))
- Support for Structured Configs that subclass `typing.Dict` is now deprecated. ([#663](https://github.com/omry/omegaconf/issues/663))
- Remove BaseContainer.{pretty,select,update_node} that have been deprecated since OmegaConf 2.0. ([#671](https://github.com/omry/omegaconf/issues/671))

### Miscellaneous changes

- Optimized config creation time. Faster by 1.25x to 4x in benchmarks ([#477](https://github.com/omry/omegaconf/issues/477))
- ListConfig.__contains__ optimized, about 15x faster in a benchmark ([#529](https://github.com/omry/omegaconf/issues/529))
- Optimized ListConfig iteration by 12x in a benchmark ([#532](https://github.com/omry/omegaconf/issues/532))


## 2.0.6 (2021-01-19)
### Bug Fixes

- Fix bug where DictConfig's shallow copy didn't work properly in some cases. ([#450](https://github.com/omry/omegaconf/issues/450))

## 2.0.5 (2020-11-11)
### Bug Fixes

- Fix bug where interpolations were unnecessarily resolved during merge ([#431](https://github.com/omry/omegaconf/issues/431))

## 2.0.4 (2020-11-03)
### Bug Fixes

- Fix a bug merging into a field annotated as Optional[List[int]] = None ([#428](https://github.com/omry/omegaconf/issues/428))


## 2.0.3 (2020-10-19)
### Deprecations and Removals

- Automatic expansion of nested dataclasses without a default value is deprecated ([#412](https://github.com/omry/omegaconf/issues/412))


## 2.0.2 (2020-09-10)
### Features

- OmegaConf.update() now takes a merge flag to indicate merge or set for config values ([#363](https://github.com/omry/omegaconf/issues/363))

### Bug Fixes

- Fix cfg.pretty() deprecation warning ([#358](https://github.com/omry/omegaconf/issues/358))
- Properly crash when accessing `${foo.bar}` if `foo` is a value node (instead of silently returning `${foo}`) ([#364](https://github.com/omry/omegaconf/issues/364))

### Deprecations and Removals

- OmegaConf.update() now warns if the merge flag is not specified ([#367](https://github.com/omry/omegaconf/issues/367))


## 2.0.1 (2020-09-01)
This is mostly a bugfix release.
The notable change is the config.pretty() is now deprecated in favor of OmegaConf.to_yaml().

### Bug Fixes

- Fixes merging of dict into a Dict[str, str] ([#246](https://github.com/omry/omegaconf/issues/246))
- Fix DictConfig created from another DictConfig drops node types ([#252](https://github.com/omry/omegaconf/issues/252))
- Relax save and load APIs to accept IO[Any] ([#253](https://github.com/omry/omegaconf/issues/253))
- Report errors when loading YAML files with duplicate keys ([#257](https://github.com/omry/omegaconf/issues/257))
- Fix a bug initializing config with field typed as Any with Structured Config object ([#260](https://github.com/omry/omegaconf/issues/260))
- Merging into a MISSING Structured config node expands the node first to ensure the result is legal ([#269](https://github.com/omry/omegaconf/issues/269))
- Fix merging into a config with a read only node if merge is not mutating that node ([#271](https://github.com/omry/omegaconf/issues/271))
- Fix OmegaConf.to_container() failing in some cases when the config is read-only ([#275](https://github.com/omry/omegaconf/issues/275))
- Optional[Tuple] types are now supported as type annotation in Structured Configs. ([#279](https://github.com/omry/omegaconf/issues/279))
- Support indirect interpolation ([#283](https://github.com/omry/omegaconf/issues/283))
- OmegaConf.save() can now save dataclass and attr classes and instances ([#287](https://github.com/omry/omegaconf/issues/287))
- OmegaConf.create() doesn't modify yaml.loader.SafeLoader ([#289](https://github.com/omry/omegaconf/issues/289))
- Fix merging a sublcass Structured Config that adds a field ([#291](https://github.com/omry/omegaconf/issues/291))
- strings containing valid ints and floats represented are converted to quoted strings instead of the primitives in pretty() ([#296](https://github.com/omry/omegaconf/issues/296))
- Loading an empty YAML file now returns an empty DictConfig ([#297](https://github.com/omry/omegaconf/issues/297))
- Fix bug that allowed an annotated List and Dict field in a Structured Config to be assigned a value of a different type. ([#300](https://github.com/omry/omegaconf/issues/300))
- merge_with() now copied flags (readonly, struct) into target config ([#301](https://github.com/omry/omegaconf/issues/301))
- Fix DictConfig setdefault method to behave as it should ([#304](https://github.com/omry/omegaconf/issues/304))
- Merging a missing list onto an existing one makes the target missing ([#306](https://github.com/omry/omegaconf/issues/306))
- Fix error when merging a structured config into a field with None value ([#310](https://github.com/omry/omegaconf/issues/310))
- Fix a bug that allowed the assignment of containers onto fields annotated as primitive types ([#324](https://github.com/omry/omegaconf/issues/324))
- Merging a List of a structured with a different type now raises an error. ([#327](https://github.com/omry/omegaconf/issues/327))
- Remove dot-keys usage warning ([#332](https://github.com/omry/omegaconf/issues/332))
- Fix merging into an Optional[List[Any]] = None ([#336](https://github.com/omry/omegaconf/issues/336))
- Fix to properly merge list of dicts into a list of dataclasses ([#348](https://github.com/omry/omegaconf/issues/348))
- OmegaConf.to_yaml() now properly support Structured Configs ([#350](https://github.com/omry/omegaconf/issues/350))

### Deprecations and Removals

- cfg.pretty() is deprecated in favor of OmegaConf.to_yaml(config). ([#263](https://github.com/omry/omegaconf/issues/263))

### Improved Documentation

- Document serialization APIs ([#278](https://github.com/omry/omegaconf/issues/278))
- Document OmegaConf.is_interpolation and OmegaConf.is_none ([#286](https://github.com/omry/omegaconf/issues/286))
- Document OmegaConf.get_type() ([#343](https://github.com/omry/omegaconf/issues/343))


## 2.0.0 (2020-05-04)

OmegaConf 2.0 is a major release introducing substantial new features, and introducing some incompatible changes.
The biggest new feature is Structured Configs, which extends OmegaConf into a schema validation system
as well as a configuration system.
With Structured Configs you can create OmegaConf objects from standard dataclasses or attr classes (or objects).
OmegaConf will retain the type information from the source object/class and validate that config mutations are legal.

This is the biggest OmegaConf release ever, the number of unit tests more than tripled (485 to 1571).

### Features

- Add support for initializing OmegaConf from typed objects and classes ([#87](https://github.com/omry/omegaconf/issues/87))
- DictConfig and ListConfig now implements typing.MutableMapping and typing.MutableSequence. ([#114](https://github.com/omry/omegaconf/issues/114))
- Enums can now be used as values and keys  ([#87](https://github.com/omry/omegaconf/issues/87)),([#137](https://github.com/omry/omegaconf/issues/137))
- Standardize exception messages ([#186](https://github.com/omry/omegaconf/issues/186))
- In struct mode, exceptions raised on invalid access are now consistent with Python ([#138](https://github.com/omry/omegaconf/issues/138)),([#94](https://github.com/omry/omegaconf/issues/94))
    * KeyError is raised when using dictionary access style for a missing key: cfg["foo"]
    * AttributeError is raised when using attribute access style for a missing attribute: cfg.foo
- Structured configs can now inherit from Dict, making them open to arbitrary fields ([#134](https://github.com/omry/omegaconf/issues/134))
- Container.pretty() now preserves insertion order by default. override with sort_keys=True ([#161](https://github.com/omry/omegaconf/issues/161))
- Merge into node interpolation is now by value (copying target node) ([#184](https://github.com/omry/omegaconf/issues/184))
- Add OmegaConf.{is_config, is_list, is_dict} to test if an Object is an OmegaConf object, and if it's a list or a dict ([#101](https://github.com/omry/omegaconf/issues/101))
- Add OmegaConf.is_missing(cfg, key) to test if a key is missing ('???') in a config ([#102](https://github.com/omry/omegaconf/issues/102))
- OmegaConf.is_interpolation queries if a node is an interpolation ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf.is_missing queries if a node is missing (has the value '???') ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf.is_optional queries if a node in the config is optional (can take None) ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf.is_none queries if a node represents None ([#239](https://github.com/omry/omegaconf/issues/239))
- OmegaConf now passes strict mypy tests ([#105](https://github.com/omry/omegaconf/issues/105))
- Add isort to ensure imports are kept sorted ([#107](https://github.com/omry/omegaconf/issues/107))

### Bug Fixes

- Disable automatic conversion of date strings in yaml decoding ([#95](https://github.com/omry/omegaconf/issues/95))
- Fixed pretty to handle strings with unicode characters correctly ([#111](https://github.com/omry/omegaconf/issues/111))
- Fix eq fails if object contains unresolveable values ([#124](https://github.com/omry/omegaconf/issues/124))
- Correctly throw MissingMandatoryValue on indirect access of missing value ([#99](https://github.com/omry/omegaconf/issues/99))
- DictConfig pop now returns the underlying value and not ValueNode ([#127](https://github.com/omry/omegaconf/issues/127))
- OmegaConf.select(key) now returns the root node when key is "" ([#135](https://github.com/omry/omegaconf/issues/135))
- Add support for loading/saving config files by using pathlib.Path objects ([#159](https://github.com/omry/omegaconf/issues/159))
- Fix AttributeError when accessing config in struct-mode with get() while providing None as default ([#174](https://github.com/omry/omegaconf/issues/174))


### Deprecations and Removals

- Renamed omegaconf.Config to omegaconf.Container ([#103](https://github.com/omry/omegaconf/issues/103))
- Dropped support Python 2.7 and 3.5 ([#88](https://github.com/omry/omegaconf/issues/88))
- cfg.select(key) deprecated in favor of OmegaConf.select(cfg, key) ([#116](https://github.com/omry/omegaconf/issues/116))
- cfg.update(key, value) deprecated in favor of OmegaConf.update(cfg, key, value) ([#116](https://github.com/omry/omegaconf/issues/116))
- Container.pretty() behavior change: sorted keys -> unsorted keys by default. override with sort_keys=True. ([#161](https://github.com/omry/omegaconf/issues/161))
- cfg.to_container() is removed, deprecated since 1.4.0. Use OmegaConf.to_container() ([#188](https://github.com/omry/omegaconf/issues/188))
- cfg.save() is removed, deprecated since 1.4.0, use OmegaConf.save() ([#188](https://github.com/omry/omegaconf/issues/188))
- DictConfig item deletion now throws ConfigTypeError if the config is in struct mode ([#225](https://github.com/omry/omegaconf/issues/225))
- DictConfig.pop() now throws ConfigTypeError if the config is in struct mode ([#225](https://github.com/omry/omegaconf/issues/225))


## 1.4.0 (2019-11-19)

### Features

- ListConfig now implements + operator (Allowing concatenation with other ListConfigs) ([#36](https://github.com/omry/omegaconf/issues/36))
- OmegaConf.save() now takes a resolve flag (defaults False) ([#37](https://github.com/omry/omegaconf/issues/37))
- Add OmegaConf.masked_copy(keys) function that returns a copy of a config with a subset of the keys ([#42](https://github.com/omry/omegaconf/issues/42))
- Improve built-in env resolver to return properly typed values ("1" -> int, "1.0" -> float etc) ([#44](https://github.com/omry/omegaconf/issues/44))
- Resolvers can now accept a list of zero or more arguments, for example: "${foo:a,b,..,n}" ([#46](https://github.com/omry/omegaconf/issues/46))
- Change semantics of contains check ('x' in conf): Missing mandatory values ('???') are now considered not included and contains test returns false for them ([#49](https://github.com/omry/omegaconf/issues/49))
- Allow assignment of a tuple value into a Config ([#74](https://github.com/omry/omegaconf/issues/74))

### Bug Fixes

- Read-only list can no longer be replaced with command line override ([#39](https://github.com/omry/omegaconf/issues/39))
- Fix an error when expanding an empty dictionary in PyCharm debugger ([#40](https://github.com/omry/omegaconf/issues/40))
- Fix a bug in open_dict causing improper restoration of struct flag in some cases ([#47](https://github.com/omry/omegaconf/issues/47))
- Fix a bug preventing dotlist values from containing '=' (foo=bar=10 -> key: foo, value: bar=10) ([#56](https://github.com/omry/omegaconf/issues/56))
- Config.merge_with_dotlist() now throws if input is not a list or tuple of strings ([#72](https://github.com/omry/omegaconf/issues/72))
- Add copy method for DictConfig and improve shallow copy support ([#82](https://github.com/omry/omegaconf/issues/82))

### Deprecations and Removals

- Deprecated Config.to_container() in favor of OmegaConf.to_container() (#[#41](https://github.com/omry/omegaconf/issues/41))
- Deprecated config.save(file) in favor of OmegaConf.save(config, file) ([#66](https://github.com/omry/omegaconf/issues/66))
- Remove OmegaConf.{empty(), from_string(), from_dict(), from_list()}. Use OmegaConf.create() (deprecated since 1.1.5) ([#67](https://github.com/omry/omegaconf/issues/67))
- Remove Config.merge_from(). Use Config.merge_with() (deprecated since 1.1.0) ([#67](https://github.com/omry/omegaconf/issues/67))
- Remove OmegaConf.from_filename() and OmegaConf.from_file(). Use OmegaConf.load() (deprecated since 1.1.5) ([#67](https://github.com/omry/omegaconf/issues/67))

### Miscellaneous changes

- Switch from tox to nox for test automation ([#54](https://github.com/omry/omegaconf/issues/54))
- Formatting code with Black ([#54](https://github.com/omry/omegaconf/issues/54))
- Switch from Travis to CircleCI for CI ([#54](https://github.com/omry/omegaconf/issues/54))
