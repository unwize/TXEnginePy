from game.cache import from_cache
from game.systems.entity import Resource
from game.systems.entity.entities import CombatEntity
from .. import TEST_PREFIX


def test_player_get_item():
    player_ref = from_cache("player")

    resources = ["Health", "Stamina", "Mana"]

    for res in resources:
        assert type(player_ref.resource_controller[res]) is Resource


def test_entity_get_item():
    for entity in from_cache("managers.EntityManager")._manifest.values():
        if isinstance(entity, CombatEntity):
            if entity.name.startswith(TEST_PREFIX):
                for resource in from_cache("managers.ResourceManager")._manifest:
                    assert type(entity.resource_controller[resource]) is Resource
