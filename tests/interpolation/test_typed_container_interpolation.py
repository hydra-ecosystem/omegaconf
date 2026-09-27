import warnings
from dataclasses import dataclass, field
from typing import Any, Tuple, cast

from pytest import raises

from omegaconf import (
    MISSING,
    DictConfig,
    KeyValidationError,
    ListConfig,
    OmegaConf,
    TupleConfig,
    flag_override,
)
from omegaconf.errors import InterpolationResolutionError, InterpolationValidationError
from tests import Color


@dataclass
class ListAlias:
    source: list[str] = field(default_factory=lambda: ["1"])
    target: list[int] = field(default_factory=list)


@dataclass
class TupleUnionAlias:
    source: list[int] = field(default_factory=lambda: [1])
    target: tuple[int, ...] | str = "x"


@dataclass
class ConvertingTupleUnionAlias:
    source: list[str] = field(default_factory=lambda: ["1"])
    target: tuple[int, ...] | str = "x"


@dataclass
class MatchingAlias:
    source: list[int] = field(default_factory=lambda: [1])
    target: list[int] = field(default_factory=list)


@dataclass
class Nested:
    port: int = 1


@dataclass
class StructuredAlias:
    source: Nested = field(default_factory=Nested)
    target: Nested = field(default_factory=Nested)


@dataclass
class GenericTupleAlias:
    target: Tuple[Any, ...] = ()


@dataclass
class RecursiveContainers:
    list_target: list[Any] = field(default_factory=list)
    dict_target: dict[str, Any] = field(default_factory=dict)


@dataclass
class DictAlias:
    source: dict[str, str] = field(default_factory=lambda: {"a": "1"})
    target: dict[str, int] = field(default_factory=dict)


@dataclass
class NestedContainerAlias:
    source: dict[str, list[tuple[str, ...]]] = field(
        default_factory=lambda: cast(dict[str, list[tuple[str, ...]]], {"1": [("2",)]})
    )
    target: dict[str, list[tuple[int, ...]]] = field(default_factory=dict)


@dataclass
class MatchingDictAlias:
    source: dict[str, int] = field(default_factory=lambda: {"a": 1})
    target: dict[str, int] = field(default_factory=dict)


@dataclass
class PrimitiveKeyMismatchAlias:
    source: dict[int, str] = field(default_factory=lambda: {1: "2"})
    target: dict[str, int] = field(default_factory=dict)


@dataclass
class EnumKeyAlias:
    target: dict[Color, int] = field(default_factory=dict)


def test_typed_list_alias_coerces_on_lazy_access_and_resolve() -> None:
    cfg = OmegaConf.structured(ListAlias)
    cfg.target = "${source}"

    target = cfg.target
    assert isinstance(target, ListConfig)
    assert target[0] == 1
    assert cfg.source[0] == "1"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", FutureWarning)
        OmegaConf.resolve(cfg)
    assert not [w for w in caught if issubclass(w.category, FutureWarning)]
    assert cfg.target[0] == 1
    assert cfg.source[0] == "1"


def test_matching_typed_list_alias_keeps_source_node() -> None:
    cfg = OmegaConf.structured(MatchingAlias)
    cfg.target = "${source}"
    assert cfg.target is cfg.source


def test_typed_container_interpolation_rejects_invalid_element() -> None:
    cfg = OmegaConf.structured(ListAlias)
    cfg.source[0] = "bad"
    cfg.target = "${source}"
    with raises(InterpolationValidationError):
        _ = cfg.target


def test_typed_container_interpolation_honors_convert_false() -> None:
    cfg = OmegaConf.structured(ListAlias)
    cfg.target = "${source}"
    with flag_override(cfg, "convert", False):
        with raises(InterpolationValidationError):
            _ = cfg.target

    target_node = cfg._get_node("target")
    assert target_node is not None
    with flag_override(target_node, "convert", False):
        with raises(InterpolationValidationError):
            _ = cfg.target


def test_typed_dict_interpolation_converts_values_on_all_paths() -> None:
    cfg: Any = OmegaConf.structured(DictAlias)
    cfg.target = "${source}"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        target = cfg.target
        assert isinstance(target, DictConfig)
        assert target["a"] == 1
        assert type(target["a"]) is int
        plain = OmegaConf.to_container(cfg, resolve=True)
        assert isinstance(plain, dict)
        assert plain["target"] == {"a": 1}
        OmegaConf.resolve(cfg)
    assert not [w for w in caught if issubclass(w.category, FutureWarning)]
    assert cfg.source["a"] == "1"
    assert type(cfg.source["a"]) is str
    target = cfg.target
    assert isinstance(target, DictConfig)
    assert target["a"] == 1


def test_primitive_dict_key_mismatch_is_rejected_for_typed_source() -> None:
    cfg = OmegaConf.structured(PrimitiveKeyMismatchAlias)
    cfg.target = "${source}"

    with raises(InterpolationValidationError):
        _ = cfg.target
    with raises(InterpolationValidationError):
        OmegaConf.resolve(cfg)
    with raises(InterpolationValidationError):
        OmegaConf.to_container(cfg, resolve=True)
    assert cfg.source == {1: "2"}
    assert OmegaConf.is_interpolation(cfg, "target")


def test_primitive_dict_key_mismatch_is_rejected_for_direct_assignment() -> None:
    cfg = OmegaConf.structured(DictAlias)
    with raises(KeyValidationError):
        cfg.target = {1: "2"}


def test_primitive_dict_key_mismatch_is_rejected_for_raw_resolver(
    restore_resolvers: Any,
) -> None:
    OmegaConf.register_resolver("raw_key_mismatch", lambda: {1: "2"})
    cfg = OmegaConf.structured(DictAlias)
    cfg.target = "${raw_key_mismatch:}"

    with raises(InterpolationValidationError):
        _ = cfg.target
    with raises(InterpolationValidationError):
        OmegaConf.resolve(cfg)
    with raises(InterpolationValidationError):
        OmegaConf.to_container(cfg, resolve=True)
    assert OmegaConf.is_interpolation(cfg, "target")


def test_enum_dict_keys_keep_existing_normalization(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("enum_key_values", lambda: {"RED": "1"})
    cfg: Any = OmegaConf.structured(EnumKeyAlias)
    cfg.target = "${enum_key_values:}"

    target = cfg.target
    assert isinstance(target, DictConfig)
    assert target[Color.RED] == 1
    OmegaConf.resolve(cfg)
    target = cfg.target
    assert isinstance(target, DictConfig)
    assert target[Color.RED] == 1


def test_nested_typed_container_interpolation_converts_without_source_mutation() -> (
    None
):
    cfg: Any = OmegaConf.structured(NestedContainerAlias)
    cfg.target = "${source}"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert cfg.target == {"1": [(2,)]}
        plain = OmegaConf.to_container(cfg, resolve=True)
        assert isinstance(plain, dict)
        assert plain["target"] == {"1": [(2,)]}
        OmegaConf.resolve(cfg)
    assert not [w for w in caught if issubclass(w.category, FutureWarning)]
    assert cfg.target == {"1": [(2,)]}
    assert cfg.source == {"1": [("2",)]}
    assert type(cfg.source["1"][0][0]) is str


def test_matching_typed_dict_interpolation_keeps_source_node() -> None:
    cfg = OmegaConf.structured(MatchingDictAlias)
    cfg.target = "${source}"
    assert cfg.target is cfg.source


def test_typed_dict_interpolation_rejects_invalid_value_and_preserves_source() -> None:
    cfg: Any = OmegaConf.structured(DictAlias)
    cfg.source["a"] = "bad"
    cfg.target = "${source}"
    with raises(InterpolationValidationError):
        _ = cfg.target
    assert cfg.source["a"] == "bad"
    assert OmegaConf.is_interpolation(cfg, "target")


def test_typed_dict_interpolation_honors_convert_false() -> None:
    cfg = OmegaConf.structured(DictAlias)
    cfg.target = "${source}"
    target_node = cfg._get_node("target")
    assert target_node is not None
    with flag_override(target_node, "convert", False):
        with raises(InterpolationValidationError):
            _ = cfg.target


def test_typed_container_resolver_result_coerces(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("source_list", lambda: ["1"])
    cfg = OmegaConf.structured(ListAlias)
    cfg.target = "${source_list:}"
    assert isinstance(cfg.target, ListConfig)
    assert cfg.target[0] == 1


def test_nested_resolver_result_uses_destination_type(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("source_list", lambda: ["1"])
    OmegaConf.register_resolver("identity_list", lambda value: value)
    cfg = OmegaConf.structured(ListAlias)
    cfg.target = "${identity_list:${source_list:}}"
    assert cfg.target == [1]
    plain = OmegaConf.to_container(cfg, resolve=True)
    assert isinstance(plain, dict)
    assert plain["target"] == [1]


def test_structured_interpolation_matching_schema_aliases() -> None:
    cfg = OmegaConf.structured(StructuredAlias)
    cfg.target = "${source}"
    assert cfg.target is cfg.source


def test_resolver_result_in_any_destination_is_not_coerced(
    restore_resolvers: Any,
) -> None:
    OmegaConf.register_resolver("source_list", lambda: ["1"])
    cfg = OmegaConf.create({"target": "${source_list:}"})
    assert cfg.target == ["1"]
    assert isinstance(cfg.target, list)


def test_union_interpolation_returns_selected_converted_member() -> None:
    cfg = OmegaConf.structured(TupleUnionAlias)
    cfg.target = "${source}"
    assert isinstance(cfg.target, TupleConfig)
    assert cfg.target[0] == 1
    assert isinstance(cfg.source, ListConfig)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", FutureWarning)
        OmegaConf.resolve(cfg)
    assert not [w for w in caught if issubclass(w.category, FutureWarning)]
    assert isinstance(cfg.target, TupleConfig)
    assert cfg.target[0] == 1


def test_union_interpolation_honors_convert_false() -> None:
    cfg = OmegaConf.structured(ConvertingTupleUnionAlias)
    cfg.target = "${source}"
    target_node = cfg._get_node("target")
    assert target_node is not None
    with flag_override(target_node, "convert", False):
        with raises(InterpolationValidationError):
            _ = cfg.target


def test_generic_tuple_resolver_result_matches_lazy_and_eager(
    restore_resolvers: Any,
) -> None:
    OmegaConf.register_resolver("source_list", lambda: [1, 2])
    cfg = OmegaConf.structured(GenericTupleAlias)
    cfg.target = "${source_list:}"
    assert isinstance(cfg.target, TupleConfig)
    assert cfg.target == (1, 2)
    OmegaConf.resolve(cfg)
    assert isinstance(cfg.target, TupleConfig)
    assert cfg.target == (1, 2)


def test_generic_tuple_resolver_preserves_opaque_missing(
    restore_resolvers: Any,
) -> None:
    OmegaConf.register_resolver("source_tuple", lambda: (r"\???", MISSING))
    cfg = OmegaConf.structured(GenericTupleAlias)
    cfg.target = "${source_tuple:}"
    assert cfg.target[0] == r"\???"
    assert cfg.target[1] == MISSING
    assert not OmegaConf.is_missing(cfg.target, 1)
    OmegaConf.resolve(cfg)
    assert cfg.target[0] == r"\???"
    assert cfg.target[1] == MISSING
    assert not OmegaConf.is_missing(cfg.target, 1)


def test_recursive_typed_list_resolver_result_is_bounded(
    restore_resolvers: Any,
) -> None:
    recursive: list[Any] = []
    recursive.append(recursive)
    OmegaConf.register_resolver("recursive_typed_list", lambda: recursive)
    cfg = OmegaConf.structured(RecursiveContainers)
    cfg.list_target = "${recursive_typed_list:}"

    with raises(InterpolationResolutionError, match="recursive resolver result"):
        _ = cfg.list_target
    assert OmegaConf.is_interpolation(cfg, "list_target")

    with raises(InterpolationResolutionError, match="recursive resolver result"):
        OmegaConf.resolve(cfg)
    assert OmegaConf.is_interpolation(cfg, "list_target")


def test_recursive_typed_dict_resolver_result_is_bounded(
    restore_resolvers: Any,
) -> None:
    recursive: dict[str, Any] = {}
    recursive["self"] = recursive
    OmegaConf.register_resolver("recursive_typed_dict", lambda: recursive)
    cfg = OmegaConf.structured(RecursiveContainers)
    cfg.dict_target = "${recursive_typed_dict:}"

    with raises(InterpolationResolutionError, match="recursive resolver result"):
        _ = cfg.dict_target
    assert OmegaConf.is_interpolation(cfg, "dict_target")

    with raises(InterpolationResolutionError, match="recursive resolver result"):
        OmegaConf.resolve(cfg)
    assert OmegaConf.is_interpolation(cfg, "dict_target")
