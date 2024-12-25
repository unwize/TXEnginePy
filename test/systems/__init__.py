from loguru import logger

from game.structures.enums import TargetMode
from game.systems.crafting.recipe import Recipe
from game.systems.currency import currency_manager, Currency
from game.systems.entity import Resource
from game.systems.entity.entities import CombatEntity
from game.systems.event import ResourceEvent
from game.systems.item.item import Item, Equipment, Usable
from game.systems.item import item_manager
from game.systems.crafting import recipe_manager
from game.systems.entity import entity_manager
from game.systems.combat import ability_manager, Ability
from game.systems.requirement.requirements import ResourceRequirement

TEST_PREFIX = "_tr_"


def pre_collect_setup():
    """
    Run some setup code that MUST be run before PyTest attempts to collect tests
     from the files in this directory and
    its subdirectories.

    This particular pre_collect_setup registering important mock items with
    global backend systems so that they can be
    initialized within the parameters of parameterized tests.
    """
    logger.info("Setting up test currencies...")

    currency_manager.register_currency(Currency(-110, "USD", {"cents": 1, "dollars": 100}))

    currency_manager.register_currency(Currency(-111, "Imperial", {"bronze": 1, "silver": 1000, "gold": 1000000}))

    logger.info("Setting up test items...")
    te1 = Item(f"{TEST_PREFIX} Item 1", -110, "A simple test item", 3, market_values={-110: 2, -111: 3})
    te2 = Item(f"{TEST_PREFIX} Item 2", -111, "A simple test item", 3)
    te3 = Item(f"{TEST_PREFIX} Item 3", -112, "A simple test item", 3)
    te4 = Item(f"{TEST_PREFIX} Item 4", -113, "Another test item", 3)

    te5 = Equipment(f"{TEST_PREFIX} Equipment 1", -114, "", "ring", "ring", 3, 3)
    te6 = Equipment(
        f"{TEST_PREFIX} Equipment 2", -115, "", "chest", "chest", 5, 5, resource_modifiers={f"{TEST_PREFIX}health": 3}
    )
    te7 = Equipment(
        f"{TEST_PREFIX} Equipment 3", -116, "", "legs", "legs", 0, 0, resource_modifiers={f"{TEST_PREFIX}health": 0.1}
    )
    te8 = Equipment(
        f"{TEST_PREFIX} Equipment 4", -117, "", "legs", "legs", 0, 0, resource_modifiers={f"{TEST_PREFIX}health": 0.1}
    )
    te9 = Equipment(
        f"{TEST_PREFIX} Equipment 5", -118, "", "legs", "legs", 0, 0, resource_modifiers={f"{TEST_PREFIX}health": -1}
    )
    te10 = Equipment(
        f"{TEST_PREFIX} Equipment 6", -119, "", "legs", "legs", 0, 0, resource_modifiers={f"{TEST_PREFIX}health": -0.25}
    )

    te11 = Usable(
        f"{TEST_PREFIX} Usable 1", -120, "", "", requirements=[ResourceRequirement(f"{TEST_PREFIX}health", 0.2)]
    )
    te12 = Usable(
        f"{TEST_PREFIX} Usable 2", -121, "", "", requirements=[ResourceRequirement(f"{TEST_PREFIX}health", 5)]
    )

    te13 = Usable(f"{TEST_PREFIX} Usable 3", -122, "", "", on_use_events=[ResourceEvent(f"{TEST_PREFIX}health", 0.2)])

    te14 = Usable(f"{TEST_PREFIX} Usable 4", -123, "", "", on_use_events=[ResourceEvent(f"{TEST_PREFIX}health", 5)])

    # test_select_element_event depends on this
    te15 = Usable(f"{TEST_PREFIX} Usable 4", -124, "", "", on_use_events=[ResourceEvent(f"{TEST_PREFIX}health", 3)])

    item_manager.register_item([te1, te2, te3, te4, te5, te6, te7, te8, te9, te10, te11, te12, te13, te14, te15])

    logger.info("Setting up test recipes...")
    tr1 = Recipe(-110, [(-110, 1)], [(-111, 1)])
    tr2 = Recipe(-111, [(-111, 1)], [(-110, 1)])
    tr3 = Recipe(-112, [(-110, 2)], [(-111, 1)])  # Even input, single
    tr4 = Recipe(-113, [(-111, 3)], [(-112, 1)])  # Odd input, single
    tr5 = Recipe(-114, [(-110, 2), (-111, 3), (-112, 1)], [(-113, 2)])  # Mixed input, multi

    recipe_manager.register_recipe(tr1)
    recipe_manager.register_recipe(tr2)
    recipe_manager.register_recipe(tr3)
    recipe_manager.register_recipe(tr4)
    recipe_manager.register_recipe(tr5)

    logger.info("Setting up resources...")
    from game.systems.entity import resource_manager

    tr_health = Resource(f"{TEST_PREFIX}health", 40, "Needed to live")
    tr_sta = Resource(f"{TEST_PREFIX}stamina", 35, "Tired without it")
    tr_mana = Resource(f"{TEST_PREFIX}mana", 50, "Magic-dependant")

    resource_manager.register_resource(tr_sta)
    resource_manager.register_resource(tr_mana)
    resource_manager.register_resource(tr_health)

    logger.info("Setting up test abilities...")

    ta_1 = Ability(
        name=f"{TEST_PREFIX}Ability 1", description="ta_1", on_use="ta_1 used", target_mode=TargetMode.SINGLE, damage=1
    )
    ta_2 = Ability(
        name=f"{TEST_PREFIX}Ability 2",
        description="ta_2",
        on_use="ta_2 used",
        target_mode=TargetMode.SINGLE_ENEMY,
        damage=1,
        costs={f"{TEST_PREFIX}health": 1},
    )
    ta_3 = Ability(
        name=f"{TEST_PREFIX}Ability 3",
        description="ta_3",
        on_use="ta_3 used",
        target_mode=TargetMode.SINGLE_ALLY,
        costs={f"{TEST_PREFIX}stamina": 2},
    )
    ta_4 = Ability(
        name=f"{TEST_PREFIX}Ability 4", description="ta_1", on_use="ta_1 used", target_mode=TargetMode.ALL, damage=1
    )
    ta_5 = Ability(
        name=f"{TEST_PREFIX}Ability 5",
        description="ta_2",
        on_use="ta_2 used",
        target_mode=TargetMode.ALL_ENEMY,
        costs={f"{TEST_PREFIX}health": 1},
        damage=1,
    )
    ta_6 = Ability(
        name=f"{TEST_PREFIX}Ability 6",
        description="ta_3",
        on_use="ta_3 used",
        target_mode=TargetMode.ALL_ALLY,
        costs={f"{TEST_PREFIX}stamina": 2},
    )

    ability_manager.register_ability(ta_1)
    ability_manager.register_ability(ta_2)
    ability_manager.register_ability(ta_3)
    ability_manager.register_ability(ta_4)
    ability_manager.register_ability(ta_5)
    ability_manager.register_ability(ta_6)

    logger.info("Setting up test entities...")
    test_entity_no_abilities = CombatEntity(name="Entity: No Abilities", id=-109, turn_speed=0)
    te_ally_1 = CombatEntity(name=f"{TEST_PREFIX}Ally 1", id=-110, turn_speed=2)
    te_ally_2 = CombatEntity(name=f"{TEST_PREFIX}Ally 2", id=-111, turn_speed=3)
    te_enemy_1 = CombatEntity(name=f"{TEST_PREFIX}Enemy 1", id=-112, turn_speed=4)
    te_enemy_2 = CombatEntity(name=f"{TEST_PREFIX}Enemy 2", id=-113, turn_speed=5)

    entity_manager.register_entity(te_ally_1)
    entity_manager.register_entity(te_ally_2)
    entity_manager.register_entity(te_enemy_1)
    entity_manager.register_entity(te_enemy_2)

    # For each ability, teach it to each entity
    assert len(ability_manager._manifest) > 0
    for ability in ability_manager._manifest:
        # Skip any non-testing abilities that might have gotten into the mix
        if not ability.startswith(TEST_PREFIX):
            continue

        for entity in entity_manager._manifest.values():
            if isinstance(entity, CombatEntity):
                entity.ability_controller.learn(ability)

    # Register late to avoid giving it abilities
    entity_manager.register_entity(test_entity_no_abilities)


pre_collect_setup()
