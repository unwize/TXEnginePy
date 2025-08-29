from enum import Enum

import game
from game import cache as cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import ComponentFactory, StringContent
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

        @self.state_logic(self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            if cache.from_cache("player") is None:
                raise RuntimeError("Cannot launch ManageInventoryAction without" " a valid Player instance!")

            if self.player_ref is None:
                self.player_ref = cache.from_cache("player")

            if self.player_ref.inventory.size == 0:
                self.set_state(self.States.EMPTY)
            else:
                self.set_state(self.States.DISPLAY_INVENTORY)

        @self.state_logic(self.States.EMPTY, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @self.state_content(self.States.EMPTY)
        def _logic() -> dict:
            return ComponentFactory.get(["Your inventory is empty"])

        # DISPLAY_INVENTORY

        @self.state_logic(self.States.DISPLAY_INVENTORY, InputType.INT, -1, lambda: self.player_ref.inventory.size - 1)
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
            else:
                self.stack_index = user_input
                self.set_state(self.States.INSPECT_STACK)

        @self.state_content(self.States.DISPLAY_INVENTORY)
        def _content() -> dict:
            return ComponentFactory.get(
                ["What stack would you like to inspect?"], self.player_ref.inventory.to_options()
            )

        # INSPECT STACK
        @self.state_logic(self.States.INSPECT_STACK, InputType.INT, -1, len(self.stack_inspect_options) - 1)
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.DISPLAY_INVENTORY)
            else:
                selected_option = list(self.stack_inspect_options.keys())[user_input]
                self.set_state(self.stack_inspect_options[selected_option])

        @self.state_content(self.States.INSPECT_STACK)
        def _content() -> dict:
            c = [
                "What would you like to do with ",
                StringContent(
                    value=f"{self.player_ref.inventory.items[self.stack_index].ref.name}", formatting="item_name"
                ),
                "?",
            ]
            return ComponentFactory.get(c, self.get_stack_inspection_options())

        # CONFIRM_DROP_STACK

        @self.state_logic(self.States.CONFIRM_DROP_STACK, InputType.AFFIRMATIVE)
        def _logic(user_input: bool) -> None:
            if user_input:
                self.set_state(self.States.DROP_STACK)
            else:
                self.set_state(self.States.INSPECT_STACK)

        @self.state_content(self.States.CONFIRM_DROP_STACK)
        def _content() -> dict:
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

        @self.state_logic(self.States.DROP_STACK, InputType.ANY)
        def _logic(_: any) -> None:
            self.player_ref.inventory.drop_stack(self.stack_index)
            self.set_state(self.States.DISPLAY_INVENTORY)

        @self.state_content(self.States.DROP_STACK)
        def _content() -> dict:
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

        @self.state_logic(self.States.DESC_ITEM, InputType.SILENT)
        def _logic(_: any) -> None:
            ref = self.player_ref.inventory.items[self.stack_index].ref

            game.add_state_device(InspectItemEvent(ref.id))
            self.set_state(self.States.INSPECT_STACK)

        # USE_ITEM

        @self.state_logic(self.States.USE_ITEM, InputType.SILENT)
        def _logic(_: any) -> None:
            game.add_state_device(uie.UseItemEvent(self.player_ref.inventory.items[self.stack_index].id))
            self.set_state(self.States.DISPLAY_INVENTORY)

        # EQUIP_ITEM

        @self.state_logic(self.States.EQUIP_ITEM, InputType.ANY)
        def _logic(_: any) -> None:
            item = self.player_ref.inventory.items[self.stack_index].ref

            if not self.player_ref.equipment_controller[item.slot].enabled:
                self.set_state(self.States.EQUIPMENT_SLOT_DISABLED)
                return

            if self.player_ref.equipment_controller[item.slot] is not None:
                self.player_ref.equipment_controller.unequip(item.slot)

            self.player_ref.equipment_controller.equip(item.id)
            self.set_state(self.States.DEFAULT)

        @self.state_content(self.States.EQUIP_ITEM)
        def _content() -> dict:
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
