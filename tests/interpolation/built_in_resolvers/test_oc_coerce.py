from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pytest import mark, param, raises

from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError
from tests import Color


@mark.parametrize(
    ("type_name", "source", "expected"),
    [
        param("int", "10", 10, id="int"),
        param("builtins.int", "10", 10, id="qualified-int"),
        param("float", "10", 10.0, id="float"),
        param("bool", "yes", True, id="bool"),
        param("str", 10, "10", id="str"),
        param("bytes", b"abc", b"abc", id="bytes"),
        param("pathlib.Path", "./out", Path("out"), id="path"),
        param("tests.Color", "RED", Color.RED, id="enum"),
        param("types.NoneType", None, None, id="none-type"),
    ],
)
def test_coerce_untyped_destination_uses_explicit_type(
    type_name: str, source: Any, expected: Any
) -> None:
    cfg = OmegaConf.create(
        {"source": source, "result": f"${{oc.coerce:{type_name},${{source}}}}"}
    )
    assert cfg.result == expected
    assert type(cfg.result) is type(expected)


@dataclass
class TypedCoerceDestinations:
    as_str: str = ""
    as_int: int = 0
    string_values: list[str] = field(default_factory=list)


def test_coerce_typed_destination_applies_its_conversion() -> None:
    cfg = OmegaConf.structured(TypedCoerceDestinations)
    cfg.as_str = "${oc.coerce:int,10}"
    cfg.as_int = "${oc.coerce:str,10}"
    cfg.string_values = ["${oc.coerce:int,10}"]

    assert cfg.as_str == "10"
    assert type(cfg.as_str) is str
    assert cfg.as_int == 10
    assert type(cfg.as_int) is int
    assert cfg.string_values[0] == "10"
    assert type(cfg.string_values[0]) is str

    OmegaConf.resolve(cfg)
    assert cfg.as_str == "10"
    assert type(cfg.as_str) is str
    assert cfg.as_int == 10
    assert type(cfg.as_int) is int
    assert cfg.string_values[0] == "10"
    assert type(cfg.string_values[0]) is str


def test_coerce_nested_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("OC_TEST_PORT", "8080")
    cfg = OmegaConf.create({"port": "${oc.coerce:int,${oc.env:OC_TEST_PORT}}"})
    assert cfg.port == 8080


@mark.parametrize("type_name", ["no_such_package.Color", "builtins.list"])
def test_coerce_invalid_type_fails_on_access_and_resolve(type_name: str) -> None:
    expression = f"${{oc.coerce:{type_name},1}}"
    cfg = OmegaConf.create({"value": expression})
    with raises(InterpolationResolutionError):
        _ = cfg.value
    with raises(InterpolationResolutionError):
        OmegaConf.resolve(cfg)


def test_coerce_invalid_value_fails_on_access_and_resolve() -> None:
    cfg = OmegaConf.create({"value": "${oc.coerce:int,abc}"})
    with raises(InterpolationResolutionError):
        _ = cfg.value
    with raises(InterpolationResolutionError):
        OmegaConf.resolve(cfg)
