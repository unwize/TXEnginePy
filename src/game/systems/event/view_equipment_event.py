from __future__ import annotations

from enum import Enum

import game
from game.structures.enums import InputType
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.entity.entities import CombatEntity
from game.systems.event import Event
from game.systems.event.events import EntityTargetMixin
from game.systems.event.inspect_item_event import InspectItemEvent


class ViewEquipmentEvent(EntityTargetMixin, Event):
    class States(Enum):
        DEFAULT = 0
        DISPLAY_EQUIPMENT = 1
        INSPECT_EQUIPMENT = 2
        SLOT_IS_EMPTY = 3
        TERMINATE = -1

    def __init__(self, target: CombatEntity, item_id: int = None, **kwargs):
        super().__init__(
            default_input_type=InputType.SILENT,
            states=self.States,
            default_state=self.States.DEFAULT,
            target=target,
            **kwargs,
        )

        self._inspect_item_id: int = item_id
        self._one_shot = True if item_id is not None else False

        if not isinstance(self.target, CombatEntity):
            raise TypeError(
                f"ViewEquipmentEvent.target must be of type " f"CombatEntity! Got {type(self.target)} instead."
            )

        self._setup_states()

    def _setup_states(self):
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            if self._inspect_item_id:
                self.set_state(self.States.INSPECT_EQUIPMENT)
            else:
                self.set_state(self.States.DISPLAY_EQUIPMENT)

        @FiniteStateDevice.state_logic(
            self,
            self.States.DISPLAY_EQUIPMENT,
            InputType.INT,
            input_min=-1,
            input_max=lambda: len(self.target.equipment_controller.enabled_slots) - 1,
        )
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            slot = self.target.equipment_controller.enabled_slots[user_input]
            if self.target.equipment_controller[slot].item_id is None:
                self.set_state(self.States.SLOT_IS_EMPTY)
                return

            self._inspect_item_id = self.target.equipment_controller[slot].item_id
            self.set_state(self.States.INSPECT_EQUIPMENT)

        @FiniteStateDevice.state_content(self, self.States.DISPLAY_EQUIPMENT)
        def _content() -> dict:
            return ComponentFactory.get(
                [self.target.name, "'s Equipment:"], self.target.equipment_controller.get_equipment_as_options()
            )

        @FiniteStateDevice.state_logic(self, self.States.SLOT_IS_EMPTY, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.DISPLAY_EQUIPMENT)

        @FiniteStateDevice.state_content(self, self.States.SLOT_IS_EMPTY)
        def _content() -> dict:
            return ComponentFactory.get(["This equipment slot is empty."])

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_EQUIPMENT, InputType.SILENT)
        def _logic(_: any) -> None:
            game.add_state_device(InspectItemEvent(self._inspect_item_id))
            self.set_state(self.States.DISPLAY_EQUIPMENT)

    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        raise NotImplementedError("ViewEquipmentEvent does not support JSON loading!")
