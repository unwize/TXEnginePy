import pytest

from game.systems.flag import flag_manager


def test_flag_manager_import():
    assert flag_manager.name is not None


test_no_flag_cases = ["base", "root.branch.leaf", ""]


@pytest.mark.parametrize("flag", test_no_flag_cases)
def test_no_flag(flag: str):
    flag_manager.clear()
    assert not flag_manager.get_flag(flag)


test_get_flag_cases = [
    ["a", False, True],
    ["root.a", False],
    ["root.b", True],
    ["root.c", True],
    ["shop1.features.enabled", False],
    ["shop1.stock.allowed", True],
    ["shop1.enabled", True],
    ["shop1.features.persistent", True],
]


@pytest.mark.parametrize("payload", test_get_flag_cases)
def test_get_flag(payload: list):
    if len(payload) == 3 and payload[2]:
        flag_manager.clear()

    flag_manager.set_flag(payload[0], payload[1])
    assert flag_manager.get_flag(payload[0]) == payload[1]


test_set_flag_blocked_cases = [["store0", False], ["store0.enabled", True], ["store0.props.enabled", True]]


@pytest.mark.parametrize("key, throws", test_set_flag_blocked_cases)
def test_get_flag_bad(key: str, throws: bool):
    if not throws:
        flag_manager.clear()
        flag_manager.set_flag(key, True)

    if throws:
        with pytest.raises(KeyError):
            flag_manager.set_flag(key, True)
