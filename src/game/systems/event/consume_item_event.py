from enum import Enum

import game.cache
from game.cache import cached
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems import item as item
from game.systems.entity import entities as entities
from game.systems.event import Event


class ConsumeItemEvent(Event):
    """Provides a standardized flow for prompting the user to optionally consume 'n' of a given item from his/her
    inventory
    """

    class States(Enum):
        DEFAULT = 0
        PROMPT_CONSUME = 1
        INSUFFICIENT_QUANTITY = 2
        REFUSED_CONSUME = 3
        ACCEPTED_CONSUME = 4
        TERMINATE = -1

    def __init__(self, item_id: int, item_quantity: int, callback: any = None):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self.item_id = item_id
        self.item_quantity = item_quantity
        self.player_ref: entities.Player = game.cache.get_cache()["player"]

        if callable(callback):
            self.callback = callback
        elif callback is not None:
            raise TypeError(f"Callback must be callable! Got {type(callback)} instead.")
        else:
            self.callback = None

        # DEFAULT

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            # Detect item quantities
            if self.player_ref.inventory.total_quantity(self.item_id) < self.item_quantity:
                self.set_state(self.States.INSUFFICIENT_QUANTITY)
            else:
                self.set_state(self.States.PROMPT_CONSUME)

        # INSUFFICIENT_QUANTITY

        @FiniteStateDevice.state_logic(self, self.States.INSUFFICIENT_QUANTITY, InputType.ANY)
        def _logic(_: any) -> None:
            if self.callback:
                self.callback(False)  # Transmit that the player failed to consume items to the callback
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSUFFICIENT_QUANTITY)
        def _content():
            return ComponentFactory.get(
                [
                    "Insufficient quantity of ",
                    StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
                    "!",
                ]
            )

        # PROMPT_CONSUME

        @FiniteStateDevice.state_logic(self, self.States.PROMPT_CONSUME, InputType.AFFIRMATIVE)
        def _logic(user_input: bool) -> None:
            if user_input:
                self.set_state(self.States.ACCEPTED_CONSUME)
            else:
                self.set_state(self.States.REFUSED_CONSUME)

        @FiniteStateDevice.state_content(self, self.States.PROMPT_CONSUME)
        def _content():
            return ComponentFactory.get(
                [
                    "Are you sure that you want to consume ",
                    StringContent(value=f"{self.item_quantity}x ", formatting="item_quantity"),
                    StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
                    "?",
                ]
            )

        # ACCEPTED_CONSUME

        @FiniteStateDevice.state_logic(self, self.States.ACCEPTED_CONSUME, InputType.ANY)
        def _logic(_: any) -> None:
            assert self.player_ref.inventory.consume_item(self.item_id, self.item_quantity)
            if self.callback:
                self.callback(True)  # Transmit that the player successfully consumed items to the callback
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.ACCEPTED_CONSUME)
        def _content():
            return ComponentFactory.get(
                [
                    "You consumed ",
                    StringContent(value=f"{self.item_quantity}x ", formatting="item_quantity"),
                    StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
                    ".",
                ]
            )

        # REFUSED_CONSUME

        @FiniteStateDevice.state_logic(self, self.States.REFUSED_CONSUME, InputType.ANY)
        def _logic(_: any) -> None:
            if self.callback:
                self.callback(False)  # Transmit that the player did not consume items to the callback
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.REFUSED_CONSUME)
        def _content():
            return ComponentFactory.get(
                [
                    "You refused to consume ",
                    StringContent(value=f"{self.item_quantity}x ", formatting="item_quantity"),
                    StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
                    ".",
                ]
            )

    def __copy__(self):
        return ConsumeItemEvent(self.item_id, self.item_quantity, self.callback)

    def __deepcopy__(self, memodict={}):
        return self.__copy__()

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ConsumeItemEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a ConsumeItemEvent object from a JSON blob.

        Required JSON fields:
        - item_id (int)
        - item_quantity (int)
        """

        required_fields = [("item_id", int), ("item_quantity", int)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "ConsumeItemEvent":
            raise ValueError()

        return ConsumeItemEvent(json["item_id"], json["item_quantity"])
