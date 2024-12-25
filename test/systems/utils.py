from contextlib import contextmanager
from typing import Iterable

from loguru import logger

from game.systems.item import ItemManager
from game.systems.item.item import Item
from game.systems.entity import EntityManager
from game.systems.entity.entities import CombatEntity
from game.systems.combat import Ability, AbilityManager


@contextmanager
def temporary_item(items: Iterable[Item]) -> ItemManager:
    """
    A context manager that temporarily registers a collection of Item objects
    with the global ItemManager instance and then deletes them when the scope
    exits.
    """
    from game.systems.item import item_manager

    for item in items:
        logger.debug(f"Temporarily registering item with id: {item.id}")
        item_manager.register_item(item)

    try:
        yield item_manager

    finally:
        # In order to "safely" delete items from the manager, check that the
        # Item registered to that ID has the same name as the temporary Item.
        # This way, an exit that occurs due to a collision doesn't break the
        # Item Manager

        for item in items:
            # Make sure item ID exists in manager
            if item_manager.is_id(item.id):
                # Make sure items are the same
                if item_manager.get_ref(item.id).name == item.name:
                    # Delete from the manager permanently
                    del item_manager._manifest[item.id]
                    logger.debug(f"De-registering item with id: {item.id}")


@contextmanager
def temporary_entity(entities: Iterable[CombatEntity]) -> EntityManager:
    """
    A context manager that temporarily registers a collection of Entity objects
    with the global EntityManager instance and then deletes them when the scope
    exits.
    """

    from game.systems.entity import entity_manager

    for entity in entities:
        entity_manager.register_entity(entity)

    try:
        yield entity_manager

    finally:
        # In order to "safely" delete entities from the manager, check that the
        # Entity registered to that ID has the same name as the temporary Entity
        # This way, an exit that occurs due to a collision doesn't break the
        # EntityManager

        for entity in entities:
            # Make sure item ID exists in manager
            if entity_manager.is_id(entity.id):
                # Make sure items are the same
                if entity_manager.get_instance(entity.id).name == entity.name:
                    # Delete from the manager permanently
                    del entity_manager._manifest[entity.id]


@contextmanager
def temporary_ability(abilities: Iterable[Ability]) -> AbilityManager:
    """
    A context manager that temporarily registers a collection of Ability objects
    with the global AbilityManager instance and then deletes them when the scope
    exits.
    """

    from game.systems.combat import ability_manager

    for ability in abilities:
        ability_manager.register_ability(ability)

    try:
        yield ability_manager

    finally:
        for ability in abilities:
            # Make sure item ID exists in manager
            if ability_manager.is_id(ability.name):
                # Delete from the manager permanently
                del ability_manager._manifest[ability.name]
