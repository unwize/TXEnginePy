import game.systems.combat.effect as effect
import game.systems.currency as currency
import game.systems.requirement.requirements as req
from game.cache import get_cache
from game.structures.loadable import LoadableMixin
from game.structures.loadable import cached


class Item(LoadableMixin):
    """
    A basic item. Objects of this type are inert.
    """

    def __init__(self, name: str, iid: int, value: dict[int, int], description: str, max_quantity: int = 10):
        super().__init__()
        self.name: str = name  # Name of item
        self.id: int = iid  # Unique id of item
        self.value: dict[int, int] = value  # Item's currency values. Key is Currency.id, value is Currency.quantity
        self.description: str = description  # The user-facing description of the item
        self.max_quantity: int = max_quantity  # The maximum number of items allowed in an inventory stack

    def get_currency_value(self, currency_id: int = None) -> currency.Currency:
        return currency.currency_manager.to_currency(currency_id,
                                                     self.value[currency_id]) if currency is not None else self.value

    @cached(LoadableMixin.LOADER_KEY, "Item")
    def from_json(self, json: dict[str, any]):
        """
        Instantiate an Item object from a JSON blob.

        Args:
            json: a dict-form representation of a JSON object

        Returns: An Item instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - value: {int, int}
        - description: str

        Optional JSON fields:
        - max_quantity: int (default value 10)
        """
        return Item(json['name'],
                    json['id'],
                    json['value'],
                    json['description'],
                    json['max_quantity'] if 'max_quantity' in json else 10
                    )


class Usable(Item, req.RequirementsMixin):
    """
    A consumable item. When consumed, this item's stack quantity decreases by 1 and the effects in 'effects' are
    triggered in sequence.
    """

    def __init__(self, name: str, iid: int, value: dict[int, int], description: str, max_quantity: int = 10,
                 effects: list[effect.Effect] = None, consumable: bool = False):
        super().__init__(name, iid, value, description, max_quantity)

        self.effects: list[effect.Effect] = effects or []  # List of effects that trigger when item is used
        self.consumable: bool = consumable  # Determines if the item should decrement quantity after each use.

    def use(self, target) -> None:

        from game.systems.entity.entities import Entity
        if not isinstance(target, Entity):
            raise TypeError("Usable target must be an instance of Entity!")

        for e in self.effects:
            e.perform(target)

    @cached(LoadableMixin.LOADER_KEY, "Usable")
    def from_json(self, json: dict[str, any]):
        """
        Instantiate an Item object from a JSON blob.

        Args:
            json: a dict-form representation of a JSON object

        Returns: An Item instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - value: {int, int}
        - description: str

        Optional JSON fields:
        - max_quantity: int (default value 10)
        - effects: [Effect]
        - consumable: bol
        """

        effects = [get_cache()['loader'][effect_json['class']](effect_json) for effect_json in
                   json['effects']] if 'effects' in json else []

        return Usable(json['name'],
                      json['id'],
                      json['value'],
                      json['description'],
                      json['max_quantity'] if 'max_quantity' in json else 10,
                      effects,
                      json['consumable']
                      )
