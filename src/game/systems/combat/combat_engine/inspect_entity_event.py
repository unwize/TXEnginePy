from __future__ import annotations

from enum import Enum

from loguru import logger

import game
from game.cache import get_config
from game.structures.enums import InputType
from game.structures.state_device import FiniteStateDevice
from game.systems.event import Event
from game.systems.event.events import EntityTargetMixin, ViewResourcesEvent
from game.systems.event.view_abilities_event import ViewAbilitiesEvent
from game.systems.event.view_equipment_event import ViewEquipmentEvent
from game.systems.event.view_inventory_event import ViewInventoryEvent
from game.systems.event.view_skills_event import ViewSkillsEvent


def get_inspection_tier(tier: int) -> list[str]:
    """
    Retrieves the configuration values for a specific inspection tier.

    args:
        tier (int): The tier to retrieve

    returns: A list of strings that represent the available information for that specific tier
    """
    return get_all_inspection_tiers()[tier]


def get_all_inspection_tiers() -> dict[int, list[str]]:
    """
    Retrieves the configuration values for all inspection tiers.

    Tiers are stored in the format of "t{x}" : ["CONFIG", "VALUES", "HERE]". The key is stripped and converted into an
    int while the value remains the same.

    args:
        None

    returns: A dict mapping a tier (int) to a list of config values (strings).
    """

    inspection_data = get_config()["combat"]["inspection"]
    results = {}

    for tier in inspection_data:
        if type(tier) is not str or len(tier) != 2:
            raise ValueError(f"Invalid Tier name! {tier}")

        try:
            results[int(tier[1])] = inspection_data[tier]
        except Exception as e:
            logger.error(f"Something went wrong while processing Inspection Tier {tier}!")
            raise e

    return results


class InspectEntityEvent(EntityTargetMixin, Event):
    class States(Enum):
        DEFAULT = 0
        SHOW_OPTIONS = 1
        INSPECT_RESOURCES = 2
        INSPECT_EQUIPMENT = 3
        INSPECT_INVENTORY = 4
        INSPECT_ABILITIES = 5
        INSPECT_SKILLS = 6
        TERMINATE = -1

    ALL_OPTIONS: dict[str, tuple[str, States]] = {
        "INVENTORY": ("Inspect Inventory", States.INSPECT_INVENTORY),
        "RESOURCES": ("Inspect Resources", States.INSPECT_RESOURCES),
        "EQUIPMENT": ("Inspect Equipment", States.INSPECT_EQUIPMENT),
        "ABILITIES": ("Inspect Abilities", States.INSPECT_ABILITIES),
        "SKILLS": ("Inspect Skills", States.INSPECT_ABILITIES),
    }

    def __init__(self, target, inspection_tier: int = None):
        super().__init__(
            target=target, default_input_type=InputType.SILENT, states=self.States, default_state=self.States.DEFAULT
        )

        from game.systems.entity.entities import CombatEntity

        if not isinstance(target, CombatEntity):
            raise TypeError(
                f"InspectEntityEvent target must be an instance of class CombatEntity! Got {type(target)} instead."
            )

        # Map states to listed prompts for user_branching_state. Key-Value pairs are generated during __init__
        self._options_map: dict[str, any] = {}
        self._inspection_tier = inspection_tier or get_config()["combat"]["default_inspection_tier"]

        if self._inspection_tier not in get_all_inspection_tiers():
            logger.error(f"Unknown inspection tier {inspection_tier}! Available tiers: {get_all_inspection_tiers()}")
            raise RuntimeError(f"Unknown inspection tier {inspection_tier}!")

        # Check which options are available for the current inspection tier, then generate the options map from them
        available_options = get_inspection_tier(self._inspection_tier)
        for option in self.ALL_OPTIONS:
            if option in available_options:
                option_listing, option_state = self.ALL_OPTIONS[option]
                self._options_map[option_listing] = option_state

        self._setup_states()

    def _setup_states(self):
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self.set_state(self.States.SHOW_OPTIONS)

        # SHOW_OPTIONS
        FiniteStateDevice.user_branching_state(
            self, self.States.SHOW_OPTIONS, self._options_map, back_out_state=self.States.TERMINATE
        )

        # INSPECT_ABILITIES
        @FiniteStateDevice.state_logic(self, self.States.INSPECT_ABILITIES, InputType.SILENT)
        def _logic(_: any) -> None:
            event = ViewAbilitiesEvent(target=self.target)
            game.add_state_device(event)
            self.set_state(self.States.SHOW_OPTIONS)

        # INSPECT_EQUIPMENT
        @FiniteStateDevice.state_logic(self, self.States.INSPECT_EQUIPMENT, InputType.SILENT)
        def _logic(_: any) -> None:
            event = ViewEquipmentEvent(target=self.target)
            game.add_state_device(event)
            self.set_state(self.States.SHOW_OPTIONS)

        # INSPECT_INVENTORY
        @FiniteStateDevice.state_logic(self, self.States.INSPECT_INVENTORY, InputType.SILENT)
        def _logic(_: any) -> None:
            event = ViewInventoryEvent(target=self.target)
            game.add_state_device(event)
            self.set_state(self.States.SHOW_OPTIONS)

        # INSPECT_SKILLS
        @FiniteStateDevice.state_logic(self, self.States.INSPECT_RESOURCES, InputType.SILENT)
        def _logic(_: any) -> None:
            event = ViewResourcesEvent(target=self.target)
            game.add_state_device(event)
            self.set_state(self.States.SHOW_OPTIONS)

        # INSPECT_RESOURCES
        @FiniteStateDevice.state_logic(self, self.States.INSPECT_SKILLS, InputType.SILENT)
        def _logic(_: any) -> None:
            event = ViewSkillsEvent(target=self.target)
            game.add_state_device(event)
            self.set_state(self.States.SHOW_OPTIONS)

    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        raise NotImplementedError("InspectEntityEvent does not support JSON loading!")
