import copy

import pytest

from game.systems.combat.effect import ResourceEffect
from game.systems.entity.entities import CombatEntity

from .. import TEST_PREFIX

dummy_entity = CombatEntity(id=-1, name="dummy")


def test_init_trivial():
    re = ResourceEffect(f"{TEST_PREFIX}health", -10, "Some text")

    assert re._resource_name == f"{TEST_PREFIX}health"
    assert re._adjust_quantity == -10
    assert re.trigger_message == "Some text"


perform_cases_single_int = [
    ResourceEffect(f"{TEST_PREFIX}health", -2),
    ResourceEffect(f"{TEST_PREFIX}health", 3),
    ResourceEffect(f"{TEST_PREFIX}stamina", -11),
    ResourceEffect(f"{TEST_PREFIX}stamina", 4),
    ResourceEffect(f"{TEST_PREFIX}mana", -100),
    ResourceEffect(f"{TEST_PREFIX}mana", 600),
]


@pytest.mark.parametrize("resource_effect", perform_cases_single_int)
def test_perform_single_int(resource_effect: ResourceEffect):
    res_name = resource_effect._resource_name
    source_tce = copy.deepcopy(dummy_entity)
    target_tce = copy.deepcopy(dummy_entity)
    RES_START_VALUE = 15
    target_tce.resource_controller[res_name].value = RES_START_VALUE
    resource_effect.assign(source_tce, target_tce)

    assert resource_effect._target_entity == target_tce
    assert target_tce.resource_controller[resource_effect._resource_name].value == RES_START_VALUE

    resource_effect.perform()

    assert target_tce.resource_controller[resource_effect._resource_name].value == min(
        max(RES_START_VALUE + resource_effect._adjust_quantity, 0), target_tce.resource_controller[res_name].max
    )


perform_cases_multiple_int = [
    [
        [ResourceEffect(f"{TEST_PREFIX}health", -2), ResourceEffect(f"{TEST_PREFIX}health", 3)],
        {f"{TEST_PREFIX}health": 1},
    ],
    [
        [ResourceEffect(f"{TEST_PREFIX}stamina", -11), ResourceEffect(f"{TEST_PREFIX}stamina", 4)],
        {f"{TEST_PREFIX}stamina": -7},
    ],
    [[ResourceEffect(f"{TEST_PREFIX}mana", -4), ResourceEffect(f"{TEST_PREFIX}mana", 6)], {f"{TEST_PREFIX}mana": 2}],
    [
        [ResourceEffect(f"{TEST_PREFIX}mana", -4), ResourceEffect(f"{TEST_PREFIX}health", 6)],
        {f"{TEST_PREFIX}mana": -4, f"{TEST_PREFIX}health": 6},
    ],
    [
        [
            ResourceEffect(f"{TEST_PREFIX}mana", -4),
            ResourceEffect(f"{TEST_PREFIX}mana", 6),
            ResourceEffect(f"{TEST_PREFIX}stamina", 3),
        ],
        {f"{TEST_PREFIX}mana": 2, f"{TEST_PREFIX}stamina": 3},
    ],
]


@pytest.mark.parametrize("resource_effects, net_res_changes", perform_cases_multiple_int)
def test_perform_multiple_int(resource_effects: list[ResourceEffect], net_res_changes: dict[str, int]):
    """
    Test that multiple consecutive ResourceEffect triggers resolve correctly.
    """

    # Set up source and target entities
    source_tce = copy.deepcopy(dummy_entity)
    target_tce = copy.deepcopy(dummy_entity)

    RESOURCE_BASE_VALUE = 15  # The value that each resource will start at
    for res in net_res_changes:
        target_tce.resource_controller[res].value = RESOURCE_BASE_VALUE

    for res in net_res_changes:
        assert target_tce.resource_controller[res].value == RESOURCE_BASE_VALUE

    # Execute effects in series and measure correctness at each step
    for effect in resource_effects:
        res_name = effect._resource_name
        starting_res_value = target_tce.resource_controller[res_name].value  # Value before execution
        effect.assign(source_tce, target_tce)
        effect.perform()  # Execution
        assert target_tce.resource_controller[res_name].value == min(
            max(0, starting_res_value + effect._adjust_quantity), target_tce.resource_controller[res_name].max
        )

    # For each resource modified, ensure that its final value conforms with the predicted differences
    for res in net_res_changes:
        assert target_tce.resource_controller[res].value - RESOURCE_BASE_VALUE == net_res_changes[res]


perform_cases_single_float = [
    ResourceEffect(f"{TEST_PREFIX}health", 0.1),  # +10%
    ResourceEffect(f"{TEST_PREFIX}health", -0.1),  # -10%
    ResourceEffect(f"{TEST_PREFIX}stamina", -0.33),  # -33%
    ResourceEffect(f"{TEST_PREFIX}stamina", 0.3),  # +30%
    ResourceEffect(f"{TEST_PREFIX}mana", -1.0),  # -100%  # Tests min enforcement
    ResourceEffect(f"{TEST_PREFIX}mana", 1.0),  # + 100% : Tests max enforcement
]


@pytest.mark.parametrize("resource_effect", perform_cases_single_float)
def test_perform_single_float(resource_effect: ResourceEffect):
    res_name = resource_effect._resource_name
    source_tce = copy.deepcopy(dummy_entity)
    target_tce = copy.deepcopy(dummy_entity)
    RES_START_VALUE = 15
    target_tce.resource_controller[res_name].value = RES_START_VALUE
    resource_effect.assign(source_tce, target_tce)

    assert resource_effect._target_entity == target_tce
    assert target_tce.resource_controller[resource_effect._resource_name].value == RES_START_VALUE

    resource_effect.perform()

    assert target_tce.resource_controller[resource_effect._resource_name].value == min(
        max(
            0,
            round(RES_START_VALUE + (target_tce.resource_controller[res_name].max * resource_effect._adjust_quantity)),
        ),
        target_tce.resource_controller[res_name].max,
    )


perform_cases_multiple_float = [
    [  # Cancel out
        ResourceEffect(f"{TEST_PREFIX}health", 0.2),
        ResourceEffect(f"{TEST_PREFIX}health", -0.2),
    ],
    [ResourceEffect(f"{TEST_PREFIX}stamina", -0.2), ResourceEffect(f"{TEST_PREFIX}stamina", 0.5)],
    [ResourceEffect(f"{TEST_PREFIX}mana", -1.0), ResourceEffect(f"{TEST_PREFIX}mana", 1.0)],
    [ResourceEffect(f"{TEST_PREFIX}mana", -0.5), ResourceEffect(f"{TEST_PREFIX}health", 0.2)],
    [
        ResourceEffect(f"{TEST_PREFIX}mana", -0.33),
        ResourceEffect(f"{TEST_PREFIX}mana", 0.2),
        ResourceEffect(f"{TEST_PREFIX}stamina", 0.33),
    ],
]


@pytest.mark.parametrize("resource_effects", perform_cases_multiple_float)
def test_perform_multiple_float(resource_effects: list[ResourceEffect]):
    """
    Test that multiple consecutive ResourceEffect triggers resolve correctly.
    """

    net_res_changes: dict[str, float] = {}  # Net change for each resource represented in float form

    for res_effect in resource_effects:
        if res_effect._resource_name not in net_res_changes:
            net_res_changes[res_effect._resource_name] = res_effect._adjust_quantity
        else:
            net_res_changes[res_effect._resource_name] += res_effect._adjust_quantity

    # Set up source and target entities
    source_tce = copy.deepcopy(dummy_entity)
    target_tce = copy.deepcopy(dummy_entity)

    RESOURCE_BASE_VALUE = 15  # The value that each resource will start at
    for res in net_res_changes:
        target_tce.resource_controller[res].value = RESOURCE_BASE_VALUE

    # Execute effects in series and measure correctness at each step
    for effect in resource_effects:
        res_name = effect._resource_name
        starting_res_value = target_tce.resource_controller[res_name].value  # Value before execution
        effect.assign(source_tce, target_tce)
        effect.perform()  # Execution
        assert target_tce.resource_controller[res_name].value == min(
            target_tce.resource_controller[res_name].max,
            max(
                0, round(starting_res_value + (target_tce.resource_controller[res_name].max * effect._adjust_quantity))
            ),
        )  # Verify


fsm_int_cases = []


# Interface not finalized, so tests not written
@pytest.mark.parametrize("resource_effect, expected_resource_value", fsm_int_cases)
def test_fsm_int(resource_effect: ResourceEffect, expected_resource_value: int):
    pass


fsm_float_cases = []


# Interface not finalized, so tests not written
@pytest.mark.parametrize("resource_effect, expected_resource_value", fsm_float_cases)
def test_fsm_float(resource_effect: ResourceEffect, expected_resource_value: int):
    pass
