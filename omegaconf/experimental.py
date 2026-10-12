"""Private experimental operations, without a compatibility guarantee."""

from typing import Any, Iterator

from . import Container, OmegaConf
from ._impl import _is_recursive_container
from ._utils import (
    _get_value,
    _is_special,
    _schema_validation,
    is_primitive_container,
    is_primitive_dict,
)
from .base import Node, UnionNode, _copy_with_parent
from .basecontainer import BaseContainer
from .errors import (
    InterpolationResolutionError,
    InterpolationValidationError,
    KeyValidationError,
    ValidationError,
)
from .grammar_parser import parse
from .nodes import AnyNode, ValueNode
from .tupleconfig import TupleConfig

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


def _revalidate_values(target: Node) -> None:
    for node in _nodes(target):
        if isinstance(node, ValueNode) and not _is_special(node):
            node.validate_and_convert(node._value())


def _materialize_private_container(
    target: Container,
    node: Container,
    destination: Container,
    raw: Any,
    key: Any | None,
) -> Node:
    """Materialize a resolver container under its preserved destination policy."""
    if _is_recursive_container(raw):
        target._format_and_raise(
            key=key,
            value=raw,
            cause=InterpolationResolutionError(
                "Cannot materialize a recursive resolver result"
            ),
        )
    raw_is_node = isinstance(raw, Node)
    resolved: Any = _copy_input(raw)
    if is_primitive_container(resolved):
        resolved = OmegaConf.create(resolved, flags={"allow_objects": True})
    assert isinstance(resolved, Container)

    _normalize_source_flags(resolved)
    destination_flags = dict(destination._metadata.flags or {})
    for flag, value in destination_flags.items():
        if flag != "allow_objects":
            resolved._set_flag(flag, value)
    _apply_destination_object_policy(destination, resolved)
    # Container construction may need the ancestor policy, but every supplied
    # child already carries its destination-local policy from the step above.
    resolved._set_flag("allow_objects", True)
    parent = node._get_parent_container()
    if not raw_is_node:
        resolved._set_parent(parent)
        resolved._set_key(key)
    OmegaConf.resolve(resolved)
    _revalidate_values(resolved)

    destination._set_flag("allow_objects", True)
    destination._set_flag("readonly", False)
    assert isinstance(destination, BaseContainer)
    try:
        try:
            destination._merge_with(resolved, _allow_readonly_target=True)
        except (ValidationError, KeyValidationError) as exc:
            target._format_and_raise(
                key=key,
                value=_get_value(resolved),
                cause=exc,
                msg=f"While dereferencing interpolation: {exc}",
                type_override=InterpolationValidationError,
            )
    finally:
        destination._metadata.flags = destination_flags
        destination._invalidate_flags_cache()

    # Merging can rebuild sequence children under the temporary permissive root
    # and thereby drop local flags. Copy the retained source policies back onto
    # the merged destination before validating only supplied fields.
    _apply_destination_object_policy(resolved, destination)
    _validate_supplied(destination, resolved, resolve=True, destination=destination)
    resolved._set_parent(parent)
    destination._set_parent(parent)
    destination._set_key(key)
    node.__dict__["_content"] = destination.__dict__["_content"]
    node._metadata.object_type = destination._metadata.object_type
    node._re_parent()
    return node


def _resolve_private_value(
    target: Container,
    key: Any | None = None,
    destination: Node | None = None,
) -> Node:
    node = target if key is None else target._get_child(key)
    assert isinstance(node, Node)
    destination = destination if destination is not None else node
    assert isinstance(destination, Node)
    destination_allow_objects = destination._get_flag("allow_objects")
    destination_flags = dict(destination._metadata.flags or {})

    # A container interpolation replaces the destination container before the
    # resolver is dereferenced. Use the preserved destination graph to transfer
    # nested policies before typed materialization can validate the result.
    if (
        isinstance(destination, Container)
        and isinstance(node, Container)
        and node._is_interpolation()
    ):
        parent = node._get_parent_container()
        receiver = parent if parent is not None else target
        raw = receiver.resolve_parse_tree(parse(_get_value(node)), node=node, key=key)
        if isinstance(raw, Container) or is_primitive_container(raw):
            return _materialize_private_container(
                target=target,
                node=node,
                destination=destination,
                raw=raw,
                key=key,
            )
        resolved = receiver._validate_and_convert_interpolation_result(
            parent=parent,
            value=node,
            key=key,
            resolved=raw,
            throw_on_resolution_failure=True,
        )
    else:
        resolved = node._dereference_node()

    if isinstance(resolved, Container):
        _normalize_source_flags(resolved)
        resolved._set_flag("allow_objects", destination_allow_objects)
        for flag, value in destination_flags.items():
            if flag != "allow_objects":
                resolved._set_flag(flag, value)
        OmegaConf.resolve(resolved)
        _revalidate_values(resolved)
        if isinstance(node, AnyNode):
            assert key is not None
            if isinstance(target, TupleConfig):
                target._set_item_for_resolution(key, resolved)
            else:
                target[key] = resolved
            stored = target._get_child(key)
            assert isinstance(stored, Node)
            return stored
        node._set_value(resolved, flags=destination_flags or None)
    else:
        node._set_value(_get_value(resolved))
    return node


def _validate_supplied(
    target: Node,
    supplied: Node,
    resolve: bool,
    destination: Node | None = None,
) -> None:
    if isinstance(target, ValueNode) and not _is_special(target):
        target.validate_and_convert(target._value())
        return
    if not isinstance(target, Container):
        return
    for key, child in _supplied_children(supplied):
        if child._is_missing():
            continue
        existing = target._get_child(key)
        assert isinstance(existing, Node)
        destination_child = None
        if isinstance(destination, Container) and isinstance(
            destination.__dict__.get("_content"), (dict, list)
        ):
            candidate = destination._get_child(key, validate_access=False)
            if isinstance(candidate, Node):
                destination_child = candidate
        if child._is_interpolation():
            if resolve:
                _resolve_private_value(target, key, destination_child)
        else:
            _validate_supplied(existing, child, resolve, destination_child)


def _validate(cfg: Container, overrides: Any, *, resolve: bool = False) -> None:
    """Validate supplied fields against cfg without conversion or input mutation.

    Only supplied fields are checked; omitted required fields are allowed.
    Validation does not read structured defaults or invoke their factories. With resolve=False,
    interpolations are deferred, so their eventual types are not guaranteed.
    With resolve=True, needed expressions are evaluated in a private patched
    copy of cfg, retaining its ancestor context and isolating resolver caches.
    Resolver callbacks keep their ordinary OmegaConf behavior. Their side
    effects outside the private graph are not rolled back.

    This private experiment returns None or raises an OmegaConf validation or
    resolution error. It does not attach a schema to the original overrides.
    """
    if not isinstance(cfg, BaseContainer):
        raise TypeError("cfg must be an OmegaConf container")
    if _is_recursive_container(overrides):
        raise ValidationError("Cannot validate a recursive input container")
    target = _copy_with_parent(cfg)
    assert isinstance(target, BaseContainer)
    token = _schema_validation.set(True)
    try:
        supplied = _copy_input(overrides)
        if _is_special(supplied):
            destination = _copy_with_parent(target)
            target._set_value(_get_value(supplied))
            if resolve and target._is_interpolation():
                _resolve_private_value(target, destination=destination)
            return
        if not isinstance(supplied, BaseContainer):
            supplied = OmegaConf.create(
                supplied,
                # Object support is checked by the eventual destination node.
                # Keep raw patches permissive until that destination is known.
                flags={"allow_objects": True},
            )
            supplied = _copy_input(supplied)
        destination = _copy_with_parent(target)
        _apply_destination_object_policy(target, supplied)
        _clear_overwritten_interpolations(target, supplied)
        try:
            target._merge_with(supplied, _allow_readonly_target=True)
        except TypeError as exc:
            target._format_and_raise(
                key=None, value=overrides, cause=ValidationError(str(exc))
            )
        if resolve:
            for node in _nodes(target._get_root()):
                node._set_flag("readonly", False)
        _validate_supplied(target, supplied, resolve, destination)
    finally:
        _schema_validation.reset(token)
