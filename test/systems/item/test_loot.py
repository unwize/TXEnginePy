from game.systems.entity.entities import CombatEntity
from game.systems.item.loot import LootTable


def test_loot_table_trivial():
    lt = LootTable(-1, {-110: 1.0}, {1: 1.0})
    assert len(lt.item_table) == LootTable.ITEM_TABLE_RESOLUTION
    assert len(lt.drop_table) == LootTable.DROP_TABLE_RESOLUTION


def test_loot_table_get_loot():
    i_prob = {
        -110: 0.33,
        -111: 0.33,
        -112: 0.34,
    }

    d_prob = {1: 1.0}

    lt = LootTable(-1, item_probabilities=i_prob, drop_probabilities=d_prob)
    assert len(lt.item_table) == LootTable.ITEM_TABLE_RESOLUTION
    assert len(lt.drop_table) == LootTable.DROP_TABLE_RESOLUTION


def test_lootable_mixin_trivial():
    i_prob = {
        -110: 0.33,
        -111: 0.33,
        -112: 0.34,
    }

    d_prob = {1: 1.0}
    sl = CombatEntity(id=-1, name="TestEntity", item_probabilities=i_prob, drop_probabilities=d_prob)

    assert type(sl.loot_table) is LootTable
    assert len(sl.loot_table.item_table) == LootTable.ITEM_TABLE_RESOLUTION
    assert sum(sl.loot_table.drop_table) == LootTable.DROP_TABLE_RESOLUTION * 1.0

    assert len(sl.get_loot().keys()) == 1  # Technically non-deterministic, but should really always be 1
