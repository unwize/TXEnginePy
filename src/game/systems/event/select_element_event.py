from __future__ import annotations

from enum import Enum
from typing import Callable, Iterable

from game.cache import request_storage_key, store_element, from_cache, loader
from game.structures.enums import InputType
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.event import Event


class SelectElementEvent(Event):
    """
    A generic Event that allows the user to select an element from a list of
    potential elements.

    Args:
        collection:
            The items from which to select an element
        key:
            A callable that takes in the selected element and returns the
            key to store in storage
        element_filter:
            A callable that returns True if the element should be shown to
            the user, False otherwise
        to_listing:
            A callable that takes in an element from the collection and
            returns a str to show the user
        prompt:
            The text to show the user above the list of elements
        must_select:
            If True, the user must select an element. If False, a -1 ->
            terminate option will exist.
    """

    class States(Enum):
        """
        An internal state Enum
        """

        DEFAULT = 0
        SHOW_ELEMENTS = 1
        TERMINATE = -1

    def __init__(
        self,
        collection: list,
        key: Callable,
        element_filter: Callable = None,
        to_listing: Callable = str,
        prompt: str = "Choose an element",
        must_select: bool = True,
    ):
        super().__init__(default_input_type=InputType.SILENT, states=self.States, default_state=self.States.DEFAULT)

        self._element_filter: Callable = element_filter
        self._collection: list = collection
        self._key: Callable = key

        # A pre-built dict to hold storage keys
        self._storage_keys: dict[str, any] = {"selected_element": None}

        self._prompt: str = prompt
        self._to_listing: Callable = to_listing
        self._must_select: bool = must_select

        # Temp values
        self.__filtered_collection: list | None = None
        self.__filtered_collection_len: int | None = None

        if len(self._collection) < 1:
            raise RuntimeError("Cannot instantiate a SelectElementEvent with a collection of " "size 0!")

        self._setup_states()

    def _link(self) -> dict[str, str]:
        """
        Override default link logic to store
        """
        # Storage key for the selected element data
        self._storage_keys["selected_element"] = request_storage_key()
        return self._storage_keys

    def _setup_states(self) -> None:
        # DEFAULT
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            # Check for a filter and use it if available
            if self._element_filter is not None:
                self.__filtered_collection = [element for element in self._collection if self._element_filter(element)]
            else:
                self.__filtered_collection = self._collection

            # Pre-compute len of remaining items
            self.__filtered_collection_len = len(self.__filtered_collection)

            # Check for broken collections
            if self.__filtered_collection_len < 1:
                raise RuntimeError("SelectElementEvent cannot have a filtered collection size " "of 0!")
            self.set_state(self.States.SHOW_ELEMENTS)

        # SHOW_ELEMENTS
        @FiniteStateDevice.state_logic(
            self,
            self.States.SHOW_ELEMENTS,
            InputType.INT,
            input_min=0 if self._must_select else -1,
            input_max=lambda: int(self.__filtered_collection_len) - 1,
        )
        def _logic(user_input: int) -> None:
            """
            If the user chooses to 'go back' via entering -1, None will be
            stored. Otherwise, the _key transformation will occur and the
            resulting value will be stored.
            """
            if user_input == -1 and not self._must_select:
                store_element(self._storage_keys["selected_element"], None)
            else:
                store_element(self._storage_keys["selected_element"], self._key(self.__filtered_collection[user_input]))

            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.SHOW_ELEMENTS)
        def _content():
            return ComponentFactory.get([self._prompt], [self._to_listing(e) for e in self.__filtered_collection])

    @staticmethod
    @loader("SelectElementEvent")
    def from_json(json: dict[str, any]) -> any:
        raise RuntimeError("Loading SelectElementEvent from JSON is not supported!")


class SelectElementEventFactory:
    @classmethod
    def get_select_ability_event(
        cls, combat_entity, only_requirements_met: bool = False, must_select: bool = True
    ) -> SelectElementEvent:
        """
        Get a SelectElementEvent that is configured to choose an Ability from a
        list of learned abilities of a given CombatEntity.

        args:
            entity:
                The CombatEntity who's abilities to inspect
            only_requirements_met:
                If True, filter abilities based on which ones can actually be
                used
            must_select:
                If True, force a selection. If false, allow an input of -1 to
                terminate the Event
        """
        ability_filter = None

        # If only_castable is True, create an inner function to act as the
        # filter.
        if only_requirements_met is True:

            def test_for_usable_ability(ability_name) -> bool:
                """
                Access the AbilityManager to get an instance of the Ability,
                then test its requirements against the given CombatEntity.
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
            must_select=must_select,
        )

        return event

    @classmethod
    def get_select_usable_item_event(
        cls,
        combat_entity,
        collection_override: any = None,
        only_requirements_met: bool = False,
        must_select: bool = False,
    ):
        """
        Get a SelectElementEvent pre-configured to select a Usable (Item).

        The returned Event is configured to only display items of type Usable,
        and can optionally be set to only display Usable items that have their
        Requirements met by the combat_entity.

        args:
            entity:
                The entity whose inventory the Usable should be selected from
            collection:
                A list of item ids from which to select a Usable. When not None,
                this collection is selected from instead of the entity's
                inventory
            only_requirements_met:
                If True, filter for Usable items that can be used by the entity
            must_select:
                If True, do not allow for a -1 input that terminates the Event
        """

        if combat_entity is not None:
            from game.systems.entity.entities import CombatEntity

            if not isinstance(combat_entity, CombatEntity):
                raise TypeError("combat_entity must be an instance of CombatEntity!")
        else:
            raise TypeError("combat_entity cannot be None!")

        # If no collection override is supplied, used the inventory in the
        # combat_entity
        # In all cases, translate the passed data structure into a list of
        # id-quantity tuples
        collection: list[tuple[int, int]] | None = None

        from game.systems.entity.mixins.inventory_mixin import InventoryMixin

        if collection_override is None:
            collection = [(stack.id, stack.quantity) for stack in combat_entity.inventory.items]

        # If a collection override with an inventory is passed, use its
        # inventory instead
        elif isinstance(collection_override, InventoryMixin):
            collection = [(stack.id, stack.quantity) for stack in collection_override.inventory.items]

        # If a list-tuple override is passed, check its contents and then use it
        elif isinstance(collection_override, list):
            if len(collection_override) < 1:
                raise ValueError("list typed collection overrides must be of size > 0")
            if (
                not isinstance(collection_override[0], tuple)
                or not isinstance(collection_override[0][0], int)
                or not isinstance(collection_override[0][1], int)
            ):
                raise ValueError("list typed collection overrides must only contain objects " "of type tuple[int, int]")
            collection = collection_override

        # Define an inner-function to handle translating the tuple to a str
        def to_listing(stack_tuple: tuple[int, int]) -> str:
            """
            Translate an id-stack tuple into a string with
            item.name xitem.quantity
            """
            instance = from_cache("managers.ItemManager").get_instance(stack_tuple[0])
            return f"{instance.name}\tx{stack_tuple[1]}"

        def usable_filter(stack_tuple: tuple[int, int]):
            instance = from_cache("managers.ItemManager").get_instance(stack_tuple[0])

            from game.systems.item.item import Usable

            if not isinstance(instance, Usable):
                return False

            if only_requirements_met is True and (not instance.is_requirements_fulfilled(combat_entity)):
                return False

            return True

        event = SelectElementEvent(
            collection=collection,
            key=lambda stack_tuple: stack_tuple[0],  # Get item.id from stack
            element_filter=usable_filter,
            prompt="Select an item to use:",
            to_listing=to_listing,
            must_select=must_select,
        )

        return event

    @classmethod
    def get_select_entity_event(
        cls,
        collection: list,
        fields_of_interest: tuple[str] = None,
        allow_player: bool = False,
        must_select: bool = False,
    ):
        """
        Get a SelectElementEvent pre-configured to select an Entity.

        Event may be optionally configured to dynamically inject variable values
        via `fields_of_interest` into the internal `to_listing` function.
        For example, an entity's ID could be inserted by passing [`id`] to the
        argument.

        Args:
            collection:
                A list of Entity objects from which to select
            fields_of_interest: tuple[str]:
                A collection of variable names to inject into the to_listing
                function.
            allow_player: bool: If False, filter out any objects of class Player
            must_select:
                If True, do not allow for a -1 input that terminates the Event.
                If False, an input of -1
        Returns: None
        """

        if not isinstance(collection, list):
            raise TypeError()

        if not isinstance(must_select, bool):
            raise TypeError()

        foi = fields_of_interest or tuple(["name"])

        from game.systems.entity.entities import Entity, Player

        # Define an inner-function to handle translating the entities to strings
        def to_listing(entity: Entity) -> str:
            if not isinstance(entity, Entity):
                raise TypeError(f"Cannot translate object of type {type(entity)}" f", expecting object of type Entity!")

            field_values = []

            for field in foi:
                if hasattr(entity, field):
                    field_values.append(getattr(entity, field))
                else:
                    raise RuntimeError(f"Entity {entity} has no field {field}!")

            return " ".join(field_values)

        event = SelectElementEvent(
            collection=collection,
            key=lambda e: e,
            element_filter=None if allow_player else lambda e: not isinstance(e, Player),
            prompt="Select an Entity",
            to_listing=to_listing,
            must_select=must_select,
        )

        return event

    @classmethod
    def get_select_equipment_event(
        cls,
        collection: list,
        only_requirements_met: bool = False,
        fields_of_interest: Iterable[str] = tuple(["name"]),
        must_select: bool = False,
    ):
        """
        Get a SelectElementEvent pre-configured to select an Entity.

        Event may be optionally configured to dynamically inject variable values
        via `fields_of_interest` into the internal `to_listing` function.
        For example, an entity's ID could be inserted by passing [`id`] to the
        argument.

        Args:
            collection:
                A list of Entity objects from which to select
            only_requirements_met:
                If True only show equipment that the player is qualified to use
            fields_of_interest: tuple[str]:
                A collection of variable names to inject into the to_listing
                function.
            must_select:
                If True, do not allow for a -1 input that terminates the Event.
                If False, an input of -1
        Returns: A pre-configured SelectElementEvent object that filters for
        equipment from an Inventory.
        """

        if not isinstance(collection, list):
            raise TypeError()

        if not isinstance(only_requirements_met, bool):
            raise TypeError()

        if not isinstance(must_select, bool):
            raise TypeError()

        if not hasattr(fields_of_interest, "__iter__"):
            raise TypeError()

        from game.systems.item.item import Equipment

        # Define an inner-function to handle translating Equipment to strings
        def to_listing(equipment: Equipment) -> str:
            if not isinstance(equipment, Equipment):
                raise TypeError(
                    f"Cannot translate object of type {type(equipment)}" f", expecting object of type Equipment!"
                )

            field_values = []

            for field in fields_of_interest:
                if hasattr(equipment, field):
                    field_values.append(getattr(equipment, field))
                else:
                    raise RuntimeError(f"Equipment {equipment} has no field {field}!")

            return " ".join(field_values)

        event = SelectElementEvent(
            collection=collection,
            key=lambda e: e,
            element_filter=None
            if not only_requirements_met
            else lambda e: e.is_requirements_fulfilled(from_cache("player")),
            prompt="Select an Equipment",
            to_listing=to_listing,
            must_select=must_select,
        )

        return event
