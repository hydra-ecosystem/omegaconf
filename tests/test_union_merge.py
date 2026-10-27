from dataclasses import dataclass, field
from typing import Any

from pytest import mark, raises

from omegaconf import AnyNode, DictConfig, Node, OmegaConf, UnionNode
from omegaconf.errors import ConfigKeyError, ReadonlyConfigError, ValidationError
from tests.test_structured_config_unions import Cat, Dog, PetWithDefaultConfig


@mark.parametrize("placement", ["field", "list", "tuple"])
@mark.parametrize("source", ["mapping", "structured", "union"])
def test_direct_union_merge_preserves_selected_branch(
    placement: str, source: str
) -> None:
    parent = OmegaConf.structured(PetWithDefaultConfig)
    if placement == "list":
        parent = OmegaConf.create([parent._get_node("pet")])
    elif placement == "tuple":
        parent = OmegaConf.create((parent._get_node("pet"),))
    key = "pet" if placement == "field" else 0
    node = parent._get_node(key)
    assert isinstance(node, UnionNode)
    update = {
        "mapping": OmegaConf.create({"name": "Fido"}),
        "structured": OmegaConf.structured(Dog(name="Fido")),
        "union": OmegaConf.structured(
            PetWithDefaultConfig(pet=Dog(name="Fido"))
        )._get_node("pet"),
    }[source]

    node._merge_with(update)

    selected = parent[key]
    assert selected == {"name": "Fido", "breed": "Lab"}
    assert OmegaConf.get_type(selected) is Dog
    assert selected._get_parent_container() is parent
    assert node._get_parent_container() is parent


def test_direct_union_merge_switches_typed_branch_without_changing_source() -> None:
    parent = OmegaConf.structured(PetWithDefaultConfig)
    source = OmegaConf.structured(Cat(name="Mochi", indoor=True))
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)

    node._merge_with(source)

    assert OmegaConf.get_type(parent.pet) is Cat
    assert parent.pet == {"name": "Mochi", "indoor": True}
    assert source._get_parent() is None
    assert source == {"name": "Mochi", "indoor": True}


@mark.parametrize("typed", [False, True])
def test_direct_union_merge_respects_explicit_mapping_branch(typed: bool) -> None:
    parent = OmegaConf.create(
        {"pet": UnionNode(Dog(name="Rex", breed="Lab"), Dog | dict[str, Any])}
    )
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)
    source = (
        OmegaConf.typed_dict({"name": "Fido"}, key_type=str, element_type=str)
        if typed
        else OmegaConf.create({"name": "Fido"})
    )

    node._merge_with(source)

    assert parent.pet == (
        {"name": "Fido"} if typed else {"name": "Fido", "breed": "Lab"}
    )
    assert OmegaConf.get_type(parent.pet) is (dict if typed else Dog)


@mark.parametrize("readonly", [False, True])
@mark.parametrize("missing", [False, True])
def test_direct_interpolated_union_merge_keeps_default_and_context(
    readonly: bool,
    missing: bool,
) -> None:
    @dataclass
    class InterpolatingDog(Dog):
        inherited: str = "${..base}"
        derived: str = "${pet.name}"

    @dataclass
    class Parent:
        base: str = "context"
        default: InterpolatingDog | None = field(
            default_factory=lambda: InterpolatingDog(name="Rex", breed="Lab")
        )
        pet: InterpolatingDog | Cat = "${default}"  # type: ignore[assignment]

    parent = OmegaConf.structured(Parent)
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)
    OmegaConf.set_readonly(parent, readonly)

    source = AnyNode("???") if missing else OmegaConf.create({"name": "Fido"})
    node._merge_with(source, _allow_readonly_target=readonly)

    expected_name = "Rex" if missing else "Fido"
    assert parent.pet.name == expected_name
    assert parent.pet.breed == "Lab"
    assert parent.pet.inherited == "context"
    assert parent.pet.derived == expected_name
    assert parent.default.name == "Rex"
    assert not OmegaConf.is_interpolation(parent, "pet")
    assert OmegaConf.is_readonly(parent) is readonly
    assert OmegaConf.is_readonly(parent.pet) is readonly


@mark.parametrize("readonly", [False, True])
def test_unsafe_merge_interpolated_union_isolates_default_and_parents(
    readonly: bool,
) -> None:
    @dataclass
    class Owner:
        default: Dog = field(default_factory=lambda: Dog(name="Rex", breed="Lab"))
        pet: Dog | Cat = "${default}"  # type: ignore[assignment]

    parent = OmegaConf.structured(Owner)
    OmegaConf.set_readonly(parent, readonly)
    result = OmegaConf.unsafe_merge(parent, {"pet": {"name": "Fido"}})

    assert isinstance(result, DictConfig)
    pet_node = result._get_node("pet")
    default_node = result._get_node("default")
    assert isinstance(pet_node, UnionNode)
    selected = pet_node._value()
    assert isinstance(selected, DictConfig)
    assert isinstance(default_node, DictConfig)
    selected_name = selected._get_child("name")
    default_name = default_node._get_child("name")
    assert isinstance(selected_name, Node)
    assert isinstance(default_name, Node)
    assert selected._get_parent_container() is result
    assert selected_name._get_parent_container() is selected
    assert default_name._get_parent_container() is default_node
    assert selected_name is not default_name
    assert result.pet.name == "Fido"
    assert result.default.name == "Rex"
    assert OmegaConf.is_readonly(result) is readonly
    assert OmegaConf.is_readonly(result.pet) is readonly


def test_direct_union_merge_rejects_unknown_structured_key() -> None:
    parent = OmegaConf.structured(PetWithDefaultConfig)
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)

    with raises(ConfigKeyError, match="unknown"):
        node._merge_with(OmegaConf.create({"unknown": 1}))

    assert parent.pet == {"name": "Rex", "breed": "Lab"}


def test_direct_union_merge_respects_readonly() -> None:
    parent = OmegaConf.structured(PetWithDefaultConfig)
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)
    OmegaConf.set_readonly(parent, True)

    with raises(ReadonlyConfigError) as error:
        node._merge_with(OmegaConf.structured(Cat(name="Mochi", indoor=True)))

    assert error.value.full_key == "pet"
    assert parent.pet == {"name": "Rex", "breed": "Lab"}
    assert OmegaConf.is_readonly(parent.pet)


@mark.parametrize("direct", [False, True])
def test_union_merge_preserves_validation_error_context(direct: bool) -> None:
    parent = OmegaConf.structured(PetWithDefaultConfig)
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)

    with raises(ValidationError) as error:
        if direct:
            node._merge_with(AnyNode(10))
        else:
            OmegaConf.merge(parent, {"pet": 10})

    assert error.value.full_key == "pet"
    assert "$VALUE" not in str(error.value)


def test_direct_union_merge_preserves_scalar_and_special_value_rules() -> None:
    node = UnionNode(10, int | str)
    node._merge_with(AnyNode("???"))
    assert node == 10
    node._merge_with(AnyNode("text"))
    assert node == "text"
    node._merge_with(AnyNode(None))
    assert node._is_none()
    with raises(ValidationError):
        node._merge_with(OmegaConf.create([1, 2]))
    assert node._is_none()


def test_direct_union_merge_keeps_source_interpolation_lazy() -> None:
    parent = OmegaConf.structured(PetWithDefaultConfig)
    node = parent._get_node("pet")
    assert isinstance(node, UnionNode)
    source = UnionNode("${later}", Dog | Cat)

    node._merge_with(source)

    assert OmegaConf.is_interpolation(parent, "pet")
    assert source._is_interpolation()
    assert node._value() == "${later}"


@mark.parametrize(
    "initial,update,expected",
    [([1, 2], [3], [3]), ({"a": 1}, {"b": 2}, {"b": 2})],
)
def test_direct_union_container_merge_keeps_existing_replacement_semantics(
    initial: Any, update: Any, expected: Any
) -> None:
    parent = OmegaConf.create({"value": UnionNode(initial, list[int] | dict[str, int])})
    node = parent._get_node("value")
    assert isinstance(node, UnionNode)

    node._merge_with(OmegaConf.create(update))

    assert parent.value == expected
