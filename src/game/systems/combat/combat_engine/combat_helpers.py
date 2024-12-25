from game.systems.combat import Ability
from game.systems.entity.entities import CombatEntity


def sum_a_tag(resistances: list[float]) -> float:
    """
    For a list of float resistances, compute the final total resistance from
    among them.

    The formula works as follows:
    - Sort in descending order
    - Total = resistances[0]
    - for each resistance from index: 1
        - total = total * (1 + resistance)

    Args:
        resistances: A list of float resistances

    Returns: A sum of all the given resistances
    """
    tag_values = sorted(resistances, reverse=True)

    total_res = tag_values[0]

    for tag in tag_values[1:]:
        total_res = total_res * (1 + tag)

    return total_res


def calculate_target_resistance(ability: Ability, target: CombatEntity) -> float:
    """
    For a given Ability and target, calculate the resistance value of the target

    Args:
        ability: The Ability to check against
        target: The CombatEntity to check against

    Returns: A float representing the resistance of the target
    """
    if not isinstance(ability, Ability):
        raise TypeError(f"Expected ability to be of type Ability, got " f"{type(ability)} instead!")

    if not isinstance(target, CombatEntity):
        raise TypeError("Expected target to be of type CombatEntity, got " f"{type(target)} instead!")

    if not isinstance(ability.tags, dict):
        raise TypeError("ability.tags should be of type dict! Got type" f"{type(ability.tags)} instead!")

    tag_values: list[float] = [0.0]
    tags_on_target: dict[str, list[float]] = target.equipment_controller.all_tag_resistance

    # Iterate through tags on Ability
    for ability_tag in ability.tags:
        # Check if tag is present in target's Equipments
        if ability_tag in tags_on_target:
            tag_values += tags_on_target[ability_tag]  # Add resistances to queue

    tag_values = sorted(tag_values, reverse=True)

    return round(sum_a_tag(tag_values), 2)


def calculate_damage_to_entity(ability: Ability, target: CombatEntity) -> int:
    """
    For a given Ability, compute the total amount of damage dealt to the target.

    The damage formula is as follows:

    total damage = (ability_base_damage) - target_armor - (1 - total_tag_res)

    Args:
        ability: The Ability to check against
        target: The CombatEntity that the ability should be targeting

    Returns: An int representing how much damage should be dealt to the target
    """

    if not isinstance(ability, Ability):
        raise TypeError(f"Expected ability to be of type Ability, got " f"{type(ability)} instead!")

    if not isinstance(target, CombatEntity):
        raise TypeError("Expected target to be of type CombatEntity, got " f"{type(target)} instead!")

    target_tag_res = calculate_target_resistance(ability, target)
    target_armor_res = target.equipment_controller.total_dmg_resistance

    return max(int((ability.damage - target_armor_res) * (1 - target_tag_res)), 0)
