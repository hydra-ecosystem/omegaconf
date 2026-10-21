import copy
from dataclasses import make_dataclass
from typing import Any, Dict, List

from pytest import fixture, mark, param

from omegaconf import OmegaConf
from omegaconf._utils import ValueKind, _is_missing_literal, get_value_kind, split_key


def build_dict(
    d: Dict[str, Any], depth: int, width: int, leaf_value: Any = 1
) -> Dict[str, Any]:
    if depth == 0:
        for i in range(width):
            d[f"key_{i}"] = leaf_value
    else:
        for i in range(width):
            c: Dict[str, Any] = {}
            d[f"key_{i}"] = c
            build_dict(c, depth - 1, width, leaf_value)

    return d


def build_list(length: int, val: Any = 1) -> List[int]:
    return [val] * length


@fixture(scope="module")
def large_dict() -> Any:
    return build_dict({}, 11, 2)


@fixture(scope="module")
def small_dict() -> Any:
    return build_dict({}, 5, 2)


@fixture(scope="module")
def dict_with_list_leaf() -> Any:
    return build_dict({}, 5, 2, leaf_value=[1, 2])


@fixture(scope="module")
def small_dict_config(small_dict: Any) -> Any:
    return OmegaConf.create(small_dict)


@fixture(scope="module")
def dict_config_with_list_leaf(dict_with_list_leaf: Any) -> Any:
    return OmegaConf.create(dict_with_list_leaf)


@fixture(scope="module")
def large_dict_config(large_dict: Any) -> Any:
    return OmegaConf.create(large_dict)


@fixture(scope="module", params=["overlap", "sparse", "nested", "structured", "list"])
def merge_data(request: Any) -> Any:
    shape = request.param
    source: Any = {f"key_{i}": i for i in range(1000)}
    overlay: Any = {f"key_{i}": -i for i in range(1000)}
    if shape == "sparse":
        overlay = {"key_500": -1}
    elif shape == "nested":
        source = {
            f"dataset_{i}": {
                "path": f"data/{i}.csv",
                "options": {"seed": i, "sep": ","},
            }
            for i in range(100)
        }
        overlay = {f"dataset_{i}": {"options": {"seed": -i}} for i in range(100)}
    elif shape == "structured":
        source = make_dataclass(
            "BenchmarkSchema", [(f"key_{i}", int, i) for i in range(1000)]
        )
    elif shape == "list":
        source, overlay = list(range(1000)), list(range(1000, 2000))
    return [OmegaConf.create(source), OmegaConf.create(overlay)]


@fixture(scope="module")
def small_list() -> Any:
    return build_list(3, 1)


@fixture(scope="module")
def small_listconfig(small_list: Any) -> Any:
    return OmegaConf.create(small_list)


@mark.parametrize(
    "data_fixture",
    [
        "small_dict",
        "large_dict",
        "small_dict_config",
        "large_dict_config",
        "dict_config_with_list_leaf",
    ],
)
def test_omegaconf_create(data_fixture: str, benchmark: Any, request: Any) -> None:
    data = request.getfixturevalue(data_fixture)
    benchmark(OmegaConf.create, data)


@mark.parametrize(
    "merge_function",
    [
        param(OmegaConf.merge, id="merge"),
        param(OmegaConf.unsafe_merge, id="unsafe_merge"),
    ],
)
def test_omegaconf_merge(merge_function: Any, merge_data: Any, benchmark: Any) -> None:
    def setup() -> Any:
        # unsafe_merge consumes its inputs; safe merge uses the same setup.
        return tuple(copy.deepcopy(merge_data)), {}

    benchmark.pedantic(
        merge_function, setup=setup, rounds=25, warmup_rounds=5, iterations=1
    )


@mark.parametrize(
    "operation",
    [
        "item",
        "attribute",
        "nested_item",
        "nested_attribute",
        "string",
        "container",
        "list",
        "get_hit",
        "get_miss",
        "reference",
        "resolver",
        "select",
        "structured",
        "union",
    ],
)
def test_access(operation: str, benchmark: Any) -> None:
    OmegaConf.register_resolver("benchmark.identity", lambda value: value, replace=True)
    cfg = OmegaConf.create(
        {
            "value": 7,
            "text": "ordinary string",
            "model": {"options": {"value": 7}},
            "items": [7, 8, 9],
            "reference": "${value}",
            "resolver": "${benchmark.identity:7}",
        }
    )
    seq = cfg["items"]
    schema = make_dataclass("AccessSchema", [("value", int, 7)])
    union_schema = make_dataclass("UnionAccessSchema", [("value", int | str, 7)])
    typed = OmegaConf.structured(schema)
    union = OmegaConf.structured(union_schema)
    operations = {
        "item": lambda: cfg["value"],
        "attribute": lambda: cfg.value,
        "nested_item": lambda: cfg["model"]["options"]["value"],
        "nested_attribute": lambda: cfg.model.options.value,
        "string": lambda: cfg["text"],
        "container": lambda: cfg["model"],
        "list": lambda: seq[1],
        "get_hit": lambda: cfg.get("value", -1),
        "get_miss": lambda: cfg.get("absent", -1),
        "reference": lambda: cfg["reference"],
        "resolver": lambda: cfg["resolver"],
        "select": lambda: OmegaConf.select(cfg, "model.options.value"),
        "structured": lambda: typed.value,
        "union": lambda: union.value,
    }
    try:
        benchmark(operations[operation])
    finally:
        OmegaConf.clear_resolver("benchmark.identity")


@mark.parametrize(
    "lst_fixture",
    [
        "small_list",
        "small_listconfig",
    ],
)
def test_list_in(lst_fixture: str, benchmark: Any, request: Any) -> None:
    lst: List[Any] = request.getfixturevalue(lst_fixture)
    benchmark(lambda seq, val: val in seq, lst, 10)


@mark.parametrize(
    "lst_fixture",
    [
        "small_list",
        "small_listconfig",
    ],
)
def test_list_iter(lst_fixture: str, benchmark: Any, request: Any) -> None:
    lst: List[Any] = request.getfixturevalue(lst_fixture)

    def iterate(seq: Any) -> None:
        for _ in seq:
            pass

    benchmark(iterate, lst)


@mark.parametrize(
    "strict_interpolation_validation",
    [True, False],
)
@mark.parametrize(
    ("value", "expected"),
    [
        ("simple", ValueKind.VALUE),
        ("${a}", ValueKind.INTERPOLATION),
        ("${a:b,c,d}", ValueKind.INTERPOLATION),
        ("${${b}}", ValueKind.INTERPOLATION),
        ("${a:${b}}", ValueKind.INTERPOLATION),
        ("${long_string1xxx}_${long_string2xxx:${key}}", ValueKind.INTERPOLATION),
        (
            "${a[1].a[1].a[1].a[1].a[1].a[1].a[1].a[1].a[1].a[1].a[1]}",
            ValueKind.INTERPOLATION,
        ),
    ],
)
def test_get_value_kind(
    strict_interpolation_validation: bool, value: Any, expected: Any, benchmark: Any
) -> None:
    assert benchmark(get_value_kind, value, strict_interpolation_validation) == expected


def test_is_missing_literal(benchmark: Any) -> None:
    assert benchmark(_is_missing_literal, "???")


@mark.parametrize(
    "key",
    [
        param("a", id="single"),
        param("a.b.c", id="dot:short"),
        param("a.b.c.d.e.f.g.h", id="dot:long"),
        param("a[b].c", id="bracket"),
        param(r"a\.b.c", id="escaped_dot"),
        param(r"a\[b\].c", id="escaped_brackets"),
        param(r"a\.b\.c\.d\.e\.f\.g\.h", id="escaped_dot:long"),
    ],
)
def test_split_key(key: str, benchmark: Any) -> None:
    benchmark(split_key, key)


@mark.parametrize("force_add", [False, True])
@mark.parametrize("key", ["a", "a.a.a.a.a.a.a.a.a.a.a"])
def test_update_force_add(
    large_dict_config: Any, key: str, force_add: bool, benchmark: Any
) -> None:
    cfg = copy.deepcopy(large_dict_config)  # this test modifies the config
    if force_add:
        OmegaConf.set_struct(cfg, True)

    def recursive_is_struct(node: Any) -> None:
        if OmegaConf.is_config(node):
            OmegaConf.is_struct(node)
            for val in node.values():
                recursive_is_struct(val)

    recursive_is_struct(cfg)

    benchmark(OmegaConf.update, cfg, key, 10, force_add=force_add)
