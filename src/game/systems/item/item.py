import copy
from abc import ABC

import game
import game.systems.requirement.requirements as req
from game.cache import cached, from_cache
from game.mixins import TagMixin
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.systems.combat.effect import CombatEffect
from game.systems.currency.trade_mixin import TradeMixin
from game.systems.entity.resource import ResourceModifierMixin
from game.systems.event.events import Event


class ItemBase(ABC):
    """
    Base class of Item object
    """

    def __init__(self, name: str, iid: int, description: str, max_quantity: int = 10):
        self.name: str = name  # Name of item
        self.id: int = iid  # Unique id of item
        self.description: str = description  # Description of the item
        self.max_quantity: int = max_quantity  # Max num items per inv stack


class Item(LoadableMixin, TradeMixin, ItemBase):
    """
    A basic item. Objects of this type are inert.

    Args:
        name: The name of the item
        id: The unique ID of the item
        description: The user-facing flavor description of the item
        max_quantity: The max quantity of the item allowed per inventory stack
        market_values: A map of Currency ID to Currency value
    """

    def __init__(self, name: str, iid: int, description: str, max_quantity: int = 10, **kwargs):
        super().__init__(name=name, iid=iid, description=description, max_quantity=max_quantity, **kwargs)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Item", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "Item":
        """
        Instantiate an Item object from a JSON blob.

        Args:
            json: a dict-form representation of a JSON object

        Returns: An Item instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - description: str

        Optional JSON fields:
        - max_quantity: int (default value 10)
        - market_values: dict[int, int]
        """

        required_fields = [("name", str), ("id", int), ("description", str)]

        optional_fields = [("max_quantity", int), ("market_values", dict)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)
        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        if "market_values" in kwargs:
            kwargs["market_values"] = {int(k): v for k, v in kwargs["market_values"].items()}

        return Item(name=json["name"], iid=json["id"], description=json["description"], **kwargs)


class Usable(req.RequirementsMixin, Item):
    """
    A consumable item. When consumed, this item's stack quantity decreases by 1 and the Events in 'use_events' are
    triggered in sequence.
    """

    def __init__(
        self,
        name: str,
        iid: int,
        description: str,
        functional_description: str,
        max_quantity: int = 10,
        on_use_events: list[Event] = None,
        consumable: bool = False,
        **kwargs,
    ):
        super().__init__(name=name, iid=iid, description=description, max_quantity=max_quantity, **kwargs)

        self.on_use_events: list[Event] = on_use_events or []  # List of Events that trigger when item is used
        self.consumable: bool = consumable  # Determines if the item should decrement quantity after each use.
        self.functional_description: str = functional_description

    def use(self, target) -> None:
        from game.systems.entity.entities import Entity

        if not isinstance(target, Entity):
            raise TypeError("Usable target must be an instance of Entity!")

        for e in self.on_use_events:
            if not isinstance(e, Event):
                raise TypeError(f"Invalid use_event object type! Got type {type(e)}. Expected type Event!")

            dce = copy.deepcopy(e)
            if hasattr(dce, "_target"):
                dce._target = target

            elif hasattr(dce, "target"):
                dce.target = target

            game.add_state_device(dce)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Usable", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "Usable":
        """
        Instantiate a Usable object from a JSON blob.

        Args:
            json: a dict-form representation of a JSON object

        Returns: A Usable instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - description: str
        - functional_description: str


        Optional JSON fields:
        - max_quantity: int (default value 10)
        - on_use_events: [Event]
        - consumable: bool
        - requirements: [Requirement]
        - market_values: dict[int, int]
        """

        required_fields = [
            ("name", str),
            ("id", int),
            ("description", str),
            ("functional_description", str),
        ]

        optional_fields = [
            ("max_quantity", int),
            ("on_use_events", list),
            ("consumable", bool),
            ("market_values", dict),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        if "market_values" in kwargs:
            kwargs["market_values"] = {int(k): v for k, v in kwargs["market_values"].items()}

        if "on_use_events" in kwargs:
            kwargs["on_use_events"] = [LoadableFactory.get(raw_effect) for raw_effect in kwargs["on_use_events"]]

        return Usable(json["name"], json["id"], json["description"], json["functional_description"], **kwargs)


class Equipment(req.RequirementsMixin, ResourceModifierMixin, TagMixin, Item):
    def __init__(
        self,
        name: str,
        iid: int,
        description: str,
        functional_description: str,
        equipment_slot: str,
        damage_buff: int,
        damage_resist: int,
        start_of_combat_effects: list[CombatEffect] = None,
        **kwargs,
    ):
        super().__init__(name=name, iid=iid, description=description, **kwargs)
        self.functional_description: str = functional_description
        self.slot: str = from_cache("managers.EquipmentManager").is_valid_slot(equipment_slot)
        self.start_of_combat_effects: list[CombatEffect] = start_of_combat_effects or []

        self.damage_buff: int = damage_buff
        self.damage_resist: int = damage_resist

    def get_stats(self) -> dict[str, str]:
        """
        Return all relevant 'stats' as a dict mapping their user-facing
        descriptions to their values in str-form
        """

        results = {}

        for key, value in self.resource_modifiers.items():
            if type(value) is int:
                if value >= 0:
                    results[key] = f"+{value}"
                else:
                    results[key] = f"-{value}"

            elif type(value) is float:
                if value >= 0:
                    results[key] = f"+{value * 100}%"
                else:
                    results[key] = f"-{value * 100}%"
            else:
                raise TypeError(
                    f"Unexpected type in resource_mods dict! Expected type int, float, got {type(value)} instead!"
                )

        # Insert secondary stats
        results["Damage"] = str(self.damage_buff)
        results["Resistance"] = str(self.damage_resist)

        return results

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Equipment", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "Equipment":
        """
        Instantiate an Equipment object from a JSON blob.

        Args:
            json: a dict-form representation of a JSON object

        Returns: An Equipment instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - description: str
        - functional_description: str
        - equipment_slot: str
        - damage_buff: int
        - damage_resist: int

        Optional JSON fields:
        - max_quantity: int (default value 10)
        - start_of_combat_effects: list[CombatEffect]
        - requirements: list[Requirement]
        - resource_modifiers: dict[str, int | float]
        - tags: dict
        - market_values: dict[int, int]
        """

        required_fields = [
            ("name", str),
            ("id", int),
            ("description", str),
            ("functional_description", str),
            ("equipment_slot", str),
            ("damage_buff", int),
            ("damage_resist", int),
        ]
        optional_fields = [
            ("max_quantity", int),
            ("start_of_combat_effects", list),
            ("requirements", list),
            ("resource_modifiers", dict),
            ("tags", dict),
            ("market_values", dict),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        # Implicitly collect requirements, resource_modifiers
        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        if "market_values" in kwargs:
            kwargs["market_values"] = {int(k): v for k, v in kwargs["market_values"].items()}

        # Overwrite SOCE since its contents must be cast to Python via LoadableFactory
        start_of_combat_effects = []
        if "start_of_combat_effects" in json:
            for effect_json in json["start_of_combat_effects"]:
                ef = LoadableFactory.get(effect_json)
                if not isinstance(ef, CombatEffect):
                    raise TypeError(f"Expected effect of type CombatEffect, got {type(ef)} instead!")

                start_of_combat_effects.append(ef)

        kwargs["start_of_combat_effects"] = start_of_combat_effects

        return Equipment(
            json["name"],
            json["id"],
            json["description"],
            json["functional_description"],
            json["equipment_slot"],
            json["damage_buff"],
            json["damage_resist"],
            **kwargs,
        )
