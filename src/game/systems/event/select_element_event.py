from __future__ import annotations

from enum import Enum
from typing import Callable

from loguru import logger

from game.cache import request_storage_key, store_element, cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.event import Event


class SelectElementEvent(Event):
    class States(Enum):
        DEFAULT = 0
        SHOW_ELEMENTS = 1
        PROCESS_CHOICE = 2
        TERMINATE = -1

    def __init__(self, collection: list, key: Callable, element_filter: Callable = None,
                 to_listing: Callable = str, prompt: str = "Choose an element", must_select: bool = True):
        super().__init__(default_input_type=InputType.SILENT, states=self.States, default_state=self.States.DEFAULT)
        """
        A generic Event that allows the user to select an element from a list of potential elements.
        
        args:
            - collection: The items from which to select an element
            - key: A callable that takes in the selected element and returns the key to store in storage
            - element_filter: A callable that returns True if the element should be shown to the user, False otherwise
            - to_listing: A callable that takes in an element from the collection and returns a str to show the user
            - prompt: The text to show the user above the list of elements
            - must_select: If True, the user must select an element. If False, a -1 -> terminate option will exist.
        """
        self._element_filter: Callable = element_filter
        self._collection: list = collection
        self._key: Callable = key
        self._storage_keys: dict[str, any] = {"selected_element": None}  # A pre-built dict to hold storage keys
        self._prompt: str = prompt
        self._to_listing: Callable = to_listing
        self._must_select: bool = must_select

        # Temp values
        self.__filtered_collection: list | None = None
        self.__filtered_collection_len: int | None = None

        if len(self._collection) < 1:
            raise RuntimeError("Cannot instantiate a SelectElementEvent with a collection of size 0!")

        self._setup_states()

    def _link(self) -> dict[str, str]:
        """
        Override default link logic to store
        """
        self._storage_keys["selected_element"] = request_storage_key()  # Storage key for the selected element data
        return self._storage_keys

    def _setup_states(self) -> None:
        # DEFAULT
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def logic(_: any) -> None:

            # Check for a filter and use it if available
            if self._element_filter is not None:
                self.__filtered_collection = [element for element in self._collection if self._element_filter(element)]
            else:
                self.__filtered_collection = self._collection

            # Pre-compute len of remaining items
            self.__filtered_collection_len = len(self.__filtered_collection)

            # Check for broken collections
            if self.__filtered_collection_len < 1:
                raise RuntimeError("SelectElementEvent cannot have a filtered collection size of 0!")
            self.set_state(self.States.SHOW_ELEMENTS)

        @FiniteStateDevice.state_content(self, self.States.DEFAULT)
        def content():
            return ComponentFactory.get()

        # SHOW_ELEMENTS
        @FiniteStateDevice.state_logic(self, self.States.SHOW_ELEMENTS, InputType.INT,
                                       input_min=0 if self._must_select else -1,
                                       input_max=lambda: int(self.__filtered_collection_len) - 1)
        def logic(user_input: int) -> None:
            """
            If the user chooses to 'go back' via entering -1, None will be stored. Otherwise, the _key transformation
            will occur and the resulting value will be stored.
            """
            if user_input == -1 and not self._must_select:
                store_element(self._storage_keys['selected_element'], None)
            else:
                store_element(self._storage_keys['selected_element'], self._key(self.__filtered_collection[user_input]))

            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.SHOW_ELEMENTS)
        def content():
            return ComponentFactory.get([self._prompt],
                                        [self._to_listing(e) for e in self.__filtered_collection])

        # PROCESS_CHOICE
        @FiniteStateDevice.state_logic(self, self.States.PROCESS_CHOICE, InputType.SILENT)
        def logic(_: any) -> None:
            pass

        @FiniteStateDevice.state_content(self, self.States.PROCESS_CHOICE)
        def content():
            return ComponentFactory.get()

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "SelectElementEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        raise RuntimeError("Loading SelectElementEvent from JSON is not supported!")


class SelectElementEventFactory:

    @classmethod
    def get_select_ability_event(cls, combat_entity,
                                 only_requirements_met: bool = False,
                                 must_select: bool = True) -> SelectElementEvent:
        """
        Get a SelectElementEvent that is configured to choose an Ability from a list of learned abilities of a given
        CombatEntity.

        args:
            entity: The CombatEntity who's abilities to inspect
            only_requirements_met: If True, filter abilities based on which ones can actually be used
            must_select: If True, force a selection. If false, allow an input of -1 to terminate the Event
        """
        ability_filter = None

        # If only_castable is True, create an inner function to act as the filter.
        if only_requirements_met is True:
            def test_for_usable_ability(ability_name) -> bool:
                """
                Access the AbilityManager to get an instance of the Ability, then test its requirements against the
                given CombatEntity.
                """
                inst = from_cache("managers.AbilityManager").get_instance(ability_name)
                print(inst)
                return inst.is_requirements_fulfilled(combat_entity)

            ability_filter = test_for_usable_ability

        abilities = list(combat_entity.ability_controller.abilities)
        abilities.sort()
        event = SelectElementEvent(
            collection=abilities,
            key=lambda x: str(x),
            element_filter=ability_filter,
            prompt="Select an ability:",
            must_select=must_select
        )

        return event

    @classmethod
    def get_select_usable_item_event(cls, combat_entity, collection_override: any = None,
                                     only_requirements_met: bool = False,
                                     must_select: bool = False):
        """
        Get a SelectElementEvent pre-configured to select an Usable (Item). The returned Event is configured to only
        display items of type Usable, and can optionally be set to only display Usable items that have their
        Requirements met by the combat_entity

        args:
            entity: The entity who's inventory the Usable should be selected from
            collection: A list of item ids from which to select a Usable. When not None, this collection is selected
                        from instead of the entity's inventory
            only_requirements_met: If True, filter for Usable items that can be used by the entity
            must_select: If True, do not allow for a -1 input that terminates the Event
        """

        if combat_entity is not None:
            from game.systems.entity.entities import CombatEntity
            if not isinstance(combat_entity, CombatEntity):
                raise TypeError("combat_entity must be an instance of CombatEntity!")
        else:
            raise TypeError("combat_entity cannot be None!")

        # If no collection override is supplied, used the inventory in the combat_entity
        # In all cases, translate the passed data structure into a list of id-quantity tuples
        collection: list[tuple[int, int]] = None

        from game.systems.entity.entities import InventoryMixin
        if collection_override is None:
            collection = [(stack.id, stack.quantity) for stack in combat_entity.inventory.items]

        # If a collection override with an inventory is passed, use its inventory instead
        elif isinstance(collection_override, InventoryMixin):
            collection = [(stack.id, stack.quantity) for stack in collection_override.inventory.items]

        # If a list-tuple override is passed, check its contents and then use it
        elif type(collection_override) == list:
            if len(collection_override) < 1:
                raise ValueError("list typed collection overrides must be of size > 0")
            if type(collection_override[0]) != tuple or type(collection_override[0][0]) != int or type(
                    collection_override[0][1]) != int:
                raise ValueError("list typed collection overrides must only contain objects of type tuple[int, int]")
            collection = collection_override

        # Define an inner-function to handle translating the tuple to a str-listing
        def to_listing(stack_tuple: tuple[int, int]) -> str:
            """Translate an id-stack tuple into a string with item.name   xitem.quantity"""
            return f"{from_cache('managers.ItemManager').get_instance(stack_tuple[0]).name}\tx{stack_tuple[1]}"

        def usable_filter(stack_tuple: tuple[int, int]):

            instance = from_cache("managers.ItemManager").get_instance(stack_tuple[0])

            from game.systems.item.item import Usable
            if not isinstance(instance, Usable):
                return False

            if only_requirements_met is True and not instance.is_requirements_fulfilled(combat_entity):
                return False

            return True

        event = SelectElementEvent(
            collection=collection,
            key=lambda stack_tuple: stack_tuple[0],  # Extract item.id from inventory stack
            element_filter=usable_filter,
            prompt="Select an item to use:",
            to_listing=to_listing,
            must_select=must_select
        )

        return event
