from game.cache import from_cache
from game.systems.entity.entities import CombatEntity
from game.systems.item.item import Equipment


def _get_test_entity(equipment: list[int] = None) -> CombatEntity:
    ce = CombatEntity(id=-1, name="Test")

    for item_id in equipment or []:
        instance = from_cache("managers.ItemManager").get_instance(item_id)

        assert isinstance(instance, Equipment)

        ce.equipment_controller.equip(item_id)

    return ce


def _get_equipment(
    slot: str, dmg_buff: int = 0, dmg_res: int = 0, tags: dict[str, float] = None, iid: int = 0, name="Test Equipment"
) -> Equipment:
    e = Equipment(name, iid, {}, "", "", slot, dmg_buff, dmg_res)

    if tags:
        e.tags = tags

    return e


def test_total_res_zero():
    ce = _get_test_entity()

    assert ce.equipment_controller.total_dmg_resistance == 0
    assert len(ce.equipment_controller.all_tag_resistance) == 0


def test_total_dmg_res():
    ce = _get_test_entity([-114, -115])
    res = (
        ce.equipment_controller["ring"].instance.damage_resist + ce.equipment_controller["chest"].instance.damage_resist
    )
    dmg = ce.equipment_controller["ring"].instance.damage_buff + ce.equipment_controller["chest"].instance.damage_buff

    assert ce.equipment_controller.total_dmg_resistance == res
    assert ce.equipment_controller.total_dmg_buff == dmg
