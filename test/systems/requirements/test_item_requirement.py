import pytest

from game.systems.entity.entities import CombatEntity
from game.systems.inventory import InventoryController
from game.systems.requirement.item_requirement import ItemRequirement


def make_inv(items: list[int]) -> InventoryController:
    """Shortcut to create an inventory with a few items in it."""
    inv = InventoryController()
    for item in items:
        inv.insert_item(item, 1)

    return inv


# Keyword arguments for CombatEntity
# requirement instance
# bool whether requirement should be satisfied
cases = [
    [{}, ItemRequirement(item_id=-110, item_quantity=1), False],  # Item Missing
    [{"inventory": make_inv([-110])}, ItemRequirement(-110, 1), True],  # Item of quantity 1 present
    [{"inventory": make_inv([-110])}, ItemRequirement(-110, 2), False],  # Too few
    [{"inventory": make_inv([-111])}, ItemRequirement(-110, 1), False],  # Wrong item
    [{"inventory": make_inv([-110, -110])}, ItemRequirement(-110, 1), True],  # More than needed
    # Precise number across more than 1 stack
    [{"inventory": make_inv([-110 for i in range(16)])}, ItemRequirement(-110, 16), True],
]


@pytest.mark.parametrize("kwargs, requirement, expected", cases)
def test_item_requirement(kwargs: dict, requirement: ItemRequirement, expected: bool):
    ce = CombatEntity(name="TestEntity", id=-1, **kwargs)

    assert requirement.fulfilled(ce) == expected
