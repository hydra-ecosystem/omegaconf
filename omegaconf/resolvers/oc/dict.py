from typing import Any, List

from omegaconf import AnyNode, Container, DictConfig, ListConfig
from omegaconf._key_path import _escape_key, split_key
from omegaconf._utils import Marker
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import ConfigKeyError

_DEFAULT_SELECT_MARKER_: Any = Marker("_DEFAULT_SELECT_MARKER_")


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
    relative_dots = len(key) - len(key.lstrip("."))
    path = key[relative_dots:]
    path_parts = split_key(path) if path else []
    escaped_path = "".join(
        ("." if i else "") + _escape_key(part) if part else "[]"
        for i, part in enumerate(path_parts)
    )
    # Compensate for the extra level of nesting within the returned ListConfig.
    prefix = "." * (relative_dots + 1) if relative_dots else ""
    for k in content:
        escaped_key = _escape_key(str(k))
        suffix = ("." if escaped_path else "") + escaped_key if escaped_key else "[]"
        ref_node = AnyNode(f"${{{prefix}{escaped_path}{suffix}}}")
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
