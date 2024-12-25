from game.structures.enums import TargetMode
from game.systems.combat.ability import Ability
from game.systems.combat.effect import ResourceEffect


def test_init_trivial():
    a = Ability(
        name="Test Ability",
        description="A simple test ability",
        on_use="Someone used a test ability somehow.",
        target_mode=TargetMode.SINGLE,
    )

    assert a is not None
    assert a.name == "Test Ability"
    assert a.description == "A simple test ability"
    assert a.on_use == "Someone used a test ability somehow."
    assert a.target_mode == TargetMode.SINGLE


def test_init_effects():
    re = ResourceEffect("Health", -10, "{ENTITY} lost {QUANTITY} {RESOURCE}")
    a = Ability(
        name="Test Ability",
        description="A simple test ability",
        on_use="Someone used a test ability somehow.",
        target_mode=TargetMode.SINGLE,
        effects=[re],
    )

    assert a is not None
    assert a.name == "Test Ability"
    assert a.description == "A simple test ability"
    assert a.on_use == "Someone used a test ability somehow."
    assert a.target_mode == TargetMode.SINGLE
    assert len(a.effects) is not None
    assert re in a.effects
