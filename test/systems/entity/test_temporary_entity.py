from game.systems.entity.entities import CombatEntity
from ..utils import temporary_entity


def test_temp_entity_trivial():
    e = CombatEntity(name="Temp", id=-256)

    with temporary_entity([e]) as entity_manager:
        assert entity_manager.is_id(-256)
        assert entity_manager[-256].id == -256

    from game.systems.entity import entity_manager

    assert not entity_manager.is_id(-256)
