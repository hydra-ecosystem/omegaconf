"""Private experimental operations, without a compatibility guarantee."""

from typing import Any, Iterator

from . import Container, OmegaConf
from ._impl import _is_recursive_container
from ._utils import (
    _get_value,
    _is_special,
    _schema_validation,
    is_primitive_dict,
)
from .base import Node, UnionNode, _copy_with_parent
from .basecontainer import BaseContainer
from .errors import ValidationError
from .nodes import ValueNode

__all__: list[str] = []


def _nodes(node: Node) -> Iterator[Node]:
    yield node
    content = node.__dict__.get("_content")
    if isinstance(content, Node):
        yield from _nodes(content)
    elif isinstance(content, (dict, list)):
        for child in content.values() if isinstance(content, dict) else content:
            yield from _nodes(child)


def _copy_input(value: Any) -> Any:
    if isinstance(value, Node):
        result = _copy_with_parent(value)
        _normalize_source_flags(result)
        return result
    if is_primitive_dict(value):
        return {key: _copy_input(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        children = [_copy_input(child) for child in value]
        return tuple(children) if isinstance(value, tuple) else children
    return value


def _supplied_children(node: Node) -> Iterator[tuple[Any, Node]]:
    if isinstance(node, UnionNode):
        content = node._value()
        if isinstance(content, Node):
            yield from _supplied_children(content)
        return
    content = node.__dict__.get("_content")
    if isinstance(content, dict):
        yield from content.items()
    elif isinstance(content, list):
        yield from enumerate(content)


def _normalize_source_flags(node: Node) -> None:
    for child in _nodes(node):
        child._metadata.flags = {}
        child._invalidate_flags_cache()


def _clear_overwritten_interpolations(target: Node, supplied: Node) -> None:
    if supplied._is_missing():
        return
    if target._is_interpolation():
        from . import MISSING

        target._set_value(MISSING)
    if isinstance(target, Container) and isinstance(
        target.__dict__["_content"], (dict, list)
    ):
        for key, child in _supplied_children(supplied):
            existing = target._get_child(key, validate_access=False)
            if isinstance(existing, Node):
                _clear_overwritten_interpolations(existing, child)


def _apply_destination_object_policy(target: Node, supplied: Node) -> None:
    """Carry each destination node's object policy onto the private source copy."""
    if not isinstance(target, Container):
        return
    if not isinstance(target.__dict__.get("_content"), (dict, list)):
        policy = target._get_flag("allow_objects")
        for _, child in _supplied_children(supplied):
            child._set_flag("allow_objects", policy)
        return
    for key, child in _supplied_children(supplied):
        existing = target._get_child(key, validate_access=False)
        if isinstance(existing, Node):
            child._set_flag("allow_objects", existing._get_flag("allow_objects"))
            _apply_destination_object_policy(existing, child)
        else:
            child._set_flag("allow_objects", target._get_flag("allow_objects"))


def _validate_supplied(target: Node, supplied: Node) -> None:
    if isinstance(target, ValueNode) and not _is_special(target):
        target.validate_and_convert(target._value())
        return
    if not isinstance(target, Container):
        return
    for key, child in _supplied_children(supplied):
        if child._is_missing() or child._is_interpolation():
            continue
        existing = target._get_child(key)
        assert isinstance(existing, Node)
        _validate_supplied(existing, child)


def _validate(cfg: Container, overrides: Any, *, in_place: bool = False) -> None:
    """Validate supplied fields against cfg without conversion or resolution.

    Only supplied fields are checked; omitted required fields are allowed.
    Validation does not read structured defaults or invoke their factories.
    Interpolations are deferred, so their eventual types are not guaranteed.

    By default both inputs remain unchanged. With in_place=True, the caller
    must own cfg's graph, including its ancestor context. Validation merges
    into cfg and can change its contents, metadata, flags and caches, including
    after failure. Readonly flags within cfg are cleared. Supplied nodes are
    still copied before merge; aliases into cfg's owned graph observe changes.

    This private experiment returns None or raises a validation error.
    It does not attach a schema to the original overrides.
    """
    if not isinstance(cfg, BaseContainer):
        raise TypeError("cfg must be an OmegaConf container")
    if _is_recursive_container(overrides):
        raise ValidationError("Cannot validate a recursive input container")
    target = cfg if in_place else _copy_with_parent(cfg)
    assert isinstance(target, BaseContainer)
    token = _schema_validation.set(True)
    try:
        supplied = _copy_input(overrides)
        if in_place:
            for node in _nodes(target):
                node._set_flag("readonly", False)
        if _is_special(supplied):
            target._set_value(_get_value(supplied))
            return
        if not isinstance(supplied, BaseContainer):
            supplied = OmegaConf.create(
                supplied,
                # Object support is checked by the eventual destination node.
                # Keep raw patches permissive until that destination is known.
                flags={"allow_objects": True},
            )
            supplied = _copy_input(supplied)
        _apply_destination_object_policy(target, supplied)
        _clear_overwritten_interpolations(target, supplied)
        try:
            target._merge_with(supplied, _allow_readonly_target=True)
        except TypeError as exc:
            target._format_and_raise(
                key=None, value=overrides, cause=ValidationError(str(exc))
            )
        _validate_supplied(target, supplied)
    finally:
        _schema_validation.reset(token)
