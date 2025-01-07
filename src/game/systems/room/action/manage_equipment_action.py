from enum import Enum

from game.cache import cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.entity import Player
from game.systems.room.action.actions import Action


class ManageEquipmentAction(Action):
    """
    A room Action that allows the user to comprehensively inspect and manage
    their equipped items.
    """

    class States(Enum):
        DEFAULT = 0
        LIST_SLOTS = 1  # Display a list of slots to user
        INSPECT_SLOT = 2  # Display options for a specific slot
        INSPECT_EQUIPMENT = 3  # Show details for a specific item in a selected slot
        VIEW_AVAILABLE_EQUIPMENT_FOR_SLOT = 4  # Show a list of items that fit into the selected slot
        REQUIREMENTS_NOT_MET = 5  # The user selected an item that they do not meet the requirements for
        REQUIREMENTS_MET = 6  # The user selected an item that they meet the requirements for
        UNEQUIP_ITEM = 7  # Remove an item from the selected slot
        TERMINATE = -1

    def __init__(self, menu_name: str = "Manage Equipment", activation_text: str = "", **kwargs):
        super().__init__(menu_name, activation_text, self.States, self.States.DEFAULT, InputType.SILENT, **kwargs)
        self._selected_slot: str = None
        self._player_ref: Player = None

        self._setup_states()

    @property
    def _inspect_slot_branch_map(self) -> dict[str, any]:
        """
        Calculate on-the-fly which options are available to the user within the INSPECT_SLOT state
        """

        res = {"Equip an item": self.States.VIEW_AVAILABLE_EQUIPMENT_FOR_SLOT}

        if self._player_ref.equipment_controller[self._selected_slot].item_id is not None:
            res["Unequip"] = self.States.UNEQUIP_ITEM
            res["Inspect"] = self.States.INSPECT_EQUIPMENT

        return res

    @property
    def selected_slot(self) -> str:
        return self._selected_slot

    def _setup_states(self) -> None:
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            # Get user-ref
            if not self._player_ref:
                self._player_ref = from_cache("player")

            # Clear in case this state is reached due to a FSD reset
            self._selected_slot = None

            self.set_state(self.States.DEFAULT)

        @FiniteStateDevice.state_logic(
            self,
            self.States.LIST_SLOTS,
            InputType.INT,
            input_min=-1,
            input_max=lambda: len(self._player_ref.equipment_controller.enabled_slots) - 1,
        )
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            self._selected_slot = self._player_ref.equipment_controller.enabled_slots[user_input]
            self.set_state(self.States.INSPECT_SLOT)

        @FiniteStateDevice.state_content(self, self.States.LIST_SLOTS)
        def _content() -> dict:
            return ComponentFactory.get(
                ["Which slot would you like to select?"],
                self._player_ref.equipment_controller.get_equipment_as_options(),
            )

        FiniteStateDevice.user_branching_state(
            self,
            self.States.INSPECT_SLOT,
            self._inspect_slot_branch_map,
            f"What would you like to do with the {self.selected_slot} slot?",
            self.States.LIST_SLOTS,
        )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_EQUIPMENT, InputType.ANY)
        def _logic(_: any) -> None:
            pass

        @FiniteStateDevice.state_content(self, self.States.INSPECT_EQUIPMENT)
        def _content() -> dict:
            pass

        @FiniteStateDevice.state_logic(self, self.States.REQUIREMENTS_MET, InputType.ANY)
        def _logic(_: any) -> None:
            pass

        @FiniteStateDevice.state_content(self, self.States.REQUIREMENTS_MET)
        def _content() -> dict:
            pass

        @FiniteStateDevice.state_logic(self, self.States.REQUIREMENTS_NOT_MET, InputType.ANY)
        def _logic(_: any) -> None:
            pass

        @FiniteStateDevice.state_content(self, self.States.REQUIREMENTS_NOT_MET)
        def _content() -> dict:
            pass

        @FiniteStateDevice.state_logic(self, self.States.UNEQUIP_ITEM, InputType.AFFIRMATIVE)
        def _logic(user_input: bool) -> None:
            pass

        @FiniteStateDevice.state_content(self, self.States.UNEQUIP_ITEM)
        def _content() -> dict:
            pass

        @FiniteStateDevice.state_logic(self, self.States.VIEW_AVAILABLE_EQUIPMENT_FOR_SLOT, InputType.SILENT)
        def _logic(_: any) -> None:
            """
            Spawn a pre-configured event to handle the selection process. Retrieve the results via storage and manage
            inventory accordingly.
            """
            pass

        @FiniteStateDevice.state_content(self, self.States.VIEW_AVAILABLE_EQUIPMENT_FOR_SLOT)
        def _content() -> dict:
            pass

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ManageEquipmentAction", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        return ManageEquipmentAction()
