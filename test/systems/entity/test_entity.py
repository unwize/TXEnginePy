import pytest

from game.systems.entity import Entity
from game.systems.entity.entities import EntityBase
from game.systems.inventory import InventoryController


def test_init_trivial():
    e = Entity(name="Test", id=-1)
    assert e
    assert isinstance(e, EntityBase)
    assert e.name == "Test"
    assert e.id == -1
    assert e.inventory is not None
    assert e.coin_purse is not None


init_kwargs_cases = [{"inventory": InventoryController(16, [(-110, 1)])}]


@pytest.mark.parametrize("kwargs", init_kwargs_cases)
def test_init_kwargs(kwargs):
    e = Entity(name="Test", id=1, **kwargs)
    assert e


def test_load():
    j = """
    {
        "class": "Entity",
        "name": "Test",
        "id": 1,
        "inventory": {
            "class": "InventoryController",
            "capacity": 16,
            "manifest": [
                [
                    -110,
                    1
                ],
                [
                    -111,
                    2
                ]
            ]
        },
        "coin_purse": {
            "class": "CoinPurse",
            "currencies": [
                {
                    "id": -110,
                    "quantity": 300
                },
                {
                    "id": -111,
                    "quantity": 231
                }
            ]
        }
    }
    """

    import json

    j_data = json.loads(j)
    e: Entity = Entity.from_json(j_data)
    assert e
    assert e.name == "Test"
    assert e.id == 1
    assert len(e.inventory) == 2
    assert -110 in e.inventory
    assert -111 in e.inventory
    assert e.coin_purse.balance(-110) == 300
    assert e.coin_purse.balance(-111) == 231
