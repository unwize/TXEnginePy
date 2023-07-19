import pytest
from loguru import logger

from game.cache import cache_element, from_cache, delete_element
from game.systems.combat.combat_engine.combat_engine import CombatEngine
from game.systems.combat.combat_engine.phase_handler import PhaseHandler
from game.systems.entity.entities import CombatEntity


def get_test_allies() -> list[int]:
    """
    Get a default list of generic ally CombatEntity objects.
    """

    return [
        -110
    ]


def get_test_enemies() -> list[int]:
    """
    Get a default list of generic enemy CombatEntity objects.
    """
    return [
        -111
    ]


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
    engine.state_data[engine.States.TERMINATE.value]['logic'](None)
    assert from_cache("combat") is None


def test_duplicate_combats():
    """
    Test that duplicate combat sessions correctly throw an error when spawned
    """

    engine = get_generic_combat_instance()
    with pytest.raises(RuntimeError):
        engine2 = get_generic_combat_instance()


def test_compute_turn_order():
    """
    Test that CombatEngine correctly determines turn order in a trivial case
    """
    delete_element("combat")

    engine = get_generic_combat_instance()
    engine._compute_turn_order()

    logger.debug([ce.name for ce in engine._turn_order])

    assert engine._turn_order[0].name == "Test Enemy"
    assert engine._turn_order[1].name == "Test Ally"
    assert engine._turn_order[2].name == "Player"


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
        assert engine.active_entity.name == engine._turn_order[
            engine.current_turn].name  # Active entity should be the fastest entity
        engine.current_turn += 1


def test_phase_handle_triggers():
    delete_element("combat")

    # A ridiculous PhaseHandler that serves to communicate that it was run via an error
    class DebugHandler(PhaseHandler):
        def __init__(self):
            super().__init__()

        # Trigger a runtime error so it can be detected during testing
        def _phase_logic(self, combat_engine) -> None:
            logger.debug(f"PhaseHandler::{combat_engine.current_phase.name} called!")
            raise RuntimeError("You should have expected this!")

    engine = get_generic_combat_instance()
    engine.set_state(engine.States.START_TURN_CYCLE)  # Skip to state
    engine.input("")  # Run State
    engine.input("")  # Run the following state (START_ENTITY_TURN) to set up engine logic

    for phase in engine.PHASE_HANDLERS:
        engine.PHASE_HANDLERS[phase].append(DebugHandler)

    # Call the HANDLE_PHASE state logic by hand
    with pytest.raises(RuntimeError):
        engine.state_data[engine.States.HANDLE_PHASE.value]['logic']("")
