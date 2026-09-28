from contextvars import ContextVar
from typing import Any

from omegaconf import Container, DictConfig, ListConfig, Node, TupleConfig, ValueNode
from omegaconf.errors import (
    ConfigKeyError,
    ConfigTypeError,
    InterpolationResolutionError,
    InterpolationToMissingValueError,
)
from omegaconf.nodes import InterpolationResultNode

from ._utils import (
    _DEFAULT_MARKER_,
    _convert_opaque_missing,
    _ensure_container,
    _get_value,
    _is_missing_literal,
    is_primitive_container,
    is_structured_config,
)

_eager_resolution: ContextVar[bool] = ContextVar("eager_resolution", default=False)


def _is_recursive_container(
    value: Any,
    ancestors: set[int] | None = None,
    verified: set[int] | None = None,
) -> bool:
    if not is_primitive_container(value):
        return False
    if ancestors is None:
        ancestors = set()
    if verified is None:
        verified = set()
    value_id = id(value)
    if value_id in ancestors:
        return True
    if value_id in verified:
        return False
    ancestors.add(value_id)
    try:
        if isinstance(value, (list, tuple)):
            recursive = any(
                _is_recursive_container(item, ancestors, verified) for item in value
            )
        else:
            recursive = any(
                _is_recursive_container(item, ancestors, verified)
                for item in value.values()
            )
    finally:
        ancestors.remove(value_id)
    if not recursive:
        verified.add(value_id)
    return recursive


def _resolve_container_value(cfg: Container, key: Any) -> None:
    node = cfg._get_child(key)
    assert isinstance(node, Node)
    if node._is_interpolation():
        try:
            resolved = node._dereference_node()
        except Exception as e:
            # Attach the same key/object_type context that direct node access
            # reports, so errors surfaced through OmegaConf.resolve() stay
            # diagnosable.
            cfg._format_and_raise(key=key, value=None, cause=e)
        if isinstance(resolved, Container):
            _resolve(resolved)
        if isinstance(resolved, InterpolationResultNode):
            resolved_value = _get_value(resolved)
            if is_primitive_container(resolved_value) or is_structured_config(
                resolved_value
            ):
                producer = resolved._get_parent_container()
                assert producer is not None
                producer_key = resolved._key()
                resolved = _materialize_resolver_container(
                    producer, producer_key, resolved_value
                )
                if producer is cfg and producer_key == key:
                    return
        if isinstance(cfg, TupleConfig) and _is_missing_literal(_get_value(resolved)):
            cfg._format_and_raise(
                key=key,
                value=_get_value(resolved),
                cause=InterpolationToMissingValueError(
                    "TupleConfig interpolation resolved to a missing value"
                ),
            )
        if isinstance(resolved, Container) and isinstance(node, ValueNode):
            if isinstance(cfg, TupleConfig):
                cfg._set_item_for_resolution(key, resolved)
            else:
                cfg[key] = resolved
        else:
            node._set_value(_get_value(resolved))
    else:
        _resolve(node)


def _materialize_resolver_container(cfg: Container, key: Any, value: Any) -> Container:
    if _is_recursive_container(value):
        cfg._format_and_raise(
            key=key,
            value=value,
            cause=InterpolationResolutionError(
                "Cannot materialize a recursive resolver result"
            ),
        )
    resolved = _ensure_container(_convert_opaque_missing(value, encode=True))
    if isinstance(cfg, TupleConfig):
        cfg._set_item_for_resolution(key, resolved)
    else:
        cfg[key] = resolved
    stored = cfg._get_child(key)
    assert isinstance(stored, Container)
    _resolve(stored)
    return stored


def _resolve(cfg: Node) -> Node:
    assert isinstance(cfg, Node)
    if cfg._is_interpolation():
        resolved = cfg._dereference_node()
        resolved_value = resolved._value()
        if isinstance(resolved, InterpolationResultNode) and is_primitive_container(
            resolved_value
        ):
            if _is_recursive_container(resolved_value):
                raise InterpolationResolutionError(
                    "Cannot materialize a recursive resolver result"
                )
            resolved_value = _convert_opaque_missing(resolved_value, encode=True)
        cfg._set_value(resolved_value)

    if isinstance(cfg, DictConfig):
        for k in list(cfg.keys()):
            _resolve_container_value(cfg, k)

    elif isinstance(cfg, (ListConfig, TupleConfig)):
        for i in range(len(cfg)):
            _resolve_container_value(cfg, i)

    return cfg


def select_value(
    cfg: Container,
    key: str,
    *,
    default: Any = _DEFAULT_MARKER_,
    throw_on_resolution_failure: bool = True,
    throw_on_missing: bool = False,
    absolute_key: bool = False,
) -> Any:
    node = select_node(
        cfg=cfg,
        key=key,
        throw_on_resolution_failure=throw_on_resolution_failure,
        throw_on_missing=throw_on_missing,
        absolute_key=absolute_key,
    )

    node_not_found = node is None
    if node_not_found or node._is_missing():
        if default is not _DEFAULT_MARKER_:
            return default
        else:
            return None

    return _get_value(node)


def select_node(
    cfg: Container,
    key: str,
    *,
    throw_on_resolution_failure: bool = True,
    throw_on_missing: bool = False,
    absolute_key: bool = False,
) -> Any:
    try:
        # for non relative keys, the interpretation can be:
        # 1. relative to cfg
        # 2. relative to the config root
        # This is controlled by the absolute_key flag. By default, such keys are relative to cfg.
        if not absolute_key and not key.startswith("."):
            key = f".{key}"

        try:
            cfg, key = cfg._resolve_key_and_root(key)
        except ConfigKeyError:
            return None

        _root, _last_key, node = cfg._select_impl(
            key,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )
    except ConfigTypeError:
        return None

    return node
