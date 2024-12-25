from __future__ import annotations


class CurrencyMixin:
    """
    A mixin for Entity objects that provides CoinPurse functionality.
    """

    def __init__(self, coin_purse=None, **kwargs):
        super().__init__(**kwargs)
        from game.systems.currency.coin_purse import CoinPurse

        self.coin_purse = coin_purse or CoinPurse()
