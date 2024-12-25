import pytest

from game.cache import get_config, from_cache
from game.systems.entity.entities import CombatEntity
from systems import TEST_PREFIX

EXPECTED_PRIMARY_RESOURCE = f"{TEST_PREFIX}health"


def _get_intelligent_agent(
    inventory_contents: list[int] = None, abilities: list[str] = None, resource_values: dict[str, int] = None
) -> CombatEntity:
    entity = CombatEntity(name="Test Intelligent Agent", abilities=abilities, naive=False, id=-1)

    if inventory_contents:
        for item_id in inventory_contents:
            entity.inventory.insert_item(item_id, 1)

    if resource_values:
        for resource in resource_values:
            entity.resource_controller[resource].value = resource_values[resource]

    return entity


def test_instantiation():
    _get_intelligent_agent()


is_restorative_items_cases = [[-122, True], [-123, True], [-121, False], [-120, False]]


@pytest.mark.parametrize("item_id, result", is_restorative_items_cases)
def test_is_restorative_item(item_id: int, result: bool):
    inst = from_cache("managers.ItemManager").get_instance(item_id)

    assert CombatEntity._is_restorative_item(inst, EXPECTED_PRIMARY_RESOURCE) == result


# List of Item IDs in, List of expected Item IDs out
restorative_items_cases = [[[-120, -121, -119, -122, -123], [-122, -123]], [[-120], []], [[], []]]


@pytest.mark.parametrize("inventory_contents, expected_items", restorative_items_cases)
def test_restorative_items(inventory_contents: list[int], expected_items: list[int]):
    proper_res_name = get_config()["resources"]["primary_resource"]
    get_config()["resources"]["primary_resource"] = EXPECTED_PRIMARY_RESOURCE

    entity = _get_intelligent_agent(inventory_contents)
    ri = [item.id for item in entity.restorative_items]

    assert set(ri) == set(expected_items)

    get_config()["resources"]["primary_resource"] = proper_res_name


offensive_ability_cases = [
    # For test abilities 1-6, only 1, 2, 4, 5 should pass as offensive abilities
    [[f"{TEST_PREFIX}Ability {i+1}" for i in range(6)], [f"{TEST_PREFIX}Ability {i}" for i in [1, 2, 4, 5]]],
    [[], []],
]


@pytest.mark.parametrize("ability_names, expected_names", offensive_ability_cases)
def test_offensive_abilities(ability_names, expected_names):
    entity = _get_intelligent_agent(abilities=ability_names)

    assert set(expected_names) == set([a.name for a in entity.offensive_abilities])
