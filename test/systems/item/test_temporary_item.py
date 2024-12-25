from game.systems.item import item_manager
from game.systems.item.item import Item
from ..utils import temporary_item


def test_trivial_temp():
    items = [Item("temp", -256, {-110: 2, -111: 3}, "A simple temporary test Item")]

    with temporary_item(items) as itm:
        assert itm.is_id(-256)
        assert itm.get_ref(-256).name == "temp"

    assert not item_manager.is_id(-256)
