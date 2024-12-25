import pytest
from loguru import logger

from game.systems.currency import currency_manager
from game.systems.currency.coin_purse import CoinPurse
from game.systems.currency.currency import Currency


def test_init():
    """
    Test that a CoinPurse object can be trivially initialized
    """
    CoinPurse()


def test_currency_acquisition():
    """
    Test that CoinPurse correctly acquires empty Currency objects from the currency_manager
    """

    cp = CoinPurse()
    assert len(cp.currencies.keys()) == len(currency_manager._manifest.keys())
    assert len(cp.currencies) > 0

    for key in currency_manager._manifest:
        assert key in cp.currencies
        assert cp.balance(key) == 0


@pytest.mark.parametrize("cur", currency_manager._manifest.values())
def test_contains(cur: int | Currency):
    """
    Test that CoinPurse correctly detects the requested currency
    """

    cp = CoinPurse()
    assert cur in cp


contains_bad_cases = [True, False, None, "s", 0.0]


@pytest.mark.parametrize("cur", contains_bad_cases)
def test_contains_bad(cur):
    """
    Test that CoinPurse::__contains__ rejects invalid values
    """

    cp = CoinPurse()

    with pytest.raises(KeyError):
        assert cur not in cp


@pytest.mark.parametrize("cur", currency_manager._manifest.keys())
def test_getitem(cur: int | Currency):
    cp = CoinPurse()

    assert len(cp.currencies) > 0

    got = cp[cur]

    assert got is not None
    assert type(got) is Currency


@pytest.mark.parametrize("cur", contains_bad_cases)
def test_getitem_bad(cur: int | Currency):
    """
    Test that CoinPurse::__getitem__ correctly rejects invalid values
    """
    cp = CoinPurse()

    with pytest.raises(KeyError):
        assert cur not in cp


def test_iter_next():
    """
    Verify that CoinPurse::__iter__ and CoinPurse::__next__ are functional

    It is important to verify two properties of CoinPurse's iterable behavior:
        1. CoinPurse correctly traverses its currency list, returning each currency id
        2. A single instance of CoinPurse can be iterated on indefinitely. Each attempted iterator must be correct
    """

    cp = CoinPurse()
    target_iter_len = len(currency_manager._manifest.keys())

    # Iterate upon the same CoinPurse instance twice
    for i in range(2):
        counter = 0  # Track how many elements were seen. You could also just enumerate.

        for cur in cp:  # Actually iterate
            assert cp is not None
            assert cur in cp  # Check if the returned value is meaningful
            counter += 1  # Increment counter

        assert counter == target_iter_len  # Verify we iterated the correct number of times
        logger.info(f"Success! Iterated {target_iter_len} times.")


def test_balance_trivial():
    """
    Trivially check that the currencies in CoinPurse post-init are present and at their initial states
    """

    cp = CoinPurse()
    assert len(cp.currencies) > 0

    for currency in cp:
        assert cp.balance(currency) is not None
        assert cp.balance(currency) == 0


def test_balance_int():
    """
    Test that CoinPurse::balance correctly retrieves values when fed a key of type int
    """
    cp = CoinPurse()
    cp.currencies[-110].quantity = 12
    cp.currencies[-111].quantity = 100231

    assert cp.balance(-110) == 12
    assert cp.balance(-111) == 100231


def test_balance_currency():
    """
    Test that CoinPurse::balance correctly retrieves values when fed a key of type Currency
    """
    cp = CoinPurse()
    cp.currencies[-110].quantity = 12
    cp.currencies[-111].quantity = 100231

    cur0 = currency_manager.to_currency(-110, 0)  # Special testing currencies
    cur1 = currency_manager.to_currency(-111, 0)

    assert cp.balance(cur0) == 12
    assert cp.balance(cur1) == 100231


balance_bad_cases = [None, "str", -123123, Currency]


@pytest.mark.parametrize("cur", balance_bad_cases)
def test_balance_bad(cur: int | Currency):
    """
    Test that CoinPurse::balance correctly rejects invalid values
    """
    cp = CoinPurse()

    with pytest.raises(KeyError):
        assert cp.balance(cur) == 0


spend_cases_good = [[-110, 1, 1, 0], [-110, 100, 50, 50], [-110, 73, 12, 61], [-111, 1, 1, 0], [-111, 51, 2, 49]]


@pytest.mark.parametrize("cur, start, offset, result", spend_cases_good)
def test_spend(cur: int | Currency, start: int, offset: int, result: int):
    """Test that CoinPurse::spend correctly reduces currency values"""

    cp = CoinPurse()
    assert cp.balance(cur) == 0
    cp.currencies[cur].quantity = start
    assert cp.spend(cur, offset)
    assert cp.balance(cur) == result


spend_cases_false = [
    [-110, 0, 1],
    [-110, 100, 101],
]


@pytest.mark.parametrize("cur, start, offset", spend_cases_false)
def test_spend_false(cur: int, start: int, offset: int):
    """
    Test that CoinPurse::spend correctly returns False when presented with an
    impossible request
    """
    cp = CoinPurse()
    assert cp.balance(cur) == 0
    cp.currencies[cur].quantity = start
    assert not cp.spend(cur, offset)


spend_cases_bad = [
    [-12, 0, 0],
    [None, 0, 0],
    [-110, 0, None],
    ["a", 100, -101],
]


# TODO: Split this test into multiple smaller tests that explicitly verify that each type of rejection works
@pytest.mark.parametrize("cur, start, offset", spend_cases_bad)
def test_spend_bad(cur: int, start: int, offset: int):
    """Test that CoinPurse::spend correctly rejects invalid values"""
    cp = CoinPurse()

    with pytest.raises((ValueError, KeyError, TypeError)):
        cp.spend(cur, offset)


adjust_int_cases_good = [
    [[0], 0],
    [[1], 1],
    [[0, 1], 1],
    [[0, 0], 0],
    [[1, -1], 0],
    [[2, -1], 1],
    [[100, 1], 101],
    [[7, 23], 30],
    [[4, -8], -4],
    [[-4, 8], 4],
    [[-1, 0], -1],
]


@pytest.mark.parametrize("offsets, result", adjust_int_cases_good)
def test_adjust_int(offsets: list[int], result):
    cp = CoinPurse()
    for cur in cp:
        assert cp.balance(cur) == 0

        for offset in offsets:
            cp.adjust(cur, offset)


adjust_float_cases_good = [
    [0, [0.0], 0],
    [0, [1.0], 0],
    [0, [-1.0], 0],
    [1, [0.0], 0],
    [-1, [0.0], 0],
    [1, [0.5], 0],
    [7, [0.5], 3],
    [20, [0.5], 10],
    [9, [0.33], 3],
    [9, [-0.33], -3],
    [-9, [0.33], -3],
    [1, [2.2, 0.5], 1],
    [100, [0.25, 0.2], 5],
]


@pytest.mark.parametrize("start, offsets, result", adjust_float_cases_good)
def test_adjust_float(start: int, offsets: list[int], result: int):
    cp = CoinPurse()
    for cur in cp:
        assert cp.balance(cur) == 0

        for offset in offsets:
            cp.adjust(cur, offset)


adjust_mixed_cases_good = [[1, [1, 2.0], 4]]


@pytest.mark.parametrize("start, offsets, result", adjust_mixed_cases_good)
def test_adjust_mixed(start: int, offsets: list[int], result: int):
    cp = CoinPurse()
    for cur in cp:
        assert cp.balance(cur) == 0

        for offset in offsets:
            cp.adjust(cur, offset)


def test_test_currency():
    cp = CoinPurse()

    assert cp.balance(-110) == 0
    cp.adjust(-110, 100)

    assert cp.test_currency(-110, 1)
    assert cp.test_currency(-110, 0)
    assert not cp.test_currency(-110, 101)


def test_test_currency_keyerror():
    cp = CoinPurse()

    with pytest.raises(KeyError):
        cp.test_currency(-1122213, 1)


def test_test_currency_valueerror():
    cp = CoinPurse()

    with pytest.raises(ValueError):
        cp.test_currency(-110, -1)


test_purchase_cases = [
    [-110, 0, -110, False],
    [-110, 1, -110, False],
    [-110, 2, -110, True],
    [-110, 3, -110, True],
    [-111, 3, -110, True],
    [-111, 4, -110, True],
]


@pytest.mark.parametrize("cur, bal, item, result", test_purchase_cases)
def test_purchase(cur: int, bal: int, item: int, result: bool):
    """
    Test that CoinPurse::test_purchase correctly looks up item costs and returns

    This test specifically makes use of a special test item that was inserted into the item manager during the currency
    test module's setup stage (see __init__.py).
    """
    cp = CoinPurse()

    cp.adjust(cur, bal)
    assert cp.test_purchase(item, cur) == result


def test_purchase_bad():
    pass


test_test_all_purchase_cases = [
    [-110, {-110: 0, -111: 1}, []],
    [-110, {-110: 1, -111: 1}, []],
    [-110, {-110: -19, -111: -1}, []],
    [-110, {-110: -1, -111: 1}, []],
    [-110, {-110: 1, -111: -1}, []],
    [-110, {-110: 2, -111: 1}, [-110]],
    [-110, {-110: 0, -111: 3}, [-111]],
    [-110, {-110: 10, -111: 11}, [-110, -111]],
]


@pytest.mark.parametrize("item, bal, results", test_test_all_purchase_cases)
def test_test_all_purchase(item: int, bal: dict[int, int], results: list[int]):
    cp = CoinPurse()

    for cur in bal:
        cp.adjust(cur, bal[cur])
        assert cp.balance(cur) == bal[cur]

    res = cp.test_all_purchase(item)

    assert len(res) == len(results)  # If lists are of equal size, no need to cross-check
    for element in results:  # Check if function results contain all expected currency ids
        assert element in res


def test_test_all_purchase_bad():
    pass
