from __future__ import annotations

from enum import Enum

import game
from game.cache import from_cache
from game.structures.enums import InputType
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.entity.entities import CombatEntity
from game.systems.event import Event
from game.systems.event.events import EntityTargetMixin


class InspectItemEvent(Event):
    """
    A simple Event that prints the inspection details of a specific Item to
    the player.

    InspecItemEvent checks the subtype of Item fetched and will display extra
    information accordingly.
     - An Item has its description and values printed.
     - A Usable prints what Item prints and adds its functional description.
     - An Equipment prints what Item prints and adds tags and stats.
    """

    class States(Enum):
        DEFAULT = 0
        CHECK_TYPE = 1
        INSPECT_ITEM = 2
        INSPECT_USABLE = 3
        INSPECT_EQUIPMENT = 4
        TERMINATE = -1

    def __init__(self, item_id: int):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self.item_id = item_id
        self.ref = from_cache("managers.ItemManager").get_instance(self.item_id)

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT,
                                       InputType.SILENT)
        def logic(_: any) -> None:
            self.set_state(self.States.CHECK_TYPE)

        @FiniteStateDevice.state_logic(self, self.States.CHECK_TYPE,
                                       InputType.SILENT)
        def logic(_: any) -> None:
            from game.systems.item.item import Item, Usable, Equipment

            if isinstance(self.ref, Equipment):
                self.set_state(self.States.INSPECT_EQUIPMENT)
            elif isinstance(self.ref, Usable):
                self.set_state(self.States.INSPECT_USABLE)
            elif isinstance(self.ref, Item):
                self.set_state(self.States.INSPECT_ITEM)
            else:
                raise TypeError("ref did not fetch an Item instance!")

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_ITEM,
                                       InputType.ANY)
        def logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSPECT_ITEM)
        def content() -> dict:
            return ComponentFactory.get(
                [
                    self.ref.name, "'s Summary",
                    "\n",
                    self.ref.description,
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in
                               self.ref.market_values])
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_USABLE,
                                       InputType.ANY)
        def logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSPECT_USABLE)
        def content() -> dict:
            return ComponentFactory.get(
                [
                    self.ref.name, "'s Summary",
                    "\n",
                    self.ref.functional_description,
                    "\n",
                    self.ref.description,
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in
                               self.ref.market_values])
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_EQUIPMENT,
                                       InputType.ANY)
        def logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSPECT_EQUIPMENT)
        def content() -> dict:
            """
                        Print in the following format:
                            * item.name
                            * Value:
                            * |cur.name\t|cur.value\t|
                            * item.desc
                        """
            return ComponentFactory.get(
                [
                    self.ref.name, "'s Summary",
                    "\n",
                    self.ref.functional_description,
                    "\n",
                    self.ref.description,
                    "\n",
                    "Stats:",
                    "\n",
                    "\n".join(
                        [f" - {k}: {v}" for k, v in self.ref.get_stats().items()]),
                    "\n\n"
                    "Type Resistances:",
                    "\n",
                    "\n".join([f" - {t}: {v}" for t, v in self.ref.tags.items()]),
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in
                               self.ref.market_values])
                ]
            )


class ViewEquipmentEvent(EntityTargetMixin, Event):
    class States(Enum):
        DEFAULT = 0
        DISPLAY_EQUIPMENT = 1
        INSPECT_EQUIPMENT = 2
        SLOT_IS_EMPTY = 3
        TERMINATE = -1

    def __init__(self, target: CombatEntity, item_id: int = None, **kwargs):
        super().__init__(default_input_type=InputType.SILENT,
                         states=self.States,
                         default_state=self.States.DEFAULT,
                         target=target,
                         **kwargs)

        self._inspect_item_id: int = item_id
        self._one_shot = True if item_id is not None else False

        if not isinstance(self.target, CombatEntity):
            raise TypeError(f"ViewEquipmentEvent.target must be of type "
                            f"CombatEntity! Got {type(self.target)} instead.")

        self._setup_states()

    def _setup_states(self):
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT,
                                       InputType.SILENT)
        def logic(_: any) -> None:
            if self._inspect_item_id:
                self.set_state(self.States.INSPECT_EQUIPMENT)
            else:
                self.set_state(self.States.DISPLAY_EQUIPMENT)

        @FiniteStateDevice.state_logic(self, self.States.DISPLAY_EQUIPMENT,
                                       InputType.INT, input_min=-1,
                                       input_max=lambda: len(
                                           self.target.equipment_controller.enabled_slots) - 1)
        def logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            slot = self.target.equipment_controller.enabled_slots[user_input]
            if self.target.equipment_controller[slot].item_id is None:
                self.set_state(self.States.SLOT_IS_EMPTY)
                return

            self._inspect_item_id = self.target.equipment_controller[
                slot].item_id
            self.set_state(self.States.INSPECT_EQUIPMENT)

        @FiniteStateDevice.state_content(self, self.States.DISPLAY_EQUIPMENT)
        def content() -> dict:
            return ComponentFactory.get(
                [self.target.name, "'s Equipment:"],
                self.target.equipment_controller.get_equipment_as_options()
            )

        @FiniteStateDevice.state_logic(self, self.States.SLOT_IS_EMPTY,
                                       InputType.ANY)
        def logic(_: any) -> None:
            self.set_state(self.States.DISPLAY_EQUIPMENT)

        @FiniteStateDevice.state_content(self, self.States.SLOT_IS_EMPTY)
        def content() -> dict:
            return ComponentFactory.get(
                ["This equipment slot is empty."]
            )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_EQUIPMENT,
                                       InputType.SILENT)
        def logic(_: any) -> None:
            game.add_state_device(InspectItemEvent(self._inspect_item_id))
            self.set_state(self.States.DISPLAY_EQUIPMENT)


    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        raise NotImplemented(
            "ViewEquipmentEvent does not support JSON loading!")
