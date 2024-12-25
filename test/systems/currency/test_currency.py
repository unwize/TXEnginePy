from copy import deepcopy

import pytest

from game.systems.currency.currency import Currency


def get_cur():
    currencies = {
        "USD": Currency(-1, "USD", {"cents": 1, "dollars": 100, "k": 100000, "m": 100000000}),
        "Imperial": Currency(-2, "Imperial", {"copper": 1, "silver": 100, "gold": 10000}),
    }
    return currencies


add_int_quantity_cases = [
    ["USD", [1], 1],
    ["USD", [0], 0],
    ["USD", [1, 1], 2],
    ["USD", [12, 12, 13], 37],
    ["USD", [0, 0, 0, 0], 0],
    ["USD", [1, 100, 0], 101],
    ["USD", [-1], -1],
    ["USD", [-1, 1], 0],
]


@pytest.mark.parametrize("currency, offsets, result", add_int_quantity_cases)
def test_add_int_quantity(currency: str, offsets: list[int], result: int):
    cur = deepcopy(get_cur()[currency])

    for offset in offsets:
        cur = cur + offset

    assert cur.quantity == result


add_int_str_cases = [
    ["USD", [1], "1 cents"],
    ["USD", [0], "0 cents"],
    ["USD", [1, 1], "2 cents"],
    ["USD", [12, 12, 13], "37 cents"],
    ["USD", [0, 0, 0, 0], "0 cents"],
    ["USD", [1, 100, 0], "1 dollars 1 cents"],
    ["USD", [1111], "11 dollars 11 cents"],
    ["USD", [100000], "1 k 0 dollars 0 cents"],
]


@pytest.mark.parametrize("currency, offsets, result", add_int_str_cases)
def test_add_int_str(currency: str, offsets: list[int], result: str):
    cur = deepcopy(get_cur()[currency])

    for offset in offsets:
        cur = cur + offset

    assert str(cur) == result


sub_int_cases = [
    ["USD", [1, 0], 1],
    ["USD", [5, 5, 0], 0],
    ["USD", [5, 3], 2],
    ["USD", [2, 1], 1],
    ["USD", [-1, 0], -1],
    ["USD", [1, 3], -2],
    ["USD", [0, 0], 0],
    ["USD", [0, 3], -3],
    ["USD", [10, 1, 1, 1, 3], 4],
]


@pytest.mark.parametrize("currency, offsets, result", sub_int_cases)
def test_sub_int(currency: str, offsets: list, result: int):
    """Test that Currency objects correctly handle subtraction by int

    The Currency's initial value is determined by offsets[0]. Each subsequent value of 'offsets' represents a
    subtraction.
    """
    cur = deepcopy(get_cur()[currency])
    cur.quantity = offsets[0]

    for i in range(1, len(offsets)):
        cur = cur - offsets[i]

    assert cur.quantity == result


mul_int_cases = [
    ["USD", [1, 1], 1],
    ["USD", [1, 2], 2],
    ["USD", [1, 0], 0],
    ["USD", [0, 0], 0],
    ["USD", [0, 1], 0],
    ["USD", [0, 928123], 0],
    ["USD", [1, 2, 3], 6],
    ["USD", [2, 2, 2], 8],
    ["USD", [3, -1, -1], 3],
    ["USD", [-1, -1, 2], 2],
]


@pytest.mark.parametrize("currency, offsets, result", mul_int_cases)
def test_mul_int(currency: str, offsets: list, result: int):
    """Test that Currency objects correctly handle multiplication by int

    The Currency's initial value is determined by offsets[0]. Each subsequent value of 'offsets' represents a
    multiplication.
    """

    cur = deepcopy(get_cur()[currency])
    cur.quantity = offsets[0]

    for i in range(1, len(offsets)):
        cur = cur * offsets[i]

    assert cur.quantity == result


mul_float_cases = [
    ["USD", [1, 1.0], 1],
    ["USD", [1, 2.0], 2],
    ["USD", [1, 0.0], 0],
    ["USD", [0, 0.0], 0],
    ["USD", [0, 1.0], 0],
    ["USD", [0, 928123.0], 0],
    ["USD", [1, 2.0, 3.0], 6],
    ["USD", [2, 2.0, 2.0], 8],
    ["USD", [3, -1.0, -1.0], 3],
    ["USD", [-1, -1.0, 2.0], 2],
    ["USD", [4, 2.5], 10],
    ["USD", [3, 2.5], 7],
]


@pytest.mark.parametrize("currency, offsets, result", mul_float_cases)
def test_mul_float(currency: str, offsets: list, result: int):
    """Test that Currency objects correctly handle multiplication by float

    The Currency's initial value is determined by offsets[0]. Each subsequent value of 'offsets' represents a
    multiplication.
    """

    cur = deepcopy(get_cur()[currency])
    cur.quantity = offsets[0]

    for i in range(1, len(offsets)):
        cur = cur * offsets[i]

    assert type(cur.quantity) is int, "Quantity was not an int!"
    assert cur.quantity == result, f"Quantity was not as expected: {cur.quantity} != {result}"


div_int_cases = [
    ["USD", [1, 1], 1],
    ["USD", [0, 1], 0],
    ["USD", [1, 2], 0],
    ["USD", [2, 2], 1],
    ["USD", [2, -1], -2],
    ["USD", [3, 2], 1],
    ["USD", [4, 2], 2],
    ["USD", [-2, 2], -1],
    ["USD", [10, 2, 5], 1],
    ["USD", [20, 2, 1, -1, -1], 10],
]


@pytest.mark.parametrize("currency, offsets, result", div_int_cases)
def test_div_int(currency: str, offsets: list, result: int):
    """
    Test that currency objects correctly handle integer division
    """
    cur = deepcopy(get_cur()[currency])
    cur.quantity = offsets[0]

    for i in range(1, len(offsets)):
        cur = cur / offsets[i]

    assert type(cur.quantity) is int, "Quantity was not an int!"
    assert cur.quantity == result, f"Quantity was not as expected: {cur.quantity} != {result}"


div_float_cases = [
    ["USD", [3, 1.5], 2],
    ["USD", [7, 3.5], 2],
    ["USD", [1, 1.0], 1],
    ["USD", [0, 2.0], 0],
    ["USD", [-3, 1.5], -2],
    ["USD", [3, -1.5], -2],
    ["USD", [10, 1.1], 9],
]


@pytest.mark.parametrize("currency, offsets, result", div_float_cases)
def test_div_float(currency: str, offsets: list, result: int):
    """
    Test that currency objects correctly handle float division
    """
    cur = deepcopy(get_cur()[currency])
    cur.quantity = offsets[0]

    for i in range(1, len(offsets)):
        cur = cur / offsets[i]

    assert type(cur.quantity) is int, "Quantity was not an int!"
    assert cur.quantity == result, f"Quantity was not as expected: {cur.quantity} != {result}"


set_cases_good = [
    ["USD", [1]],
    ["USD", [1, 0]],
    ["USD", [-1]],
    ["USD", [1, -1]],
    ["USD", [1000, 10]],
    ["USD", [19, -1, 2022, 4]],
]


@pytest.mark.parametrize("currency, values", set_cases_good)
def test_set_good(currency: str, values: list[int]):
    """
    Test that Currency::set correctly assigns values to Currency::quantity
    """
    cur: Currency = deepcopy(get_cur()[currency])
    assert cur.quantity == 0

    for value in values:
        cur.set(value)
        assert cur.quantity == value

    assert cur.quantity == values[-1]


set_cases_bad = [
    ["USD", [1.0]],
    ["USD", [1, 0.0]],
    ["USD", [None]],
    ["USD", ["1", -1]],
    ["USD", [1000, "10"]],
    ["USD", [19, None, 2022, 4]],
    ["USD", [True]],
    ["USD", [lambda: pow(2, 2)]],
]


@pytest.mark.parametrize("currency, values", set_cases_bad)
def test_set_bad(currency: str, values: list[int]):
    """
    Test that Currency::set correctly reject invalid values
    """
    cur: Currency = deepcopy(get_cur()[currency])

    with pytest.raises(TypeError):
        for value in values:
            cur.set(value)


adjust_int_cases_good = [
    ["USD", [1, 2, 3], 6],
    ["USD", [-1, 1, 3], 3],
    ["USD", [50, 0, 0], 50],
    ["USD", [1, 0, 3], 4],
    ["USD", [-2, -3, -1], -6],
    ["USD", [1], 1],
    ["USD", [0], 0],
]

adjust_float_cases_good = [
    ["USD", [1, 3.0], 3],
    ["USD", [0, 3.0, 2.0, 1.0], 0],
    ["USD", [1, 0.0], 0],
    ["USD", [1, -1.0], -1],
    ["USD", [1, 2.0, 3.0], 6],
    ["USD", [5, 2.5], 12],
    ["USD", [1, 0.5], 0],
    ["USD", [20, 0.2], 4],
    ["USD", [6, 0.33], 2],
]

adjust_mixed_cases_good = [
    ["USD", [1, 0, 1, 0.0], 0],
    ["USD", [1, 2.5, 3], 5],
    ["USD", [1, 2.0, 3], 5],
    ["USD", [1, 0.33, 3], 3],
    ["USD", [6, 0.33, 2.0], 4],
    ["USD", [100, 0.33, 1], 34],
    ["USD", [100, -50, 1.1], 55],
]


@pytest.mark.parametrize(
    "currency, offsets, result", adjust_int_cases_good + adjust_float_cases_good + adjust_mixed_cases_good
)
def test_adjust_good(currency: str, offsets: list[int], result):
    cur: Currency = deepcopy(get_cur()[currency])

    assert cur.quantity == 0

    for offset in offsets:
        cur.adjust(offset)

    assert cur.quantity == result


adjust_cases_bad = [
    ["USD", [None]],
    ["USD", ["sneaky number"]],
    ["USD", [1, 2.0, None]],
    ["USD", [2.0, 1, 0, 0.0, "4"]],
    ["USD", [True]],
    ["USD", [False]],
    ["USD", [1, False, True]],
]


@pytest.mark.parametrize("currency, offsets", adjust_cases_bad)
def test_adjust_bad(currency: str, offsets: list[int]):
    cur: Currency = deepcopy(get_cur()[currency])

    with pytest.raises(TypeError):
        for offset in offsets:
            cur.adjust(offset)
