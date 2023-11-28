from __future__ import annotations

from enum import Enum
from pprint import pprint

from loguru import logger

from game.cache import get_config
from game.structures.enums import InputType
from game.structures.state_device import FiniteStateDevice
from game.systems.entity.entities import CombatEntity
from game.systems.event import Event
from game.systems.event.events import EntityTargetMixin


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
    results = {}

    for tier in get_config()["combat"]["inspection"]:
        print(type(tier))
        print(tier)
        logger.warning("Tier logic has not been implemented!")

    return results


class InspectEntityEvent(EntityTargetMixin, Event):
    class States(Enum):
        DEFAULT = 0
        SHOW_OPTIONS = 1
        INSPECT_RESOURCES = 2
        INSPECT_EQUIPMENT = 3
        INSPECT_INVENTORY = 4
        INSPECT_ABILITIES = 5
        TERMINATE = -1

    ALL_OPTIONS: dict[str, tuple[str, States]] = {
        "INVENTORY": ("Inspect Inventory", States.INSPECT_INVENTORY),
        "RESOURCES": ("Inspect Resources", States.INSPECT_RESOURCES),
        "EQUIPMENT": ("Inspect Equipment", States.INSPECT_EQUIPMENT),
        "ABILITIES": ("Inspect Abilities", States.INSPECT_ABILITIES)
    }

    def __init__(self, target: CombatEntity, inspection_tier: int = 0):
        super().__init__(target=target, default_input_type=InputType.SILENT, states=self.States,
                         default_state=self.States.DEFAULT)

        # Map states to listed prompts for user_branching_state. Key-Value pairs are generated during __init__
        self.options_map: dict[str, any] = {}

        if inspection_tier not in get_all_inspection_tiers():
            logger.error(f"Unknown inspection tier {inspection_tier}! Available tiers: {get_all_inspection_tiers()}")
            raise RuntimeError(f"Unknown inspection tier {inspection_tier}!")

        # Check which options are available for the current inspection tier, then generate the options map from them
        available_options = get_inspection_tier(inspection_tier)
        for option in self.ALL_OPTIONS:
            if option in available_options:
                option_listing, option_state = self.ALL_OPTIONS[option]
                self.options_map[option_listing] = option_state

        self._setup_states()

    def _setup_states(self):

        # SHOW_OPTIONS
        FiniteStateDevice.user_branching_state(self, self.States.SHOW_OPTIONS, self.options_map,
                                               back_out_state=self.States.TERMINATE)

        # INSPECT_ABILITIES



    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        raise NotImplemented("InspectEntityEvent does not support JSON loading!")
