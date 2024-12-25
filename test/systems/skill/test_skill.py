from game.systems.skill.skills import Skill

import pytest


def test_init_trivial():
    sk = Skill(name="SomeSkill", id=0, description="")
    assert sk is not None
    assert sk.level == 1
    assert sk.xp == 0
    assert sk.id == 0
    assert sk.name == "SomeSkill"
    assert sk.level_up_limit == sk.initial_level_up_limit
    assert sk.remaining_xp == sk.level_up_limit


def test_remaining_xp():
    sk = Skill(name="SomeSkill", id=0, description="")
    assert sk.remaining_xp == sk.level_up_limit - sk.xp

    for i in range(sk.remaining_xp):
        sk.xp += 1
        assert sk.remaining_xp == sk.level_up_limit - sk.xp


def test_xp_ceiling():
    sk = Skill(name="SomeSkill", id=0, description="")
    sk.level_up_limit = sk.initial_level_up_limit = 4
    sk.next_level_ratio = 1.5

    assert sk._xp_ceiling(1) == 4
    assert sk._xp_ceiling(2) == 6
    assert sk._xp_ceiling(3) == 9

    sk.force_level_up()
    assert sk.level_up_limit == 6


def test_level_up_trivial():
    """
    Tests that level_up correctly handles a single level-up
    """
    sk = Skill(name="SomeSkill", id=0, description="")
    sk.level_up_limit = sk.initial_level_up_limit = 4
    sk.next_level_ratio = 1.5

    sk.gain_xp(4)

    assert sk.level == 2
    assert sk.xp == 0
    assert sk.level_up_limit == 6


level_up_recursive_cases = [[6, 2, 2], [10, 3, 0], [40, 5, 7]]


@pytest.mark.parametrize("xp, expected_level, leftover_xp", level_up_recursive_cases)
def test_level_up_recursive(xp: int, expected_level: int, leftover_xp: int):
    """
    Tests that level_up correctly handles leveling up multiple levels at once
    """
    sk = Skill(name="SomeSkill", id=0, description="")
    sk.level_up_limit = sk.initial_level_up_limit = 4
    sk.next_level_ratio = 1.5

    sk.gain_xp(xp)
    assert sk.level == expected_level
    assert sk.xp == leftover_xp
