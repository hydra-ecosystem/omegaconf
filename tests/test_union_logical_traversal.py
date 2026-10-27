import copy
import pickle
from dataclasses import dataclass, field

from pytest import mark, raises

from omegaconf import OmegaConf, UnionNode
from omegaconf.base import Node
from omegaconf.errors import ConfigKeyError


@dataclass
class Adam:
    lr: float = 0.001
    inherited: float = "${..base_lr}"  # type: ignore[assignment]


@dataclass
class SGD:
    momentum: float = 0.9


@dataclass
class Config:
    base_lr: float = 0.01
    optimizer: Adam | SGD = field(default_factory=Adam)
    choices: list[Adam | SGD] = field(default_factory=lambda: [Adam(), SGD()])
    named: dict[str, Adam | SGD] = field(
        default_factory=lambda: {"adam": Adam(), "sgd": SGD()}
    )


@mark.parametrize("placement", ["field", "list", "dict"])
def test_selected_union_child_has_logical_key_and_path(placement: str) -> None:
    config = OmegaConf.structured(Config)
    parent, key, path = {
        "field": (config, "optimizer", "optimizer"),
        "list": (config.choices, 0, "choices[0]"),
        "dict": (config.named, "adam", "named.adam"),
    }[placement]
    child = parent._get_child(key)
    assert child._get_parent_container() is parent
    assert child._key() == key
    assert parent._get_child(child._key()) is child
    assert child._get_full_key(None) == path
    assert child._get_full_key("lr") == path + ".lr"
    assert child._get_node("lr")._get_full_key(None) == path + ".lr"


def test_union_key_follows_list_reindexing() -> None:
    config = OmegaConf.structured(Config)
    member = config.choices[1]
    assert member._key() == 1
    del config.choices[0]
    assert member._key() == 0
    assert member._get_full_key(None) == "choices[0]"
    assert config.choices._get_child(member._key()) is member


@mark.parametrize("clone", [copy.deepcopy, lambda cfg: pickle.loads(pickle.dumps(cfg))])
def test_union_logical_navigation_survives_copy(clone) -> None:
    original = OmegaConf.structured(Config)
    config = clone(original)
    assert config.optimizer._key() == "optimizer"
    assert config.optimizer._get_parent_container() is config
    assert config._get_child(config.optimizer._key()) is config.optimizer
    assert config.optimizer._get_full_key("lr") == "optimizer.lr"
    assert config.optimizer.inherited == 0.01
    assert original.optimizer.lr == 0.001


def test_union_merge_keeps_branch_selection_and_logical_path() -> None:
    config = OmegaConf.structured(Config)
    merged = OmegaConf.merge(config, {"optimizer": {"lr": 0.2}})
    assert OmegaConf.get_type(merged.optimizer) is Adam
    assert merged.optimizer.lr == 0.2
    assert merged.optimizer._key() == "optimizer"
    assert merged.optimizer._get_full_key(None) == "optimizer"
    switched = OmegaConf.merge(config, {"optimizer": SGD()})
    assert OmegaConf.get_type(switched.optimizer) is SGD
    assert switched.optimizer._key() == "optimizer"
    assert switched.optimizer._get_full_key("momentum") == "optimizer.momentum"
    with raises(ConfigKeyError):
        OmegaConf.merge(config, {"optimizer": {"unknown": 1}})


@mark.parametrize(
    "parent", [{"value": UnionNode(10, int | str)}, [UnionNode(10, int | str)]]
)
def test_scalar_union_child_has_logical_key(parent) -> None:
    config = OmegaConf.create(parent)
    key = "value" if OmegaConf.is_dict(config) else 0
    child = config._get_child(key)
    assert child._key() == key
    assert child._get_parent_container()._get_child(child._key()) is child


def test_union_child_lookup_preserves_unresolved_interpolation() -> None:
    config = OmegaConf.create({"value": UnionNode("${missing}", int | str)})
    child = config._get_child("value")
    assert isinstance(child, Node)
    assert child._is_interpolation()
    assert child._value() == "${missing}"
    assert child._key() == "value"
