from abc import ABC
from enum import Enum

from game.cache import from_cache, cached
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent


class TerminationHandler(LoadableMixin, ABC):
    """
    Termination handlers inspect a CombatEngine object and determine if combat should end and whether it ends in
    a win or a loss.
    """

    class TerminationMode(Enum):
        WIN = 0
        LOSS = 1

    def __init__(self, mode: TerminationMode, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner  # CombatEngine
        self.mode: TerminationHandler.TerminationMode = mode

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, combat_engine) -> None:
        from game.systems.combat.combat_engine.combat_engine import CombatEngine

        if not isinstance(combat_engine, CombatEngine):
            raise TypeError(
                f"Cannot assign owner! Expected owner of type CombatEngine, got {type(combat_engine)} instead."
            )

        self._owner = combat_engine

    @property
    def trigger_message(self) -> list[str | StringContent]:
        raise NotImplementedError()

    def is_conditions_met(self) -> bool:
        raise NotImplementedError()


class GroupResourceCondition(TerminationHandler, ABC):
    """
    A condition that triggers when all entities in the designated group reach a specified resource value threshold.
    """

    class Mode(Enum):
        """
        Operational mode for GroupResourceCondition.
        """

        EQUAL_TO = "equal_to"
        GREATER_THAN = "greater_than"
        LESS_THAN = "less_than"

    def __init__(
        self,
        resource_name: str,
        resource_value: int | float,
        termination_mode: TerminationHandler.TerminationMode,
        resource_mode: Mode,
        owner=None,
    ):
        super().__init__(owner)
        self.resource_name: str = resource_name
        self.resource_value: int | float = resource_value
        self.resource_mode: GroupResourceCondition.Mode = resource_mode
        self.termination_mode: TerminationHandler.TerminationMode = termination_mode

    @property
    def group_name(self) -> str:
        """Returns the name of the group of entities to test against.

        The returned string will be used to populate player-facing messages. As such, the group name should be in
        plural form.
        """
        raise NotImplementedError()

    @property
    def group(self) -> list:
        """
        Returns a list of entities to test the condition against
        """
        raise NotImplementedError()

    def is_conditions_met(self) -> bool:
        resources = [entity.resource_controller[self.resource_name] for entity in self.group]

        match self.resource_mode:
            case self.Mode.EQUAL_TO:
                if type(self.resource_value) is not int:
                    raise TypeError(f"Invalid resource_value type! Expected float, got {type(self.resource_value)}")
                return all([res.value == self.resource_value for res in resources])

            case self.Mode.LESS_THAN:
                if type(self.resource_value) is int:
                    return all([res.value < self.resource_value for res in resources])

                elif type(self.resource_value) is float:
                    return all([res.percent_remaining < self.resource_value for res in resources])
                else:
                    raise TypeError(
                        f"Invalid resource_value type! Expected int | float, got {type(self.resource_value)}"
                    )

            case self.Mode.GREATER_THAN:
                if type(self.resource_value) is int:
                    return all([res.value > self.resource_value for res in resources])

                elif type(self.resource_value) is float:
                    return all([res.percent_remaining > self.resource_value for res in resources])
                else:
                    raise TypeError(
                        f"Invalid resource_value type! Expected int | float, got {type(self.resource_value)}"
                    )

            case _:
                raise RuntimeError(f"Unknown operating mode: {self.mode}!")

    @property
    def trigger_message(self) -> list[str | StringContent]:
        if type(self.resource_value) is int:
            return [f"All {self.group_name} have reached {self.resource_value} {self.resource_name}"]
        else:
            return [f"All {self.group_name} have reached {self.resource_value * 100}% {self.resource_name}"]

    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate an GroupResourceCondition object from a JSON blob.

        Required JSON fields:
        - resource_name: str
        - resource_value: str
        - resource_mode: Mode
        - termination_mode: TerminationMode

        Optional JSON fields:
        - None
        """

        required_fields = [
            ("resource_name", str),
            ("resource_value", (int, float), ("termination_mode", str), ("resource_mode", str)),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        return GroupResourceCondition(
            json["resource_name"],
            json["resource_value"],
            GroupResourceCondition.TerminationMode(json["termination_mode"]),
            GroupResourceCondition.Mode(json["resource_mode"]),
        )


class AllyResourceCondition(GroupResourceCondition):
    """
    A TerminationHandler that triggers when all allies (including the player) reach the designated resource threshold.
    """

    @property
    def group_name(self) -> str:
        return "allies"

    @property
    def group(self) -> list:
        return from_cache("combat").allies

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "AllyResourceCondition", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate an AllyResourceCondition object from a JSON blob.

        Required JSON fields:
        - resource_name: str
        - resource_value: str
        - termination_mode: TerminationMode

        Optional JSON fields:
        - None
        """

        required_fields = [
            ("resource_name", str),
            ("resource_value", (int, float), ("termination_mode", str), ("resource_mode", str)),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        return AllyResourceCondition(
            json["resource_name"],
            json["resource_value"],
            AllyResourceCondition.TerminationMode(json["termination_mode"]),
            GroupResourceCondition.Mode(json["resource_mode"]),
        )


class EnemyResourceCondition(GroupResourceCondition):
    @property
    def group_name(self) -> str:
        return "enemies"

    @property
    def group(self) -> list:
        return from_cache("combat").enemies

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "EnemyResourceCondition", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate an EnemyResourceCondition object from a JSON blob.

        Required JSON fields:
        - resource_name: str
        - resource_value: str
        - termination_mode: TerminationMode

        Optional JSON fields:
        - None
        """

        required_fields = [
            ("resource_name", str),
            ("resource_value", (int, float), ("termination_mode", str), ("resource_mode", str)),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        return EnemyResourceCondition(
            json["resource_name"],
            json["resource_value"],
            GroupResourceCondition.TerminationMode(json["termination_mode"]),
            GroupResourceCondition.Mode(json["resource_mode"]),
        )


class PlayerResourceCondition(GroupResourceCondition):
    """
    The PlayerResourceCondition triggers when a specified resource meets a specified value.
    """

    @property
    def group_name(self) -> str:
        return "player"

    @property
    def group(self) -> list:
        return [from_cache("player")]  # GroupResourceCondition::is_conditions_met expects a list of entities

    @property
    def trigger_message(self) -> list[str | StringContent]:
        if type(self.resource_value) is int:
            return [f"You have reached {self.resource_value} {self.resource_name}"]
        else:
            return [f"You have reached {self.resource_value * 100}% {self.resource_name}"]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "PlayerResourceCondition"])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate a PlayerResourceCondition object from a JSON blob.

        Required JSON fields:
        - resource_name: str
        - resource_value: str
        - termination_mode: TerminationMode

        Optional JSON fields:
        - None
        """

        required_fields = [
            ("resource_name", str),
            ("resource_value", (int, float), ("termination_mode", str), ("resource_mode", str)),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        return PlayerResourceCondition(
            json["resource_name"],
            json["resource_value"],
            PlayerResourceCondition.TerminationMode(json["termination_mode"]),
            GroupResourceCondition.Mode(json["resource_mode"]),
        )
