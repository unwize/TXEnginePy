from __future__ import annotations
import copy
import weakref

from typing import TYPE_CHECKING

from loguru import logger

from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.systems import currency as currency
from game.util.asset_utils import get_asset

if TYPE_CHECKING:
    from game.systems.item.item import Item


class ItemManager(Manager):
    """
    The global manager for Item objects. Stores master copies of all instances
    of Item objects, creates copies, and handles IO for Item assets at load
    time.
    """

    ITEM_ASSET_PATH = "items"

    def __init__(self):
        super().__init__()
        self._manifest: dict[int, Item] = {}

    def register_item(self, item_object: Item | list[Item]) -> None:
        """
        Register an item object with the ItemManager.
        """

        from game.systems.item.item import Item

        if isinstance(item_object, Item):
            if item_object.id in self._manifest:
                raise ValueError(f"Item with ID {item_object.id} already registered!")

            self._manifest[item_object.id] = item_object

        elif isinstance(item_object, list):
            for obj in item_object:
                self.register_item(obj)
        else:
            raise TypeError(f"Expected object of type Item or type list[Item], got type {type(item_object)} instead.")

    def get_name(self, item_id: int) -> str:
        return self._manifest[item_id].name

    def get_desc(self, item_id: int) -> str:
        return self._manifest[item_id].description

    def get_currency_values(self, item_id: int) -> dict[int, int]:
        """
        Get the value of an item in all currencies

        Args:
            item_id: The ID of the item whose value to retrieve

        Returns: A dict that maps an items value in a specific currency to
        that currency's id
        """

        return self._manifest[item_id]._market_values

    def get_currency_value(self, item_id: int, currency_id: int, as_currency: bool = False) -> int | currency.Currency:
        """
        Get the value of an item in a specific currency

        Args: item_id: The ID of the item to look up currency_id: The ID of
        the currency to look up as_currency: If True, return an instance of a
        currency instead of an int

        Returns: An int value representing the item's cost in currency
        'currency_id'
        """
        if not as_currency:
            return self._manifest[item_id].trade_values[currency_id]
        else:
            return self._manifest[item_id].get_market_value(currency_id)

    def get_instance(self, item_id: int) -> Item:
        """
        Create and return a deep-copied instance of the item with item.id ==
        'item_id'

        Args:
            item_id: The ID of the item whose instance to create

        Returns: A deep copy of the requested item
        """
        if type(item_id) is not int:
            raise TypeError(f"Item IDs must be of type int! Got {type(item_id)} instead.")

        if item_id not in self._manifest:
            raise ValueError(f"No such item with ID {item_id}!")

        return copy.deepcopy(self._manifest[item_id])

    def get_ref(self, item_id: int) -> Item:
        """
        Get a direct reference to the master object copy stored in the
        ItemManager.

        Use sparingly.
        """
        if type(item_id) is not int:
            raise TypeError(f"Item IDs must be of type int! Got {type(item_id)} instead.")

        if item_id not in self._manifest:
            logger.error(f"ItemManager @ {self.__repr__()} failed to find item with ID {item_id}")
            logger.error(self._manifest)
            raise ValueError(f"No such item with ID {item_id}!")

        return weakref.proxy(self._manifest[item_id])

    def load(self) -> None:
        """
        Load item game objects from disk.
        """
        raw_asset: dict[str, any] = get_asset(self.ITEM_ASSET_PATH)
        for raw_item in raw_asset["content"]:
            item = LoadableFactory.get(raw_item)

            from game.systems.item.item import Item

            if not isinstance(item, Item):
                raise TypeError(f"Expected object of type Ability, got {type(item)} instead!")

            self.register_item(item)

    def save(self) -> None:
        pass
