from __future__ import annotations

from abc import ABC

from typing import TYPE_CHECKING

from game.cache import from_cache
from game.structures.messages import StringContent

if TYPE_CHECKING:
    from game.systems.currency import Currency


class TradeMixin(ABC):
    """
    A mixin that defines an interface for assigning currency value to an object.
    """

    def __init__(self, market_values: dict[int, int] = None, **kwargs):
        super().__init__(**kwargs)

        self._market_values: dict[int, int] = market_values or {}

    @property
    def market_values(self) -> list[Currency]:
        return [from_cache("managers.CurrencyManager").to_currency(k, v) for k, v in self._market_values.items()]

    def has_market_value(self, currency_id: int) -> bool:
        """
        Determine if the object can be sold in the given Currency

        Args:
            currency_id: The ID of the currency to check against

        Returns: True if the object has a value in that Currency, False
            otherwise.
        """

        return currency_id in self._market_values

    def get_market_value(self, currency_id: int) -> Currency:
        """
        Fetch a Currency object representing the value of the object in the
        given Currency.

        Args:
            currency_id: The ID of the currency to fetch

        Returns: A Currency object with the value of self in the given Currency
        """

        if not self.has_market_value(currency_id):
            raise RuntimeError(f"{self} has no value in Currency with ID {currency_id}")

        return from_cache("managers.CurrencyManager").to_currency(currency_id, self._market_values[currency_id])

    def get_market_values_as_options(self) -> list[list[str, StringContent]]:
        """
        Build a list of formatted strings representing this object's value
        in each available Currency.
        """

        res = []

        for cur_id, cur_value in self._market_values.items():
            cur: Currency = from_cache("managers.CurrencyManager").to_currency(cur_id, cur_value)
            res.append(
                [
                    StringContent(value=cur.name, formatting="currency_name"),
                    ": ",
                    StringContent(value=str(cur), formatting="currency_value"),
                ]
            )

        return res
