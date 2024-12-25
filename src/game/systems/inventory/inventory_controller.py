from __future__ import annotations

import dataclasses
import weakref
from typing import Callable

import game.cache as cache
from game.structures.loadable import LoadableMixin
from game.structures.messages import StringContent

from loguru import logger


def get_default_capacity() -> int:
    return cache.get_config()["inventory"]["default_capacity"]


@dataclasses.dataclass
class Stack:
    id: int
    quantity: int

    def __post_init__(self):
        from game.systems.item.item import Item

        self.ref: Item = cache.from_cache("managers.ItemManager").get_ref(self.id)


class InventoryController(LoadableMixin):
    def __init__(self, capacity: int = None, items: list[tuple[int, int]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capacity: int = capacity
        self.fragmented: bool = False
        self.items: list[Stack] = []

        # We cannot query the cache for the default capacity on class definition
        # since there's no guarantee the config
        # will already be loaded.
        if not self.capacity:
            self.capacity = get_default_capacity()

        # Insert each stack of items. This process may re-arrange the index of
        # each stack.

        if items is not None:
            for t in items:
                if type(t) is list or type(t) is tuple:
                    self.insert_item(*t)
                else:
                    raise TypeError(f"Unknown type {type(t)} in inventory item_manifest!")

    # Private Methods
    def _all_stack_indexes(self, item_id: int) -> list[int]:
        """
        Returns a list of the indexes of all stacks with a matching item_id.

        Args:
            item_id: The ID to look up

        Returns: A list of indexes to valid stacks in the inventory
        """
        if type(item_id) is not int:
            raise TypeError(f"item_id must be an int! Got object of type {type(item_id)} instead.")

        return [idx for idx, stack in enumerate(self.items) if stack.id == item_id]

    def _all_stacks(self, item_id: int) -> list[Stack]:
        """
        Retrieve a list of references to each stack containing the designated item id
        """
        if type(item_id) is not int:
            raise TypeError(f"item_id must be an int! Got object of type {type(item_id)} instead.")

        return [weakref.proxy(stack) for stack in self.items if stack.id == item_id]

    def _consolidate_stacks(self):
        """
        Combine multiple non-full stacks of the same item_id into a single stack.
        """
        quantity_cache = {}

        for stack in self.items:
            if stack.id not in quantity_cache:
                quantity_cache[stack.id] = self.total_quantity(stack.id)

        self.items = []
        for item_id in quantity_cache:
            self.insert_item(item_id, quantity_cache[item_id])

    def total_quantity(self, item_id: int) -> int:
        """
        Computes the sum of the quantities of a given item in all available stacks.

        Args:
            item_id: The ID of the item whose sum to compute

        Returns: The total sum quantity of the item in the inventory
        """
        if type(item_id) is not int:
            raise TypeError(f"item_id must be an int! Got object of type {type(item_id)} instead.")

        return sum([s.quantity for s in self._all_stacks(item_id)])

    def filter_stacks(self, _filter: Callable) -> list[Stack]:
        """
        Returns a list of stacks that meet the conditions set in the _filter callable.

        Args:
            _filter: A callable that returns True or False based on the properties of an Item object

        Returns: A list of all stacks whose ref satisfies the filter
        """
        if not callable(_filter):
            return self.items

        return [stack for stack in self.items if _filter(stack.ref)]

    # Public Methods

    @property
    def full(self) -> bool:
        """
        A property the is True when the inventory has zero remaining slots for new stacks of items
        Returns: True when the inventory has zero remaining slots for new stacks of items, False otherwise

        """
        return len(self.items) >= self.capacity

    @property
    def size(self) -> int:
        """
        A property that returns the size of the inventory (total number of
        stacks).

        Returns: An int that represents the number of stacks currently in the
        inventory.
        """
        return len(self.items)

    def consume_item(self, item_id: int, quantity: int) -> bool:
        """
        Removes a specific quantity of item from the inventory. If there are not
         enough of the given item, return False
        Args:
            item_id: The id the of the item to consume
            quantity: The quantity of the given item to consume

        Returns: True if the quantity of item_id was consumed, False otherwise

        """
        if type(item_id) is not int or type(quantity) is not int:
            raise TypeError(
                f"item_id and quantity must be of type int! Got type " f"{type(item_id)} and {type(quantity)} instead."
            )

        if self.total_quantity(item_id) < quantity:
            return False

        already_consumed: int = 0
        while already_consumed < quantity:
            # If the loop is started over a list of zero stacks, raise an error
            # to avoid an infinite loop
            if len(self._all_stack_indexes(item_id)) < 1:
                raise ValueError(f"Something went wrong while trying to consume" f" item::{item_id}.")

            offset = 0
            for stack_index in self._all_stack_indexes(item_id):
                # If the current stack is bigger than needed, adjust its size
                # and return True
                if self.items[stack_index - offset].quantity > quantity - already_consumed:
                    self.items[stack_index - offset] = Stack(
                        item_id, self.items[stack_index - offset].quantity - (quantity - already_consumed)
                    )

                    self._consolidate_stacks()
                    return True

                # If the current stack is exactly the size needed, delete it and
                # return True
                elif self.items[stack_index - offset].quantity == quantity - already_consumed:
                    del self.items[stack_index - offset]
                    offset += 1

                    self._consolidate_stacks()
                    return True

                # If the stack is too small, record its size as consumed and
                # delete it.
                else:
                    already_consumed = already_consumed + self.items[stack_index - offset].quantity

                    del self.items[stack_index - offset]
                    offset += 1

    def __str__(self) -> str:
        buf = ""

        for (
            idx,
            stack,
        ) in self.items:
            buf = buf + f"[{idx}]: {stack.id}, x{stack.quantity}\n"

        return buf

    def __contains__(self, element: int | any) -> bool:
        from game.systems.item.item import Item

        if type(element) is not int and type(element) is not Item:
            logger.warning(f"Attempted to search inventory for object of type " f"{type(element)}")
            return False

        search_for = element if type(element) is int else element.id

        for i in self.items:
            if i.id == search_for:
                return True

        return False

    def __len__(self):
        return self.size

    def to_options(self, _filter: Callable = None) -> list[list[str | StringContent]]:
        results = []

        for stack in self.filter_stacks(_filter):
            results.append(
                [
                    StringContent(value=stack.ref.name, formatting="item_name"),
                    "\t",
                    StringContent(value=f"{stack.quantity}x", formatting="item_quantity"),
                ]
            )

        return results

    def drop_stack(self, stack_index: int) -> None:
        """
        Remove a stack from the inventory.

        Args:
            stack_index: The index of the stack within the player's inventory.
            Zero-indexed.

        Returns: None
        """

        if stack_index >= len(self.items):
            raise ValueError(
                f"Can't drop stack! {stack_index} is out of range," f" inventory is of size {len(self.items)}"
            )

        del self.items[stack_index]

    def is_collidable(self, item_id: int, quantity: int) -> bool:
        """
        Test if 'quantity' of an item with id=='item_id' can be inserted into
        the inventory without creating an overflow.

        Flow:
            - Calculate 'stacks * item.max_quantity' where 'stacks' is the
                number of empty slots in the inventory
            - Sum the amount of capacity remaining in each stack where
                stack.id == item_id
            - Sum those two values
            - Check if 'quantity' is greater than the sum. If so, the quantity
                of 'item_id' cannot be inserted without an overflow.

        Args:
            item_id: The id of the item to check against
            quantity: The quantity of the item to check against

        Returns: True if the user needs to resolve a collision, False otherwise
        """

        max_quantity = cache.from_cache("managers.ItemManager").get_ref(item_id).max_quantity
        remaining_cap: int = (self.capacity - len(self.items)) * max_quantity

        for stack in self._all_stacks(item_id):
            remaining_cap = remaining_cap + (stack.ref.max_quantity - stack.quantity)

        if quantity > remaining_cap:
            return True

        return False

    def new_stack(self, item_id: int, quantity: int, force: bool = False) -> int:
        """
        Creates a new stack in the inventory with the given item_id and
        item_quantity. If quantity > item.max_stack, return the difference.

        Args:
            item_id: The ID of the item to make the stack for
            quantity: the size of the stack
            force: If True, ignore capacity and make new stacks

        Returns: the amount of leftover items that didn't make it into the stack
        """

        if not force and self.full:
            return quantity

        from game.systems.item import item_manager

        leftover = quantity - item_manager.get_instance(item_id).max_quantity

        if leftover >= 0:
            self.items.append(Stack(item_id, item_manager.get_instance(item_id).max_quantity))
            return leftover

        self.items.append(Stack(item_id, quantity))
        return 0

    def insert_item(self, item_id: int, quantity: int) -> int:
        """
        Inserts 'quantity' of the item with id 'item_id' into the inventory.

        This process starts with filling up existing stacks of 'item_id' and
        then creating new stacks. The process terminates when the inventory
        becomes full or all items have been inserted, whichever comes first.

        Args:
            item_id: An int that represents the id of the item to insert
            quantity: The quantity of the item to insert

        Returns:
            An int that represents how many items were not inserted
        """

        remaining_quantity: int = quantity  # Set initial quantity
        max_stack_size: int = None

        # Insert items into existing stacks if possible
        for stack in self._all_stacks(item_id):
            max_stack_size = stack.ref.max_quantity

            if stack.quantity < max_stack_size:  # If stack is not full
                if remaining_quantity > (
                    max_stack_size - stack.quantity
                ):  # If num remaining items > capacity of the stack
                    remaining_quantity = remaining_quantity - (
                        max_stack_size - stack.quantity
                    )  # Reduce remaining quantity by the capacity of the stack
                    stack.quantity = max_stack_size  # Fill the stack
                else:  # If the entire remaining quantity can fit into the current stack
                    stack.quantity = stack.quantity + remaining_quantity  # Add rq to the stack
                    remaining_quantity = 0  # Set rq to zero
                    break  # Exit the loop

        # Look up max stack size if it wasn't already done
        if not max_stack_size:
            from game.systems.item import item_manager  # Any global-scoped import of item_manager circular imports

            max_stack_size = item_manager.get_ref(item_id).max_quantity

        # Attempt to make new stacks
        while not self.full and remaining_quantity > 0:
            # If there are too many items for a single stack
            if remaining_quantity >= max_stack_size:
                self.new_stack(item_id, max_stack_size)  # Make a maxed-out stack
                remaining_quantity = remaining_quantity - max_stack_size
            else:  # If All items can fit into a single stack
                self.new_stack(item_id, remaining_quantity)  # Make a stack of size 'remaining_quantity'
                remaining_quantity = 0

        return remaining_quantity  # Return the leftover quantity

    @staticmethod
    @cache.cached([LoadableMixin.LOADER_KEY, "InventoryController", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "InventoryController":
        """
        Instantiate an InventoryController object from a JSON blob.

        Args:
            json: a dict-form representation of an InventoryController object

        Returns: an InventoryController instance with the properties defined in the JSON

        Required JSON fields:
        - manifest: [[int, int]]

        Optional JSON fields:
        - capacity: int
        """

        class_key = "InventoryController"
        manifest_key = "manifest"

        # Type and field checking
        required_fields = [manifest_key]
        for field in required_fields:
            if field not in json:
                raise ValueError(f"Required field {field} not in JSON!")

        if json["class"] != class_key:
            raise ValueError(f"Cannot load JSON for object of class {json['class']}")

        if type(json[manifest_key]) is not list:
            raise TypeError(f"Cannot parse item manifest of type {type(json[manifest_key])}! Expect type list")

        capacity = json["capacity"] if ("capacity" in json) else get_default_capacity()

        inv = InventoryController(capacity, json[manifest_key])
        return inv
