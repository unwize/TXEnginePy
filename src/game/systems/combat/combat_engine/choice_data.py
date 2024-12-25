from __future__ import annotations

from enum import Enum

from game.structures.errors import CombatError
from game.systems.entity import entities

from loguru import logger


class ChoiceData:
    """
    A struct with built-in validation logic for entity combat choices.

    ChoiceData strictly enforces that all types are correct and that there are no missing or extraneous values.

    An entity may choose to: pass the turn, select an item to use, select an ability to use
    """

    class ChoiceType(Enum):
        PASS = "pass"
        ABILITY = "ability"
        ITEM = "item"

    def __init__(
        self,
        choice_type: ChoiceType,
        item_id: int = None,
        ability_name: str = None,
        ability_target: list[entities.CombatEntity] = None,
    ):
        self.ability_name: str | None = None  # Name of selected ability
        self.ability_target: list[entities.CombatEntity] | None = None  # Target of selected ability
        self.item_id: int | None = None  # ID of selected item
        self.choice_type = choice_type

        if choice_type == ChoiceData.ChoiceType.ITEM:
            if ability_target is not None or ability_name is not None:
                logger.error("Cannot process choice! `choice_type` == 'item', but ability values are not None!")
                raise CombatError("Cannot process choice! `choice_type` == 'item', but ability values are not None!")

            self.item_id = item_id

        elif choice_type == ChoiceData.ChoiceType.ABILITY:
            if item_id is not None:
                logger.error("Cannot process choice! `choice_type` == 'ability', but item values are not None!")
                raise CombatError("Cannot process choice! `ability` == 'item', but item values are not None!")

            self.ability_target = ability_target
            self.ability_name = ability_name

        elif choice_type == ChoiceData.ChoiceType.PASS:
            if item_id is not None or ability_name is not None or ability_target is not None:
                logger.error("Cannot process choice! `choice_type` == 'pass', but other values are not None!")
                raise CombatError("Cannot process choice! `choice_type` == 'pass', but other values are not None!")

        else:
            raise CombatError(f"Unknown choice type {choice_type}!")
