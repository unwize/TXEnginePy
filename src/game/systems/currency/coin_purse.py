from __future__ import annotations
from typing import TYPE_CHECKING

import dataclasses
from typing import Iterator

from game.cache import cached, from_cache
from game.structures.loadable import LoadableMixin
from game.systems.currency import Currency
from game.systems.currency import currency_manager

if TYPE_CHECKING:
    from game.systems.item.item import Item


@dataclasses.dataclass
class CoinPurse(LoadableMixin):
    currencies: dict[int, Currency] = dataclasses.field(default_factory=dict)

    def __contains__(self, item: int | Currency) -> bool:
        if type(item) is Currency:
            return item.id in self.currencies
        elif type(item) is int:
            return item in self.currencies
        else:
            raise KeyError(f"Cannot look up Currency with id of type {type(item)}! Expected id of type: int.")

    def __getitem__(self, item: int | Currency) -> Currency:
        if type(item) is Currency:
            return self.currencies[item.id]
        elif type(item) is int:
            return self.currencies[item]
        else:
            raise KeyError(f"Cannot look up Currency with id of type {type(item)}! Expected id of type: int.")

    def __iter__(self) -> Iterator:
        """
        Cache an iterator for self.currencies and then return the cached copy
        """
        self._iterator = self.currencies.__iter__()
        return self._iterator

    def __next__(self) -> int:
        """
        Pass the call to the cached iterator
        """
        return self._iterator.__next__()

    def __post_init__(self):
        # Initialize the currencies map.
        for currency in currency_manager:
            self.currencies[currency.id] = currency_manager.to_currency(currency.id, 0)

    def balance(self, cur: Currency | int) -> int:
        """
        Retrieve the quantity of the currency passed in

        Args:
            cur: The ID of the currency to retrieve or an instance of the currency to retrieve

        Returns:
            The quantity of the currency requested
        """

        if cur not in self:
            raise KeyError(f"Unknown currency: {cur}")

        return self[cur].quantity

    def spend(self, cur: Currency | int, quantity: int | None = None) -> bool:
        """
        Attempt to spend currency.

        Args:
            cur: the currency to spend, or the id of the currency to spend
            quantity: The amount of the currency to spend

        Returns: True if the currency was successfully spent, False otherwise
        """

        if cur not in self:
            raise KeyError(f"Unknown currency: {cur}")

        if quantity is not None and type(quantity) is not int:
            raise TypeError(f"Cannot spend not-int values! Got type{type(quantity)}. Expected type: int")

        if type(cur) is int:
            if quantity < 1:
                raise ValueError(f"Cannot spend values less than 1! Got {quantity}.")

            if self[cur].quantity < quantity:
                return False

            self.adjust(cur, quantity * -1)
            return True

        if type(cur) is Currency:
            if cur.quantity <= self.balance(cur):
                self.currencies[cur.id].quantity -= cur.quantity
                return True

            return False

        return False

    def adjust(self, cur: int | Currency, quantity: int | float) -> None:
        """
        Adjusts a currency by a specified amount.

        Args:
            cur: The id of the currency to adjust or an instance of the currency to adjust
            quantity: The amount to adjust by. If this is an int, simply add. If it is a float, simply multiply.

        Returns: None
        """
        if cur not in self:
            raise KeyError(f"Unknown currency: {cur}")

        if type(quantity) is int:
            self[cur].quantity += quantity

        elif type(quantity) is float:
            self[cur].quantity = round(self[cur].quantity * quantity)

        else:
            raise TypeError(f"Unknown type: {type(quantity)}! Quantity must be of type int or float")

    def test_currency(self, cur: int | Currency, quantity: int) -> bool:
        """
        Test if there is enough of currency 'currency_id' such that
        currency.quantity >= quantity

        Args:
            cur: The ID of the currency to test or an instance of the currency to test
            quantity: The amount of currency that must be present to return True

        Returns: True if currency.quantity >= quantity, False otherwise
        """

        if cur not in self:
            raise KeyError(f"Unknown currency: {cur}")

        if quantity < 0:
            raise ValueError("Cannot test a negative value against a currency!")

        if quantity == 0:
            return True

        return self[cur].quantity >= quantity

    def test_all_purchase(self, item_id: int) -> list[int]:
        """
        Test if the item with item_id can be purchased using any currency and
        return a list of valid currency IDs

        Args:
            item_id: The ID of the item to test against

        Returns: A list of currency IDs that can be used to purchase the item
            with item IDs
        """
        from game.systems.item import item_manager

        costs: dict[int, int] = item_manager.get_currency_values(item_id)
        return [cur_id for cur_id, value in costs.items() if self.test_currency(cur_id, value)]

    def test_purchase(self, item_id: int, currency_id: int) -> bool:
        """
        Test if the item with id 'item_id' can be purchased using currency with
        id 'currency_id'.

        Args:
            item_id: The ID of the item to test the purchase
            currency_id: The ID of the currency to use to test

        Returns: True if the there is a sufficient quantity of currency with id
            'currency_id', False otherwise
        """

        item: Item = from_cache("managers.ItemManager").get_ref(item_id)

        return self.test_currency(currency_id, item.get_market_value(currency_id).quantity)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "CoinPurse", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "CoinPurse":
        """
        Instantiate an CoinPurse object from a JSON blob.

        Args:
            json: a dict-form representation of an CoinPurse object

        Returns: an CoinPurse instance with the properties defined in the JSON

        Required JSON fields:
        - currencies: [{id: int, quantity: int}]

        Optional JSON fields:
        - None
        """

        class_key = "CoinPurse"
        currencies_key = "currencies"

        # Type and field checking
        required_fields = [currencies_key]
        for field in required_fields:
            if field not in json:
                raise ValueError(f"Required field {field} not in JSON!")

        if json["class"] != class_key:
            raise ValueError(f"Cannot load JSON for object of class {json['class']}")

        if type(json[currencies_key]) is not list:
            raise TypeError(f"Cannot parse item manifest of type {type(json[currencies_key])}! Expect type list")

        cp = CoinPurse()

        for currency in json["currencies"]:
            cp.adjust(currency["id"], currency["quantity"])

        return cp
