import pytest
from loguru import logger

from game.cache import cache_element, from_cache, delete_element
from game.systems.combat.combat_engine.combat_engine import CombatEngine
from game.systems.combat.combat_engine.phase_handler import PhaseHandler
from game.systems.entity.entities import CombatEntity
from .. import TEST_PREFIX


def get_test_allies() -> list[int]:
    """
    Get a default list of generic ally CombatEntity objects.
    """

    return [-110, -111]


def get_test_enemies() -> list[int]:
    """
    Get a default list of generic enemy CombatEntity objects.
    """
    return [-112, -113]


def get_generic_combat_instance() -> CombatEngine:
    """
    Return a fresh instance of a generic (totally-default) CombatEngine.
    """
    return CombatEngine(get_test_allies(), get_test_enemies())


def test_init_trivial():
    """
    Test that CombatEngine can be instantiated without generating an Error.
    """
    assert get_generic_combat_instance()


def test_self_cache():
    """
    Test that a CombatEngine instance correctly caches a reference to itself on instantiation and purges the reference
    when it is deleted.
    """

    # Ensure that there is no cached combat
    cache_element("combat", None)
    assert from_cache("combat") is None

    # Spawn a new combat session the check that it got cached
    engine = get_generic_combat_instance()
    assert from_cache("combat") == engine

    # Terminate the combat session and verify that it isn't cached anymore
    engine.state_data[engine.States.TERMINATE.value]["logic"](None)
    assert from_cache("combat") is None


def test_duplicate_combats():
    """
    Test that duplicate combat sessions correctly throw an error when spawned
    """

    get_generic_combat_instance()
    with pytest.raises(RuntimeError):
        get_generic_combat_instance()


def test_compute_turn_order():
    """
    Test that CombatEngine correctly determines turn order in a trivial case
    """
    delete_element("combat")

    engine = get_generic_combat_instance()
    engine._compute_turn_order()

    logger.debug([ce.name for ce in engine._turn_order])

    assert engine._turn_order[0].name == f"{TEST_PREFIX}Enemy 2"
    assert engine._turn_order[1].name == f"{TEST_PREFIX}Enemy 1"
    assert engine._turn_order[2].name == f"{TEST_PREFIX}Ally 2"
    assert engine._turn_order[3].name == f"{TEST_PREFIX}Ally 1"
    assert engine._turn_order[4].name == "Player"


def test_active_entity():
    """
    Test that the active entity is the entity whose turn it currently is
    """
    delete_element("combat")

    engine = get_generic_combat_instance()
    engine.set_state(engine.States.START_TURN_CYCLE)  # Skip to state
    engine.input("")  # Run State
    engine.input("")  # Run the following state (START_ENTITY_TURN) to set up engine logic

    for i in range(len(engine._turn_order)):
        assert (
            engine.active_entity.name == engine._turn_order[engine.current_turn].name
        )  # Active entity should be the fastest entity
        engine.current_turn += 1


def test_phase_handle_triggers():
    delete_element("combat")

    # A ridiculous PhaseHandler that serves to communicate that it was run via an error
    class DebugHandler(PhaseHandler):
        def __init__(self):
            super().__init__()

        # Trigger a runtime error so it can be detected during testing
        def _phase_logic(self) -> None:
            raise RuntimeError("You should have expected this!")

    engine = get_generic_combat_instance()
    engine.set_state(engine.States.START_TURN_CYCLE)  # Skip to state
    engine.input("")  # Run State
    engine.input("")  # Run the following state (START_ENTITY_TURN) to set up engine logic

    for phase in engine.PHASE_HANDLERS:
        engine.PHASE_HANDLERS[phase].append(DebugHandler)

    # Call the HANDLE_PHASE state logic by hand
    with pytest.raises(RuntimeError):
        engine.state_data[engine.States.HANDLE_PHASE.value]["logic"]("")


def test_get_relative_enemies():
    delete_element("combat")

    engine = get_generic_combat_instance()
    allies = engine._allies
    enemies = engine._enemies

    # Check for each absolute enemy, they are included in a relative list of enemies to an absolute ally
    for enemy in enemies:
        assert enemy in engine.get_relative_enemies(allies[0])

    # Check for each absolute ally, they are included in a relative list of enemies to an absolute enemy
    for ally in allies:
        assert ally in engine.get_relative_enemies(enemies[0])


def test_get_relative_allies():
    delete_element("combat")

    engine = get_generic_combat_instance()
    allies = engine.allies
    enemies = engine.enemies

    # Check for each absolute enemy, they are included in a relative list of allies to an absolute ally
    for enemy in enemies:
        assert enemy in engine.get_relative_allies(enemies[0])

    # Check for each absolute ally, they are included in a relative list of allies to an absolute ally
    for ally in allies:
        assert ally in engine.get_relative_allies(allies[0])


test_get_target_single_cases = [
    ["ABSOLUTE_ALLY", f"{TEST_PREFIX}Ability 1", "ANY"],
    ["ABSOLUTE_ALLY", f"{TEST_PREFIX}Ability 2", "ABSOLUTE_ENEMY"],
    ["ABSOLUTE_ALLY", f"{TEST_PREFIX}Ability 3", "ABSOLUTE_ALLY"],
    ["ABSOLUTE_ENEMY", f"{TEST_PREFIX}Ability 1", "ANY"],
    ["ABSOLUTE_ENEMY", f"{TEST_PREFIX}Ability 2", "ABSOLUTE_ALLY"],
    ["ABSOLUTE_ENEMY", f"{TEST_PREFIX}Ability 3", "ABSOLUTE_ENEMY"],
]


@pytest.mark.parametrize("source_entity_type, ability, valid_targets", test_get_target_single_cases)
def test_get_target_single(source_entity_type: str, ability: str, valid_targets: str):
    delete_element("combat")

    engine = get_generic_combat_instance()
    allies: list[CombatEntity] = engine.allies
    enemies: list[CombatEntity] = engine.enemies

    def translate_target_str(target_type: str) -> list[CombatEntity]:
        match target_type:
            case "ABSOLUTE_ALLY":
                return allies
            case "ABSOLUTE_ENEMY":
                return enemies
            case "ANY":
                return allies + enemies
            case _:
                raise RuntimeError("No such group")

    for entity in engine.get_valid_ability_targets(translate_target_str(source_entity_type)[0], ability):
        assert entity in translate_target_str(valid_targets)


test_get_target_group_cases = [
    ["ABSOLUTE_ALLY", f"{TEST_PREFIX}Ability 4", "ALL"],
    ["ABSOLUTE_ALLY", f"{TEST_PREFIX}Ability 5", "ABSOLUTE_ENEMY"],
    ["ABSOLUTE_ALLY", f"{TEST_PREFIX}Ability 6", "ABSOLUTE_ALLY"],
    ["ABSOLUTE_ENEMY", f"{TEST_PREFIX}Ability 4", "ALL"],
    ["ABSOLUTE_ENEMY", f"{TEST_PREFIX}Ability 5", "ABSOLUTE_ALLY"],
    ["ABSOLUTE_ENEMY", f"{TEST_PREFIX}Ability 6", "ABSOLUTE_ENEMY"],
]


@pytest.mark.parametrize("source_entity_type, ability, valid_group", test_get_target_group_cases)
def test_get_target_group(source_entity_type, ability, valid_group):
    delete_element("combat")

    engine = get_generic_combat_instance()
    allies: list[CombatEntity] = engine.allies
    enemies: list[CombatEntity] = engine.enemies

    def translate_target_str(target_type: str) -> list[CombatEntity]:
        match target_type:
            case "ABSOLUTE_ALLY":
                return allies
            case "ABSOLUTE_ENEMY":
                return enemies
            case "ALL":
                return allies + enemies
            case _:
                raise RuntimeError("No such group")

    resulting_group = engine.get_valid_ability_targets(translate_target_str(source_entity_type)[0], ability)

    expected_group = translate_target_str(valid_group)

    # Check that all returned entities are in the expected group
    assert all([(ent in expected_group) for ent in resulting_group])

    # Check that all expected entities are in the returned group
    assert all([(ent in resulting_group) for ent in expected_group])
