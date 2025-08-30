from __future__ import annotations

from loguru import logger

import game
from game.cache import get_cache, cached, from_cache
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.systems.inventory.structures import EquipSlot


class EquipmentController(LoadableMixin):
    """
    An EquipmentController's duties are to manage the items that an
    entities.Entity equips. This includes handling the equipping and unequipped
     processes, validating that an item is allowed to fit into a slot.

    An instance of EquipmentController can behave in one of two ways: PlayerMode
    and EntityMode. While in PlayerMode, all attempts to equip equipment are
    checked against that item's Requirements. While in EntityMode, Requirements
    are ignored.
    """

    def __init__(self, owner=None, equipment: list[int] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.player_mode: bool = False
        self._slots: dict[str, EquipSlot] = get_cache()["managers"]["EquipmentManager"].get_slots()

        # If the equipment list is not None
        if equipment is not None and isinstance(equipment, list):
            # For each equipment id
            for item_id in equipment:
                from game.systems.item.item import Equipment

                inst = from_cache("managers.ItemManager").get_instance(item_id)
                if not isinstance(inst, Equipment):
                    raise TypeError(
                        "Cannot instantiate a EquipmentController"
                        "with items not of type Equipment! Got "
                        f"object of type  {type(inst)}."
                    )

                if not self._slots[inst.slot].enabled:
                    logger.error(f"Failed to equip item with id: {item_id}")
                    raise RuntimeError("Cannot equip item to disabled slot!")

                if self._slots[inst.slot].item_id is not None:
                    logger.error(f"Failed to equip item with id: {item_id}")
                    raise RuntimeError("Cannot equip item to occupied slot")

                self.equip(item_id)

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

        # If value is a bool, treat is an enable/disable slot
        if type(value) is bool:
            self._slots[key].enabled = value

        # If an int, treat it as set-id
        elif type(value) is int:
            from game.systems.item import item_manager

            ref = item_manager.get_ref(value)

            from game.systems.item.item import Equipment

            if not isinstance(ref, Equipment):
                raise ValueError(f"Cannot assign item {str(ref)} to slot {key}! Item {str(ref)} is not an Equipment!")

            if ref.slot != key:
                raise ValueError(f"Cannot assign item {str(ref)} to slot {key}! Wrong slot! {key} != {ref.slot}")

            self._slots[key].item_id = value

        # If None, treat it as clear-slot
        elif value is None:
            self._slots[key].item_id = value

        # That's not right
        else:
            raise TypeError(f"Unknown type for value! Expected int, bool, or None. Got {type(value)}!")

    def equip(self, item_id: int) -> bool:
        """
        Pops the item currently in the slot for the item and returns its ID,
        then sets slot's id to item_id

        args:
            item_id: The ID of the item to equip

        returns: True if the slot is enabled, false otherwise
        """
        from game.systems.item import item_manager

        item_ref = item_manager.get_ref(item_id)

        from game.systems.item.item import Equipment

        if isinstance(item_ref, Equipment):
            if not self._slots[item_ref.slot].enabled:
                raise RuntimeError(
                    f"Cannot equip {item_ref.name} to slot {item_ref.slot} since slot {item_ref.slot} is disabled."
                )

            # If operating in player mode, check for quantity and requirements
            if self.player_mode:
                if not item_ref.is_requirements_fulfilled(self._owner):
                    return False

                if self._owner.inventory.total_quantity(item_ref.id) < 1:
                    return False

                # Consume item from inventory before equipping
                self._owner.inventory.consume_item(item_ref.id, 1)

            self.unequip(item_ref.slot)  # Attempt to unequip existing item
            self[item_ref.slot] = item_id  # Set slot id to item id

            return True

        raise TypeError(f"Cannot equip item of type {type(item_ref)}! Expected item of type Equipment")

    def unequip(self, slot: str) -> bool:
        """
        Remove the item from a slot and return its ID

        args:
            slot: The name of the slot to empty

        returns: True if the slot is enabled, false otherwise
        """

        if not get_cache()["managers"]["EquipmentManager"].is_valid_slot(slot):
            raise ValueError(f"Unknown slot: {slot}!")

        if not self._slots[slot].enabled:
            return False

        temp = self[slot].item_id

        # Add-item-event to handle moving the item back in player inventory
        if self.player_mode and temp is not None:
            from game.systems.event.add_item_event import AddItemEvent

            game.add_state_device(AddItemEvent(temp, 1))
        elif not self.player_mode and temp is not None:
            self.owner.inventory.new_stack(temp, 1)

        self[slot] = None
        return True

    def get_equipment_as_options(self) -> list[list[str | StringContent]]:
        """
        Get a list of lists intended to be passed as an `options` JSON field in
        a Frame. Content of the lists describes each Equipment.
        """

        return [self._slots[slot].as_option() for slot in self._slots]

    @property
    def owner(self) -> any:
        return self._owner

    @owner.setter
    def owner(self, entity) -> None:
        """
        The Entity instance that encapsulates this object. Check if the Entity
        is an instance of Player and set player_mode accordingly.
        """
        from game.systems.entity import Entity, Player

        if entity is not None and not isinstance(entity, Entity):
            raise TypeError(f"Cannot assign an owner of type {type(entity)}, owner must of type entities.Entity")

        elif isinstance(entity, Player):
            self._owner = entity
            self.player_mode = True

        else:
            self._owner = entity
            self.player_mode = False

    @property
    def enabled_slots(self) -> list[str]:
        return [slot for slot in self._slots if self._slots[slot].enabled]

    @property
    def total_dmg_resistance(self) -> int:
        """
        Calculate and return the total resistance of equipment attached to the
        entity in all enabled slots
        """
        instances = [
            from_cache("managers.ItemManager").get_instance(s.item_id)
            for s in self._slots.values()
            if (s.enabled and s.item_id is not None)
        ]

        return sum([e.damage_resist for e in instances])

    @property
    def total_dmg_buff(self) -> int:
        """
        Calculate and return the total resistance of equipment attached to the
        entity in all enabled slots
        """
        instances = [
            from_cache("managers.ItemManager").get_instance(s.item_id)
            for s in self._slots.values()
            if (s.enabled and s.item_id is not None)
        ]

        return sum([e.damage_buff for e in instances])

    @property
    def all_tag_resistance(self) -> dict[str, list[float]]:
        """
        Collect and return lists of tag resistances from all enabled slots
        """

        instances = [
            from_cache("managers.ItemManager").get_instance(s.item_id)
            for s in self._slots.values()
            if s.enabled and s.item_id is not None
        ]
        total_tags: dict[str, list[float]] = {}
        for equipment in instances:
            for tag, value in equipment.tags.items():
                if tag not in total_tags:
                    total_tags[tag] = []

                total_tags[tag].append(equipment.tags[tag])

        return total_tags

    @property
    def sum_tag_resistance(self) -> dict[str, float]:
        """
        Collect and return a dict mapping the name of a tag to the total
        resistance associated with that tag.

        Returns: A dict containing the total resistance for each given tag
        """

        from game.systems.combat.combat_engine.combat_helpers import sum_a_tag

        total_resistances: dict[str, float] = {}

        for tag in self.all_tag_resistance:
            total_resistances[tag] = sum_a_tag(self.all_tag_resistance[tag])

        return total_resistances

    def get_tag_resistances_as_options(self) -> list[list[str | StringContent]]:
        """
        Generate info about the total tag resistances across all items.

        Returns:a list of lists containing style-formatted strings
        """

        opts = []

        for tag, value in self.sum_tag_resistance.items():
            opts.append([StringContent(value=tag, formatting="equipment_tag"), ": ", value])

        return opts

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "EquipmentController", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "EquipmentController":
        class_key: str = "EquipmentController"
        slots_key: str = "slots"

        # Type and field checking
        required_fields = [("slots", dict)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != class_key:
            raise ValueError(f"Cannot load JSON for object of class {json['class']}")

        ec = EquipmentController()

        # Equip each slot
        for slot in json[slots_key]:
            ec.equip(json[slots_key][slot])

        return ec
