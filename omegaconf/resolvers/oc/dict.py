import base64
import json
import math
from enum import Enum
from typing import Any, List

from omegaconf import AnyNode, Container, DictConfig, ListConfig, Node
from omegaconf._utils import Marker
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import (
    ConfigKeyError,
    InterpolationKeyError,
    InterpolationToMissingValueError,
)

_DEFAULT_SELECT_MARKER_: Any = Marker("_DEFAULT_SELECT_MARKER_")
_VALUE_REF_PREFIX = "${oc.dict._value:"


class _ValueReference(str):
    """A portable expression that also retains its raw key during Python copies."""

    key: Any

    def __new__(cls, value: str, key: Any) -> "_ValueReference":
        reference = super().__new__(cls, value)
        reference.key = key
        return reference

    def __reduce__(self) -> tuple[Any, tuple[str, Any]]:
        return type(self), (str(self), self.key)


def _encode_reference(path: str, key: Any) -> str:
    if isinstance(key, Enum):
        key_data = ["enum", [type(key).__module__, type(key).__qualname__, key.name]]
    elif isinstance(key, bytes):
        key_data = ["bytes", key.hex()]
    else:
        key_data = [type(key).__name__, key]
    return _ValueReference(_pack_reference([path, key_data]), key)


def _pack_reference(data: Any) -> str:
    token = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return f"{_VALUE_REF_PREFIX}{token}}}"


def _unpack_reference(token: str) -> Any:
    return json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))


def _reference_enums_to_str(value: str) -> str:
    """Match the Enum key conversion performed by to_container(enum_to_str=True)."""
    if not value.startswith(_VALUE_REF_PREFIX) or not value.endswith("}"):
        return value
    try:
        path, key_data = _unpack_reference(value[len(_VALUE_REF_PREFIX) : -1])
        if key_data[0] == "enum":
            key = key_data[1][2]
            return _ValueReference(_pack_reference([path, ["str", key]]), key)
    except (ValueError, TypeError, IndexError, KeyError):
        # Unresolved expressions supplied by users need not be valid references.
        pass
    return value


def _value(token: str, _parent_: Container, _node_: Node) -> Node:
    """Resolve an internal, serialized raw-key reference produced by values()."""
    assert isinstance(_parent_, BaseContainer)
    path, key_data = _unpack_reference(token)
    source = _get_and_validate_dict_input(
        path, parent=_parent_, resolver_name="oc.dict.values"
    )
    result = _reference_node(token, key_data, source, _node_)._dereference_node()
    _parent_._validate_not_dereferencing_to_parent(node=_node_, target=result)
    return result


def _reference_node(
    token: str, key_data: Any, source: DictConfig, reference: Node
) -> Node:
    kind, key = key_data
    cache = reference._metadata.resolver_cache.setdefault("oc.dict._value", {})
    raw = reference._value()
    if isinstance(raw, _ValueReference):
        key = raw.key
    elif token in cache:
        key = cache[token]
    else:
        if kind == "bytes":
            key = bytes.fromhex(key)
        elif kind == "enum":
            key = next(
                (
                    candidate
                    for candidate in source
                    if isinstance(candidate, Enum)
                    and [
                        type(candidate).__module__,
                        type(candidate).__qualname__,
                        candidate.name,
                    ]
                    == key
                ),
                _DEFAULT_SELECT_MARKER_,
            )
        elif kind == "float" and math.isnan(key):
            key = next(
                (
                    candidate
                    for candidate in source
                    if isinstance(candidate, float) and math.isnan(candidate)
                ),
                _DEFAULT_SELECT_MARKER_,
            )
        if key is not _DEFAULT_SELECT_MARKER_:
            cache[token] = key
    node = (
        None
        if key is _DEFAULT_SELECT_MARKER_
        else source._get_child(key, validate_access=False)
    )
    if node is None:
        raise InterpolationKeyError(
            f"Dictionary key {key!r} not found in '{source._get_full_key(None)}'"
        )
    assert isinstance(node, Node)
    if node._is_missing():
        raise InterpolationToMissingValueError(
            f"Missing mandatory value: {source._get_full_key(key)}"
        )
    return node


def keys(
    key: str,
    _parent_: Container,
) -> ListConfig:
    from omegaconf import OmegaConf

    assert isinstance(_parent_, BaseContainer)

    in_dict = _get_and_validate_dict_input(
        key, parent=_parent_, resolver_name="oc.dict.keys"
    )

    ret = OmegaConf.create(list(in_dict.keys()), parent=_parent_)
    assert isinstance(ret, ListConfig)
    return ret


def values(key: str, _root_: BaseContainer, _parent_: Container) -> ListConfig:
    assert isinstance(_parent_, BaseContainer)
    in_dict = _get_and_validate_dict_input(
        key, parent=_parent_, resolver_name="oc.dict.values"
    )

    content = in_dict._content
    assert isinstance(content, dict)

    ret = ListConfig([])
    if key.startswith("."):
        key = f".{key}"  # extra dot to compensate for extra level of nesting within ret ListConfig
    for k in content:
        reference = _encode_reference(key, k)
        ref_node = AnyNode(reference)
        ret.append(ref_node)

    # Finalize result by setting proper type and parent.
    element_type: Any = in_dict._metadata.element_type
    ret._metadata.element_type = element_type
    ret._metadata.ref_type = List[element_type]
    ret._set_parent(_parent_)

    return ret


def _get_and_validate_dict_input(
    key: str,
    parent: BaseContainer,
    resolver_name: str,
) -> DictConfig:
    from omegaconf._impl import select_value

    if not isinstance(key, str):
        raise TypeError(
            f"`{resolver_name}` requires a string as input, but obtained `{key}` "
            f"of type: {type(key).__name__}"
        )

    in_dict = select_value(
        parent,
        key,
        throw_on_missing=True,
        absolute_key=True,
        default=_DEFAULT_SELECT_MARKER_,
    )

    if in_dict is _DEFAULT_SELECT_MARKER_:
        raise ConfigKeyError(f"Key not found: '{key}'")

    if not isinstance(in_dict, DictConfig):
        raise TypeError(
            f"`{resolver_name}` cannot be applied to objects of type: "
            f"{type(in_dict).__name__}"
        )

    return in_dict
