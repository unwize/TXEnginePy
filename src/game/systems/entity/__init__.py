from game.systems.entity.entities import Entity, Player
from game.systems.entity.resource import Resource
from game.systems.entity.resource_manager import ResourceManager
from game.systems.entity.entity_manager import EntityManager

resource_manager: ResourceManager = ResourceManager()
entity_manager: EntityManager = EntityManager()

__all__ = ["Entity", "Player", "Resource", "resource_manager", "entity_manager"]
