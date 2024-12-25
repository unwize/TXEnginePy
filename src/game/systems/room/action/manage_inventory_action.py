from enum import Enum

import game
from game import cache as cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems import entity
from game.systems.event import use_item_event as uie
from game.systems.event.inspect_item_event import InspectItemEvent
from game.systems.room.action.actions import Action


class ManageInventoryAction(Action):
    class States(Enum):
        DEFAULT = 0
        DISPLAY_INVENTORY = 1
        INSPECT_STACK = 2
        DROP_STACK = 3
        CONFIRM_DROP_STACK = 4
        USE_ITEM = 5
        DESC_ITEM = 6
        EQUIP_ITEM = 8
        EMPTY = 9
        TERMINATE = -1

    stack_inspect_options = {
        "Inspect": States.DESC_ITEM,
        "Use": States.USE_ITEM,
        "Equip": States.EQUIP_ITEM,
        "Drop": States.CONFIRM_DROP_STACK,
    }

    @classmethod
    def get_stack_inspection_options(cls) -> list[list[str]]:
        return [[opt] for opt in cls.stack_inspect_options.keys()]

    def __init__(self, **kwargs):
        super().__init__("View inventory", "", self.States, self.States.DEFAULT, InputType.SILENT, **kwargs)

        self.player_ref: entity.entities.Player = None
        self.stack_index: int = None

        # DEFAULT

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def logic(_: any) -> None:
            if cache.from_cache("player") is None:
                raise RuntimeError("Cannot launch ManageInventoryAction without" " a valid Player instance!")

            if self.player_ref is None:
                self.player_ref = cache.from_cache("player")

            if self.player_ref.inventory.size == 0:
                self.set_state(self.States.EMPTY)
            else:
                self.set_state(self.States.DISPLAY_INVENTORY)

        @FiniteStateDevice.state_logic(self, self.States.EMPTY, InputType.ANY)
        def logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.EMPTY)
        def logic() -> dict:
            return ComponentFactory.get(["Your inventory is empty"])

        # DISPLAY_INVENTORY

        @FiniteStateDevice.state_logic(
            self, self.States.DISPLAY_INVENTORY, InputType.INT, -1, lambda: self.player_ref.inventory.size - 1
        )
        def logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
            else:
                self.stack_index = user_input
                self.set_state(self.States.INSPECT_STACK)

        @FiniteStateDevice.state_content(self, self.States.DISPLAY_INVENTORY)
        def content() -> dict:
            return ComponentFactory.get(
                ["What stack would you like to inspect?"], self.player_ref.inventory.to_options()
            )

        # INSPECT STACK
        @FiniteStateDevice.state_logic(
            self, self.States.INSPECT_STACK, InputType.INT, -1, len(self.stack_inspect_options) - 1
        )
        def logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.DISPLAY_INVENTORY)
            else:
                selected_option = list(self.stack_inspect_options.keys())[user_input]
                self.set_state(self.stack_inspect_options[selected_option])

        @FiniteStateDevice.state_content(self, self.States.INSPECT_STACK)
        def content() -> dict:
            c = [
                "What would you like to do with ",
                StringContent(
                    value=f"{self.player_ref.inventory.items[self.stack_index].ref.name}", formatting="item_name"
                ),
                "?",
            ]
            return ComponentFactory.get(c, self.get_stack_inspection_options())

        # CONFIRM_DROP_STACK

        @FiniteStateDevice.state_logic(self, self.States.CONFIRM_DROP_STACK, InputType.AFFIRMATIVE)
        def logic(user_input: bool) -> None:
            if user_input:
                self.set_state(self.States.DROP_STACK)
            else:
                self.set_state(self.States.INSPECT_STACK)

        @FiniteStateDevice.state_content(self, self.States.CONFIRM_DROP_STACK)
        def content() -> dict:
            stack = self.player_ref.inventory.items[self.stack_index]
            return ComponentFactory.get(
                [
                    "Are you sure you want to drop ",
                    StringContent(value=stack.ref.name, formatting="item_name"),
                    " ",
                    StringContent(value=f"{stack.quantity}x", formatting="item_quantity"),
                    "?",
                ]
            )

        # DROP_STACK

        @FiniteStateDevice.state_logic(self, self.States.DROP_STACK, InputType.ANY)
        def logic(_: any) -> None:
            self.player_ref.inventory.drop_stack(self.stack_index)
            self.set_state(self.States.DISPLAY_INVENTORY)

        @FiniteStateDevice.state_content(self, self.States.DROP_STACK)
        def content() -> dict:
            stack = self.player_ref.inventory.items[self.stack_index]
            return ComponentFactory.get(
                [
                    "You dropped ",
                    StringContent(value=f"{stack.quantity}x", formatting="item_quantity"),
                    " ",
                    StringContent(value=stack.ref.name, formatting="item_name"),
                    ".",
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.DESC_ITEM, InputType.SILENT)
        def logic(_: any) -> None:
            ref = self.player_ref.inventory.items[self.stack_index].ref

            game.add_state_device(InspectItemEvent(ref.id))
            self.set_state(self.States.INSPECT_STACK)

        # USE_ITEM

        @FiniteStateDevice.state_logic(self, self.States.USE_ITEM, InputType.SILENT)
        def logic(_: any) -> None:
            game.add_state_device(uie.UseItemEvent(self.player_ref.inventory.items[self.stack_index].id))
            self.set_state(self.States.DISPLAY_INVENTORY)

        # EQUIP_ITEM

        @FiniteStateDevice.state_logic(self, self.States.EQUIP_ITEM, InputType.ANY)
        def logic(_: any) -> None:
            item = self.player_ref.inventory.items[self.stack_index].ref

            if not self.player_ref.equipment_controller[item.slot].enabled:
                self.set_state(self.States.EQUIPMENT_SLOT_DISABLED)
                return

            if self.player_ref.equipment_controller[item.slot] is not None:
                self.player_ref.equipment_controller.unequip(item.slot)

            self.player_ref.equipment_controller.equip(item.id)
            self.set_state(self.States.DEFAULT)

        @FiniteStateDevice.state_content(self, self.States.EQUIP_ITEM)
        def content() -> dict:
            return ComponentFactory.get(
                [
                    "You equipped ",
                    StringContent(value=self.player_ref.inventory.items[self.stack_index].ref.name, style="item_name"),
                ]
            )

    @staticmethod
    @cache.cached([LoadableMixin.LOADER_KEY, "ManageInventoryAction", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        LoadableFactory.validate_fields([], json)
        if json["class"] != "ManageInventoryAction":
            raise ValueError(f"Cannot load object of type {json['class']} via " f"ManageInventoryAction.from_json!")

        return ManageInventoryAction()
