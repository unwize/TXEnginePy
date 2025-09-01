from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from loguru import logger

from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.util.asset_utils import get_asset

if TYPE_CHECKING:
    from game.systems.inventory.structures import EquipSlot


class EquipmentManager(Manager):
    """
    The EquipmentManager's duties are to load and distribute data about
    different equipment slots.

    A game developer may want to add or remove equipment slots to their game
    and can do so through the equipment manager.
    """

    SLOT_ASSET_PATH = "equipment_slots"

    def __init__(self):
        super().__init__()
        self._slots: dict[str, EquipSlot] = {}

    def __contains__(self, item: str) -> bool:
        return self._slots.__contains__(item)

    def __getitem__(self, item: str) -> EquipSlot:
        return self._slots.__getitem__(item)

    def __setitem__(self, key: str, value: bool | int | None) -> None:
        """
        A wrapper for EquipmentManager::_slots::__set_item__.

        If the value passed is of type bool, it is assumed that this value is
        intended for the SlotProperties::enabled field. If the value is of type
        int or None, it is assumed that this value is intended for the
        SlotProperties::item_id field.
        """

        if key not in self._slots:
            raise KeyError(f"Unknown slot: {key}!")

        if type(value) is bool:
            self._slots[key].enabled = value

        elif type(value) is int or value is None:
            self._slots[key].item_id = value

        else:
            raise TypeError(f"Unknown type for value! Expected int, bool, or None. Got {type(value)}!")

    def register_slot(
        self, instance: EquipSlot = None, name: str = None, item_id: int | None = None, enabled: bool = True
    ) -> None:
        """
        Registers a new slot with the EquipmentManager.

        Pass either an instance of EquipSlot or a `name` value. If a `name` value is passed, `item_id` and `enabled` may also
        be passed.
        """

        from game.systems.inventory.structures import EquipSlot

        # Handle registering instance
        if isinstance(instance, EquipSlot):
            if instance.name in self._slots:
                logger.error(f"Failed to register slot {instance.name}: A slot with that name already exists!")
                raise RuntimeError(f"Failed to register slot {instance.name}!")

            self._slots[instance.name] = instance

        # Handle registering by name
        else:
            if not isinstance(name, str):
                raise TypeError()

            if item_id is not None and not isinstance(item_id, int):
                raise TypeError()

            if not isinstance(enabled, bool):
                raise TypeError()

            self._slots[name] = EquipSlot(name, item_id, enabled)

    def get_slots(self) -> dict:
        """
        Get a deep copy of the slot properties for each slot.
        """
        return copy.deepcopy(self._slots)

    def is_valid_slot(self, slot: str) -> str:
        """
        Validates that a given slot key exists. If it does, return the slot.
        Otherwise, raise an Error.

        args:
            slot: The slot key to validate

        returns: `slot` if `slot` exists
        """
        if slot in self._slots:
            return slot

        raise ValueError(f"Slot {slot} does not exist! Possible slots are {','.join(list(self._slots.keys()))}")

    def load(self) -> None:
        """
        Load item game objects from disk.
        """
        raw_asset: dict[str, any] = get_asset(self.SLOT_ASSET_PATH)
        for raw_slot in raw_asset["content"]:
            slot = LoadableFactory.get(raw_slot)

            from game.systems.inventory.structures import EquipSlot

            if not isinstance(slot, EquipSlot):
                raise TypeError(f"Expected object of type EquipSlot, got {type(slot)} instead!")

            self.register_slot(slot)

    def save(self) -> None:
        pass
