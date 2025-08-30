from __future__ import annotations

from abc import ABC
from enum import Enum

from loguru import logger

from game.structures.loadable_factory import LoadableFactory
from game.cache import from_cache, cached
from game.structures.loadable import LoadableMixin
from game.structures.messages import StringContent


class Requirement(LoadableMixin, ABC):
    """
    An abstract object that defines broad logical parameters that must be met.
    Children of this class narrow that logic and allow other objects to compose
    them to enforce a wide variety of gameplay mechanics.
    """

    def fulfilled(self, entity) -> bool:
        """
        Computes whether the requirement is fulfilled by the owner
        Returns: True if the requirement is fulfilled, False otherwise

        """
        raise NotImplementedError()

    @property
    def description(self) -> list[str | StringContent]:
        """
        Args:
        Returns:
            A list of strings and StringContents that provides the reader with a
            textual representation of the conditions that are specified for this
            Requirement to be 'fulfilled' such that self. Fulfilled==True
        """
        raise NotImplementedError()

    def __str__(self):
        """
        Return a conjoined string that strings self. Description of styling data
        """
        return " ".join([str(e) for e in self.description])


class RequirementsMixin:
    """
    A mixin class that enables a child class to accept requirements.
    """

    def __init__(self, requirements: list[Requirement] = None, **kwargs):
        super().__init__(**kwargs)
        self.requirements: list[Requirement] = requirements or []

    def is_requirements_fulfilled(self, entity) -> bool:
        """
        Calculates if all the requirements are fulfilled
        Returns: True if all requirements are fulfilled, False otherwise

        """

        if self.requirements is None or self.requirements == []:
            return True

        return all([req.fulfilled(entity) for req in self.requirements])

    def get_requirements_as_str(self) -> list[str]:
        """Get a list of strings that represent the conditions for the requirements associated with this object"""
        return [str(r) for r in self.requirements]

    def get_requirements_as_options(self) -> list[list[str | StringContent]]:
        """Get a list of lists that contain styling data that can be used by Frame objects"""
        return [r.description for r in self.requirements]

    @classmethod
    def get_requirements_from_json(cls, json) -> list[Requirement]:
        requirements = []
        if "requirements" in json:
            if not isinstance(json["requirements"], list):
                raise TypeError("requirements field must be a list!")

            for raw_requirement in json["requirements"]:
                if "class" not in raw_requirement:
                    raise ValueError("Bad or missing class field!")

                r = LoadableFactory.get(raw_requirement)  # Instantiate the Requirement via factory
                if not isinstance(r, Requirement):  # Typecheck it
                    raise TypeError(f"Unsupported class {type(r)} found in requirements field!")

                requirements.append(r)

        return requirements


class SkillRequirement(Requirement):
    """
    Fulfilled when the target has a skill level >= the specified level.
    """

    def __init__(self, skill_id: int, level: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skill_id: int = skill_id
        self.level: int = level

        self._skill_name: str | None = None

    def fulfilled(self, entity) -> bool:
        from game.systems.entity.mixins.skill_mixin import SkillMixin

        if isinstance(entity, SkillMixin):
            if self.skill_id not in entity.skill_controller.skills:
                return False

            return entity.skill_controller.get_level(self.skill_id) >= self.level

        # If the target entity does not have support for skills
        # (IE, NPC CombatEntities) simply return True
        else:
            logger.warning(f"SkillRequirement defaulted to True for entity: {str(entity)}")
            return True

    @property
    def description(self) -> list[str | StringContent]:
        if self._skill_name is None:
            self._skill_name = from_cache("managers.SkillManager").get_skill(self.skill_id).name

        return ["Requires ", StringContent(value=self._skill_name), f" level {self.level}"]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "SkillRequirement", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a SkillRequirement object from a JSON blob.

        Required JSON fields:
        - skill_id (int)
        - level (int)
        """

        required_fields = [("skill_id", int), ("level", int)]

        LoadableFactory.validate_fields(required_fields, json)

        return SkillRequirement(json["skill_id"], json["level"])


class ResourceRequirement(Requirement):
    """
    A requirement that checks that an entity possesses sufficient Resource
    value.
    """

    def __init__(self, resource_name: str, adjust_quantity: int | float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource_name: str = resource_name
        self.adjust_quantity: int | float = adjust_quantity

    def fulfilled(self, entity) -> bool:
        # Resource must be gte adjustment quantity
        if isinstance(self.adjust_quantity, int):
            if entity.resource_controller[self.resource_name].value < self.adjust_quantity:
                return False

        # Resource % must be >= adjust_quantity
        elif isinstance(self.adjust_quantity, float):
            _resource = entity.resource_controller[self.resource_name]
            if _resource.percent_remaining < self.adjust_quantity:
                return False

        else:
            raise TypeError("Adjustment must be of type int or float!")

        return True

    @property
    def description(self) -> list[str | StringContent]:
        sss = f"{self.adjust_quantity}" if isinstance(self.adjust_quantity, int) else f"{self.adjust_quantity * 100}%"
        return [
            "Requires ",
            StringContent(value=sss, formatting="resource_value"),
            " of ",
            StringContent(value=self.resource_name, formatting="resource_name"),
        ]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ResourceRequirement", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a ResourceRequirement object from a JSON blob.

        Required JSON fields:
        - resource_name (str)
        - adjust_quantity (float | int)
        """

        required_fields = [("resource_name", str), ("adjust_quantity", (int, float))]
        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "ResourceRequirement":
            raise ValueError(
                f"Invalid class field for ResourceRequirement! Got {json['class']} instead of ResourceRequirement!"
            )

        return ResourceRequirement(json["resource_name"], json["adjust_quantity"])


class FlagRequirement(Requirement):
    """
    Fulfilled when the designated flag is set to some expected value.
    """

    def __init__(self, flag_name: str, description: str, flag_value: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(flag_name, str):
            raise TypeError()

        if not isinstance(description, str):
            raise TypeError()

        if not isinstance(flag_value, bool):
            raise TypeError()

        self.flag = flag_name
        self.flag_value = flag_value
        self._description = [description]

    def fulfilled(self, entity) -> bool:
        fm = from_cache("managers.FlagManager")
        return fm.get_flag(self.flag) == self.flag_value

    @property
    def description(self) -> list[str | StringContent]:
        return self._description

    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a FlagRequirement object from a JSON blob.

        Required JSON fields:
        - flag_name (str)
        - flag_value (bool)
        - description (str)
        """

        required_fields = [("flag_name", str), ("flag_value", bool), ("description", str)]

        LoadableFactory.validate_fields(required_fields, json)

        return FlagRequirement(json["flag_name"], json["flag_value"], json["description"])


class FactionRequirement(Requirement):
    """
    A requirement that checks that the player possesses sufficient reputation
    with a given Faction.
    """

    class Mode(Enum):
        GREATER_THAN_EQUAL_TO = "gte"
        LESS_THAN_EQUAL_TO = "lte"
        EQUAL_TO = "eq"

    def __init__(self, faction_id: int, required_affinity: int, mode: str = "gte", *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.faction_id: int = faction_id
        self.required_affinity: int = required_affinity
        self.mode: FactionRequirement.Mode = FactionRequirement.Mode(mode)

    def fulfilled(self, entity) -> bool:
        faction_manager = from_cache("managers.FactionManager")

        if self.mode == self.Mode.GREATER_THAN_EQUAL_TO:
            return faction_manager.get_affinity(self.faction_id) >= self.required_affinity

        elif self.mode == self.Mode.LESS_THAN_EQUAL_TO:
            return faction_manager.get_affinity(self.faction_id) >= self.required_affinity

        elif self.mode == self.Mode.EQUAL_TO:
            return faction_manager.get_affinity(self.faction_id) == self.required_affinity

        else:
            raise ValueError(f"Unknown mode {self.mode}")

    @property
    def description(self) -> list[str | StringContent]:
        faction_manager = from_cache("managers.FactionManager")

        return [
            f"Must have an affinity of at least {self.required_affinity} with ",
            StringContent(value=faction_manager[self.faction_id].name, formatting="faction_name"),
            ".",
        ]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "FactionRequirement", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a FactionRequirement from a JSON blob.

        Required JSON fields:
        faction_id: (int)
        required_affinity: (int)

        Optional JSON fields:
        mode: (str)
        """

        required_fields = [("faction_id", int), ("required_affinity", int)]

        optional_fields = [("mode", str)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json)
        if json["class"] != "FactionRequirement":
            raise ValueError()

        kwargs = {}
        if "mode" in json:
            kwargs["mode"] = json["mode"]

        return FactionRequirement(json["faction_id"], json["required_affinity"], **kwargs)


class CurrencyRequirement(Requirement):
    """
    A requirement that verifies that an entity possesses at least 'n' of a
    given Currency.
    """

    def __init__(self, currency_id: int, currency_quantity: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._currency_id = currency_id
        self._currency_quantity = currency_quantity

    def fulfilled(self, entity) -> bool:
        if not hasattr(entity, "coin_purse"):
            return False

        return entity.coin_purse.balance(self._currency_id) >= self._currency_quantity

    @property
    def description(self) -> list[str | StringContent]:
        return [
            "Must have ",
            str(from_cache("Managers.CurrencyManager").to_currency(self._currency_id, self._currency_quantity)),
        ]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "CurrencyRequirement", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Load a CurrencyRequirement from a JSON blob.

        Required JSON fields:
        - currency_id: int
        - currency_quantity: int

        Optional JSON fields:
        - None
        """

        required_fields = [("currency_id", int), ("currency_quantity", int)]

        LoadableFactory.validate_fields(required_fields, json)
        return CurrencyRequirement(json["currency_id"], json["currency_quantity"])
