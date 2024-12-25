from game.systems.entity.entities import CombatEntity, Entity
from game.systems.entity.mixins.equipment_mixin import EquipmentMixin
from game.systems.entity.mixins.ability_mixin import AbilityMixin

import pytest


def test_init_trivial():
    ce = CombatEntity(name="CombatEntity", id=-1)

    required_types = [AbilityMixin, EquipmentMixin, Entity]
    for cls in required_types:
        assert isinstance(ce, cls)


init_kwargs_cases = [
    {
        "name": "Proto Combat Entity",
        "id": 9999,
    },
    {
        "name": "TCE",
        "id": 1,
        "xp_yield": 10,
        "turn_speed": 2,
    },
]


@pytest.mark.parametrize("kwargs", init_kwargs_cases)
def test_init_kwargs(kwargs):
    ce = CombatEntity(**kwargs)

    for kw in kwargs:
        if hasattr(ce, kw):
            assert getattr(ce, kw) == kwargs[kw]
