import copy
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pytest import mark, raises

from omegaconf import MissingMandatoryValue, OmegaConf
from omegaconf.base import ContainerMetadata, Metadata
from omegaconf.grammar_parser import _parse_cached


@mark.parametrize("sequence", [False, True])
def test_reads_follow_value_changes(sequence: bool) -> None:
    cfg = OmegaConf.create([7, 11] if sequence else {"value": 7, "seed": 11})
    key: Any = 0 if sequence else "value"
    reference = "${1}" if sequence else "${seed}"
    assert cfg[key] == 7
    cfg[key] = reference
    assert cfg[key] == 11
    cfg[key] = "???"
    with raises(MissingMandatoryValue):
        cfg[key]
    cfg[key] = r"\???"
    assert cfg[key] == "???"
    cfg[key] = r"\${unknown}"
    assert cfg[key] == "${unknown}"


def test_missing_string_subclass() -> None:
    class UnequalString(str):
        def __ne__(self, other: Any) -> bool:
            return True

    cfg = OmegaConf.create({"value": UnequalString("???")})
    assert cfg.get("value", 7) == 7
    with raises(MissingMandatoryValue):
        cfg["value"]


def test_interpolation_unhashable_string_subclass() -> None:
    class UnhashableString(str):
        def __eq__(self, other: Any) -> bool:
            return super().__eq__(other)

    cfg = OmegaConf.create({"seed": 7, "value": UnhashableString("${seed}")})
    assert cfg.value == 7
    cfg.seed = 11
    assert cfg.value == 11


def test_cached_syntax_keeps_resolvers_dynamic(restore_resolvers: Any) -> None:
    calls = []

    def identity(value: Any) -> Any:
        calls.append(value)
        return value

    OmegaConf.register_resolver("dynamic", identity)
    cfg = OmegaConf.create({"seed": 7, "value": "${dynamic:${seed}}"})
    assert cfg.value == 7
    cfg.seed = 11
    assert cfg.value == 11
    assert calls == [7, 11]
    OmegaConf.register_resolver("dynamic", lambda value: value + 1, replace=True)
    assert cfg.value == 12


def test_cached_syntax_keeps_config_context() -> None:
    def read(seed: int) -> int:
        cfg = OmegaConf.create({"seed": seed, "value": "${seed}"})
        for i in range(300):
            OmegaConf.create({"seed": i, "value": f"${{seed}}-{i}"}).value
        return cfg.value

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(read, range(8))) == list(range(8))


def test_cached_parse_keeps_modes_separate() -> None:
    text = "123"
    config_tree = _parse_cached(text)
    element_tree = _parse_cached(text, "singleElement", "VALUE_MODE")
    assert config_tree.getRuleIndex() != element_tree.getRuleIndex()
    assert _parse_cached(text).getText() == text + "<EOF>"
    # Long literals parse correctly without affecting other cached syntax.
    assert _parse_cached("x" * 4097).getText() == "x" * 4097 + "<EOF>"
    assert _parse_cached(text).getText() == text + "<EOF>"


def test_metadata_copy_preserves_aliases_and_isolates_mutables() -> None:
    metadata = Metadata(ref_type=Any, object_type=None, optional=True, key="value")
    metadata.flags = {"readonly": True}
    metadata.resolver_cache["flags"] = metadata.flags
    metadata.resolver_cache["self"] = metadata
    metadata.resolver_cache["values"] = [7]
    cloned = copy.deepcopy(metadata)
    assert cloned.resolver_cache["self"] is cloned
    assert cloned.resolver_cache["flags"] is cloned.flags
    assert cloned.flags is not metadata.flags
    assert cloned.flags is not None
    cloned.flags["readonly"] = False
    cloned.resolver_cache["values"].append(11)
    assert metadata.flags["readonly"] is True
    assert metadata.resolver_cache["values"] == [7]


def test_metadata_copy_preserves_subclass_slots() -> None:
    class InheritedSlotMetadata(ContainerMetadata):
        __slots__ = "__private"
        __private: dict[str, list[int]]

    class SlotMetadata(InheritedSlotMetadata):
        __slots__ = ("slot_state", "unset_slot")
        slot_state: dict[str, list[int]]
        unset_slot: dict[str, list[int]]

    metadata = SlotMetadata(
        ref_type=Any,
        object_type=dict,
        optional=True,
        key="value",
        key_type=Any,
    )
    setattr(metadata, "_InheritedSlotMetadata__private", {"values": [1]})
    metadata.slot_state = {"values": [2]}
    metadata.resolver_cache["slot_state"] = metadata.slot_state
    metadata.resolver_cache["metadata"] = metadata

    cfg = OmegaConf.create({})
    cfg.__dict__["_metadata"] = metadata
    cloned = copy.deepcopy(cfg)
    cloned_metadata = cloned.__dict__["_metadata"]

    assert cloned_metadata.slot_state == {"values": [2]}
    assert cloned_metadata.slot_state is not metadata.slot_state
    assert getattr(cloned_metadata, "_InheritedSlotMetadata__private") == {
        "values": [1]
    }
    assert getattr(cloned_metadata, "_InheritedSlotMetadata__private") is not getattr(
        metadata, "_InheritedSlotMetadata__private"
    )
    assert cloned_metadata.resolver_cache["slot_state"] is cloned_metadata.slot_state
    assert cloned_metadata.resolver_cache["metadata"] is cloned_metadata
    with raises(AttributeError):
        _ = cloned_metadata.unset_slot

    cloned_metadata.slot_state["values"].append(3)
    assert metadata.slot_state == {"values": [2]}
