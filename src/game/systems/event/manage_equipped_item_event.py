from enum import Enum

from game.cache import from_cache
from game.structures.enums import InputType
from game.structures.messages import ComponentFactory
from game.systems.event import Event


class ManageEquippedItemEvent(Event):
    class States(Enum):
        DEFAULT = 0
        DISPLAY = 1
        UNEQUIP = 2
        TERMINATE = -1

    def __init__(self, slot: str):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        if not isinstance(slot, str):
            raise TypeError("`slot` must be of type str!")

        self.target_slot = from_cache("managers.EquipmentManager").is_valid_slot(slot)
        self.ref = from_cache("managers.ItemManager").get_instance(
            from_cache("player").equipment_controller[slot].item_id
        )

        @self.state_logic(self.States.DEFAULT, InputType.INT, -1, 0)
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            if user_input == 0:
                self.set_state(self.States.UNEQUIP)

        @self.state_content(self.States.DEFAULT)
        def _content() -> dict:
            return ComponentFactory.get(
                [
                    self.ref.name,
                    "'s Summary",
                    "\n",
                    self.ref.functional_description,
                    "\n",
                    self.ref.description,
                    "\n",
                    "Stats:",
                    "\n",
                    "\n".join([f" - {k}: {v}" for k, v in self.ref.get_stats().items()]),
                ]
                + [
                    "\n\nType Resistances:",
                    "\n",
                    "\n".join([f" - {t}: {v * 100}%" for t, v in self.ref.tags.items()]),
                ]
                if len(self.ref.tags)
                else []
                + [
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in self.ref.market_values]),
                ],
                [["Unequip"]],
            )

        @self.state_logic(self.States.UNEQUIP, InputType.SILENT)
        def _logic(_) -> None:
            from_cache("player").equipment_controller.unequip(self.target_slot)
            self.set_state(self.States.TERMINATE)
