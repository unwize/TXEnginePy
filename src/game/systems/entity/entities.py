from __future__ import annotations
from typing import TYPE_CHECKING

from abc import ABC

from game.cache import cached
from game.structures.enums import CombatPhase
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.systems.combat.combat_engine.combat_agent import PlayerAgentMixin, CombatAgentMixin
import game.systems.entity.mixins as mixins
from game.systems.item.loot import LootableMixin, LootTable

if TYPE_CHECKING:
    from game.systems.combat.effect import CombatEffect


class EntityBase(ABC):
    def __init__(self, id: int, name: str):
        if not isinstance(id, int):
            raise TypeError(f"Expected id to be of type int, got {type(id)} instead.")

        if not isinstance(name, str):
            raise TypeError(f"Expected name to be of type str, got {type(name)} instead.")

        self.id: int = id
        self.name: str = name


class Entity(
    mixins.SkillMixin, mixins.CurrencyMixin, mixins.InventoryMixin, LoadableMixin, mixins.ResourceMixin, EntityBase
):
    """
    A basic object that stores an entity's instance attributes such as name,
    ID, inventory, currencies, etc
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Entity", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate an Entity object from a JSON blob.

        Args:
            json: a dict-form representation of a json object

        Returns: an Entity instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int

        Optional JSON fields:
        - inventory: InventoryController
        - coin_purse: CoinPurse
        - skills: dict
        """

        # Turn the attributes JSON fields into key-word arguments to be passed
        # to Entity's subclasses
        required_fields = [("name", str), ("id", int)]

        optional_fields = [("inventory", dict), ("coin_purse", dict), ("skills", dict)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)
        kw = LoadableFactory.collect_optional_fields(optional_fields, json)

        return Entity(name=json["name"], id=json["id"], **kw)


class CombatEntity(mixins.AbilityMixin, mixins.EquipmentMixin, CombatAgentMixin, LootableMixin, Entity):
    """
    A subclass of Entity that contains all the necessary components to
    participate in Combat.
    """

    def __init__(self, xp_yield: int = 1, turn_speed: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.xp_yield: int = xp_yield
        self.turn_speed = turn_speed
        self.active_effects: dict[CombatPhase, list[CombatEffect]] = {phase: [] for phase in CombatPhase}
        self.ability_controller.owner = self
        self.equipment_controller.owner = self

    def acquire_effect(self, effect: CombatEffect, phase: CombatPhase) -> None:
        """
        Ingest an effect and store it in a phase's list.
        """

        self.active_effects[phase].append(effect)

    def clear_effects(self) -> None:
        """
        Remove all Effects from the Entity.
        """
        for phase in self.active_effects:
            self.active_effects[phase] = []

    def _prune_effects(self) -> None:
        """
        Remove all dead Effects from the Entity.

        An Effect is considered dead when its duration has decremented to zero.
        """
        for phase in self.active_effects:
            for i in range(len(self.active_effects[phase])):
                if self.active_effects[phase][i].duration == 0:
                    del self.active_effects[phase][i]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "CombatEntity", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate a CombatEntity object from a JSON blob.

        Args:
            json: a dict-form representation of a json object

        Returns: a CombatEntity instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - xp_yield: int
        - turn_speed: int
        - abilities: list[str]
        - loot_table: int | LootTable

        Optional JSON fields:
        - combat_provider (str)
        - inventory_controller: InventoryController
        - resource_controller: ResourceController
        - equipment_controller: EquipmentController
        - coin_purse: CoinPurse
        - naive: bool

        """

        required_fields = [
            ("name", str),
            ("id", int),
            ("xp_yield", int),
            ("turn_speed", int),
            ("abilities", list),
            ("loot_table", object),
        ]

        optional_fields = [
            ("combat_provider", str),
            ("inventory_controller", dict),
            ("resource_controller", dict),
            ("equipment_controller", dict),
            ("coin_purse", dict),
            ("naive", bool),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)
        kw = LoadableFactory.collect_optional_fields(optional_fields, json)

        # Pre-process LootableMixin data. Determine if an ID or an instance is
        # passed.
        # If an ID is passed, simply pass it through. If a LootTable JSON blob
        # is passed,
        # transform it via LoadableFactory and pass it back to kw dict.
        if isinstance(json["loot_table"], int):
            kw["loot_table_id"] = json["loot_table"]
        elif isinstance(json["loot_table"], dict):
            res = LoadableFactory.get(json["loot_table"])
            if not isinstance(res, LootTable):
                raise TypeError("Expected entity['loot_table'] to be of class LootTable!")

            kw["loot_table_instance"] = res
        else:
            raise TypeError("Unexpected type for json['loot_table'] in CombatEntity JSON!")

        ce = CombatEntity(
            json["xp_yield"], json["turn_speed"], name=json["name"], id=json["id"], abilities=json["abilities"], **kw
        )

        # Post-init fixing
        # Note: since the equipment_controller only gets assigned an owner
        # assigned AFTER init, it cannot check equip
        #       requirements. Thus, when loading the player's
        #       equipment_controller, can allow equipment to be equipped
        #       that the player cannot normally equip.
        if "equipment_controller" in kw:
            ce.equipment_controller.owner = ce

        return ce


class Player(mixins.CraftingMixin, PlayerAgentMixin, CombatEntity):
    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Player", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        # TODO: Implement player persistence
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.equipment_controller.player_mode = True
