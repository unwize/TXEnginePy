import random

from loguru import logger
import pytest

from game.systems.entity.entities import CombatEntity
from game.systems.item import item_manager
from .. import TEST_PREFIX


def test_trivial():
    """
    Test that a modifier can be trivially attached without causing error
    """
    dummy_entity = CombatEntity(0, 0, name="Dummy", id=-110)
    dummy_entity.resource_controller.attach_modifier(item_manager.get_instance(-114))

    dummy_entity.resource_controller.attach_modifier(item_manager.get_instance(-115))
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", int)) == 1


def test_flat_attach():
    dummy_entity = CombatEntity(0, 0, name="Dummy", id=-110)
    tr_health_initial = dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health")

    dummy_entity.resource_controller.attach_modifier(item_manager.get_instance(-115))
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", int)) == 1

    assert (
        dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health")
        == tr_health_initial + item_manager.get_instance(-115).resource_modifiers[f"{TEST_PREFIX}health"]
    )


def test_flat_attach_detach():
    dummy_entity = CombatEntity(0, 0, name="Dummy", id=-110)
    tr_health_initial = dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health")

    e_instance = item_manager.get_instance(-115)

    dummy_entity.resource_controller.attach_modifier(e_instance)
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", int)) == 1

    assert (
        dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health")
        == tr_health_initial + item_manager.get_instance(-115).resource_modifiers[f"{TEST_PREFIX}health"]
    )

    dummy_entity.resource_controller.detach_modifier(e_instance)
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", int)) == 0
    assert dummy_entity.resource_controller.get_max(
        f"{TEST_PREFIX}health"
    ) == dummy_entity.resource_controller.get_base_max(f"{TEST_PREFIX}health")


def test_float_attach_detach():
    dummy_entity = CombatEntity(0, 0, name="Dummy", id=-110)
    tr_health_initial = dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health")

    e_instance = item_manager.get_instance(-116)

    dummy_entity.resource_controller.attach_modifier(e_instance)
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", float)) == 1

    assert dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health") == tr_health_initial + (
        tr_health_initial * e_instance.resource_modifiers[f"{TEST_PREFIX}health"]
    )

    dummy_entity.resource_controller.detach_modifier(e_instance)
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", float)) == 0
    assert dummy_entity.resource_controller.get_max(
        f"{TEST_PREFIX}health"
    ) == dummy_entity.resource_controller.get_base_max(f"{TEST_PREFIX}health")


def test_mixed_attach_detach():
    dummy_entity = CombatEntity(0, 0, name="Dummy", id=-110)
    tr_health_initial = dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health")

    e_instance_int = item_manager.get_instance(-115)
    e_instance_float = item_manager.get_instance(-116)

    dummy_entity.resource_controller.attach_modifier(e_instance_int)
    dummy_entity.resource_controller.attach_modifier(e_instance_float)

    expected_max = (
        tr_health_initial
        + (tr_health_initial * e_instance_float.resource_modifiers[f"{TEST_PREFIX}health"])
        + e_instance_int.resource_modifiers[f"{TEST_PREFIX}health"]
    )

    logger.debug(f"Base max: {tr_health_initial}")
    logger.debug(f"Expected max: {expected_max}")

    assert (
        len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", float))
        == len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", float))
        == 1
    )
    assert dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health") == expected_max

    dummy_entity.resource_controller.detach_modifier(e_instance_float)
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", float)) == 0
    assert len(dummy_entity.resource_controller.get_modifiers(f"{TEST_PREFIX}health", int)) == 1

    assert dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health") == (
        tr_health_initial + e_instance_int.resource_modifiers[f"{TEST_PREFIX}health"]
    )

    dummy_entity.resource_controller.attach_modifier(e_instance_float)
    dummy_entity.resource_controller.detach_modifier(e_instance_int)

    assert dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health") == (
        tr_health_initial + (tr_health_initial * e_instance_float.resource_modifiers[f"{TEST_PREFIX}health"])
    )

    dummy_entity.resource_controller.detach_modifier(e_instance_float)

    assert dummy_entity.resource_controller.get_max(f"{TEST_PREFIX}health") == tr_health_initial


random_attach_detach_cases = [[[i for i in range(-119, -114)], 123456]]


@pytest.mark.parametrize("item_ids, seed", random_attach_detach_cases)
def test_random_attach_detach(item_ids: list[int], seed):
    """
    Verify that resource modifiers can be attached and detached randomly while still following the rules
    """
    dummy_entity = CombatEntity(0, 0, name="Dummy", id=-110)
    resource_mods = {res_name: {"float": 0.0, "int": 0} for res_name in dummy_entity.resource_controller.resources}

    def compute_max(resource_name):
        total = dummy_entity.resource_controller.get_base_max(resource_name)
        total += round(
            dummy_entity.resource_controller.get_base_max(resource_name) * resource_mods[resource_name]["float"]
        )
        total = total + resource_mods[resource_name]["int"]
        return total

    def verify_maxes():
        for res_name in resource_mods:
            assert dummy_entity.resource_controller.get_max(res_name) == compute_max(res_name)

    unused_instances: list = [item_manager.get_instance(i) for i in item_ids]
    used_instances: list = []
    random.seed(seed)

    # Randomly select items to attach and check that the maxes are correct at each step
    while len(unused_instances) > 0:
        index = random.randint(0, len(unused_instances) - 1)  # Select a random index in the unused list
        selected_equipment = unused_instances[index]  # Extract item from list
        del unused_instances[index]

        dummy_entity.resource_controller.attach_modifier(selected_equipment)  # Attach item

        # Record item's mods in the test logic
        for res_name, res_mod in selected_equipment.resource_modifiers.items():
            if type(res_mod) is int:
                resource_mods[res_name]["int"] += res_mod
            elif type(res_mod) is float:
                resource_mods[res_name]["float"] += res_mod
            else:
                raise TypeError("Unexpected resource modifier type")

        used_instances.append(selected_equipment)  # Record item as used

        # Check through all the max values of Entity's resources and verify that they match the predicted values
        verify_maxes()

    while len(used_instances) > 0:
        index = random.randint(0, len(used_instances) - 1)  # Select a random index in the unused list
        selected_equipment = used_instances[index]  # Extract item from list
        del used_instances[index]

        dummy_entity.resource_controller.detach_modifier(selected_equipment)  # Attach item

        # Record item's mods in the test logic
        for res_name, res_mod in selected_equipment.resource_modifiers.items():
            if type(res_mod) is int:
                resource_mods[res_name]["int"] -= res_mod
            elif type(res_mod) is float:
                resource_mods[res_name]["float"] -= res_mod
            else:
                raise TypeError("Unexpected resource modifier type")

        verify_maxes()
