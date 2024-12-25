import pytest

from game.systems.crafting.crafting_controller import CraftingController
from game.systems.entity import Player
from game.systems.inventory import InventoryController


def test_init_trivial():
    cc = CraftingController()
    assert cc is not None


manifest_cases = [[], [-110], [-110, -111, -112, -113, -114]]


@pytest.mark.parametrize("manifest", manifest_cases)
def test_init_manifest(manifest: list[int]):
    cc = CraftingController(manifest)

    for recipe in manifest:
        assert recipe in cc.learned_recipes


def test_owner():
    p = Player(
        name="Crafty Boy", id=1, inventory=InventoryController(items=[(-110, 1), (-111, 2)]), recipes=[-110, -111]
    )

    assert hasattr(p, "crafting_controller")
    assert p.crafting_controller.owner == p


def test_has_sufficient_ingredients():
    p = Player(
        name="Crafty Boy", id=1, inventory=InventoryController(items=[(-110, 1), (-111, 2)]), recipes=[-110, -111]
    )

    assert p.inventory.total_quantity(-110) == 1
    assert p.inventory.total_quantity(-111) == 2
    assert -110 in p.crafting_controller.learned_recipes
    assert -111 in p.crafting_controller.learned_recipes

    assert p.crafting_controller.has_sufficient_ingredients(-110)
    assert p.crafting_controller.has_sufficient_ingredients(-111)


max_crafts_cases = [
    [-112, [(-110, 2)], 1],  # Exact
    [-112, [(-110, 3)], 1],  # Odd offset
    [-112, [], 0],  # Missing
    [-112, [(-110, 1)], 0],  # Insufficient
    [-113, [(-111, 3)], 1],
    [-113, [(-111, 2)], 0],
    [-113, [(-111, 4)], 1],
    [-114, [(-110, 2), (-111, 3), (-112, 1)], 1],  # Exact
    [-114, [(-110, 2), (-111, 3), (-112, 2)], 1],  # Exact 2, offset 1
    [-114, [(-110, 2), (-111, 6), (-112, 1)], 1],  # Exact 2, double 1
    [-114, [(-110, 11), (-111, 3), (-112, 1)], 1],  # Exact 2, huge offset 1
    [-114, [(-110, 2), (-111, 3)], 0],  # Exact 2, missing 1
    [-114, [(-110, 7), (-111, 9), (-112, 3)], 3],  # Triple 2, triple offset 1
]


@pytest.mark.parametrize("recipe_id, inventory_contents, results", max_crafts_cases)
def test_max_crafts(recipe_id: int, inventory_contents: list[tuple[int, int]], results: int):
    p = Player(name="Crafty Boy", id=1, inventory=InventoryController(items=inventory_contents), recipes=[-110, -111])

    assert p.crafting_controller.get_max_crafts(recipe_id) == results
