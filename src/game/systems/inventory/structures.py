from __future__ import annotations
from dataclasses import dataclass
from game.cache import from_cache
from game.structures.messages import StringContent

from loguru import logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.systems.item.item import Equipment


@dataclass
class EquipSlot:
    """
    A simple dataclass for storing the properties of an equipment slot.
    """

    name: str  # Name of the slot
    item_id: int | None  # ID of the item placed in the slot
    enabled: bool  # If the slot is allowed to be used

    def unlock(self) -> None:
        """
        Enables the slot.
        """
        if self.enabled:
            logger.warning(f"Slot {self.name} was already enabled!")
        self.enabled = True

    def as_option(self) -> list[str | StringContent]:
        """
        Return a list of strings intended to be included in the `options` field
         of a Frame. Includes the slot's name and the name of the item in the
         slot.
        """
        return [
            self.name,
            ": ",
            from_cache("managers.ItemManager").get_instance(self.item_id).name if self.item_id is not None else "Empty",
        ]

    @property
    def instance(self) -> Equipment | None:
        """
        Get an instance of the Equipment in the slot.

        returns: An Equipment instance or None if the slot is empty.
        """
        if self.item_id is None:
            return None

        return from_cache("managers.ItemManager").get_instance(self.item_id)
