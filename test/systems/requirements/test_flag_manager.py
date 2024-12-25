import pytest

from game.cache import from_cache
from game.systems.flag import FlagManager
from game.systems.requirement.requirements import FlagRequirement

flag_cases = [[True, True, True], [False, False, True], [True, False, False], [False, True, False]]


@pytest.mark.parametrize("actual, expected, result", flag_cases)
def test_flag(actual: bool, expected: bool, result: bool):
    """
    Test if FlagRequirement yields the correct value for a matrix of given
    expected/given flag values
    Args:
        actual: The actual value to set the flag to
        expected: The value the flag is expected to hold
        result: The value expected to be yielded by the FlagRequirement

    Returns: None

    """
    fm: FlagManager = from_cache("managers.FlagManager")
    fm.set_flag("test", actual)

    req = FlagRequirement("test", "A test flag", expected)

    assert req.fulfilled(None) == result
