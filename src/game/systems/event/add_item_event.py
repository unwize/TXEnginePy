"""
A sublass of Event that handles adding one or more items to an Inventory with a
User-centric flow.
"""

import weakref
from enum import Enum

from loguru import logger

from game import cache
from game.structures.enums import InputType as IT
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems import item as item
from game.systems.entity import entities as entities
from game.systems.event.events import Event


class AddItemEvent(Event):
    """
    An Event that flows the user through the process of adding an item to their
    inventory.

    This is usually an automatic process, but occasionally requires user
    intervention, particularly when there isn't enough inventory space.
    """

    class States(Enum):
        """
        Internal State Enum
        """

        DEFAULT = 0
        PROMPT_KEEP_NEW_ITEM = 1
        INSERT_ITEM = 2
        TERMINATE = -1

    def __init__(self, item_id: int, item_quantity: int = 1):
        """
        Args:
            item_id:
                The ID of the Item to attempt to add to the player's inventory.
            item_quantity:
                The quantity of the Item to attempt to add to the player's
                inventory.

        Returns: An instance of an AddItemEvent
        """
        super().__init__(IT.SILENT, self.States, self.States.DEFAULT)
        self.item_id = item_id
        self.item_quantity = item_quantity
        self.remaining_quantity = item_quantity
        self.player_ref: entities.Player = None
        self._build_states()

    def __str__(self) -> str:
        return (
            f"FiniteStateDevice::AddItemEvent::(item_id: {self.item_id}"
            f", item_quantity: {self.item_quantity})::{id(self)}"
        )

    def __copy__(self):
        return AddItemEvent(self.item_id, self.item_quantity)

    def __deepcopy__(self, memodict={}):
        return self.__copy__()

    def _build_states(self) -> None:
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, IT.SILENT)
        def logic(_: any) -> None:
            if self.player_ref is None:
                logger.debug("Setting player ref...")
                # Grab a weak reference to Player
                self.player_ref = weakref.proxy(cache.get_cache()["player"])

            # Detect collision
            if self.player_ref.inventory.is_collidable(self.item_id, self.remaining_quantity):
                logger.debug("Moving to PROMPT_KEEP_NEW_ITEM")
                # Make player choose to keep or drop new item
                self.set_state(self.States.PROMPT_KEEP_NEW_ITEM)
            else:
                logger.debug("MOVING TO INSERT_ITEM")
                self.set_state(self.States.INSERT_ITEM)  # Insert items
                logger.debug(f"{self.current_state}: {id(self)}")

        @FiniteStateDevice.state_logic(self, self.States.PROMPT_KEEP_NEW_ITEM, IT.AFFIRMATIVE)
        def logic(user_input: bool) -> None:
            if user_input:
                self.set_state(self.States.INSERT_ITEM)
            else:
                self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.PROMPT_KEEP_NEW_ITEM)
        def content() -> dict:
            c = [
                "Would you like to make room in your inventory for ",
                StringContent(value=f"{self.remaining_quantity}x ", formatting="item_quantity"),
                StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
                "?",
            ]
            return ComponentFactory.get(c)

        @FiniteStateDevice.state_logic(self, self.States.INSERT_ITEM, IT.ANY)
        def logic(_: any) -> None:
            self.remaining_quantity = self.player_ref.inventory.insert_item(self.item_id, self.item_quantity)

            if self.remaining_quantity > 0:
                self.set_state(self.States.PROMPT_KEEP_NEW_ITEM)
            else:
                self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSERT_ITEM)
        def content() -> dict:
            return ComponentFactory.get(
                [
                    "You added ",
                    StringContent(value=str(self.item_quantity), formatting="item_quantity"),
                    "x ",
                    StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
                    " to your inventory.",
                ]
            )

    @staticmethod
    @cache.cached([LoadableMixin.LOADER_KEY, "AddItemEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Required JSON fields:
        - item_id: int
        - item_quantity: int

        Optional JSON fields:
        - None
        """

        required_fields = [("item_id", int), ("item_quantity", int)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "AddItemEvent":
            raise ValueError("Invalid class field!")

        return AddItemEvent(json["item_id"], json["item_quantity"])
