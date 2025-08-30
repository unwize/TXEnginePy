from __future__ import annotations
from typing import TYPE_CHECKING
from abc import ABC

from loguru import logger

from game.cache import cached
from game.mixins import TagMixin
from game.structures.enums import CombatPhase, TargetMode
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.systems.requirement.requirements import RequirementsMixin, ResourceRequirement

if TYPE_CHECKING:
    from game.systems.combat.effect import CombatEffect


class AbilityBase(ABC):
    """
    The functional base class of Ability.

    This class is required in order to make proper use of the cooperative
    inheritance constructors specified in LoadableMixin and RequirementsMixin.
    """

    def __init__(
        self,
        name: str,
        description: str,
        on_use: str,
        target_mode: TargetMode,
        effects: dict[CombatPhase, list[CombatEffect]] = None,
        damage: int = 1,
        costs: dict[str, int | float] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.name: str = name
        self.description: str = description
        self.on_use: str = on_use
        self.effects: dict[CombatPhase, list[CombatEffect]] = effects or {ev: [] for ev in CombatPhase}
        self.target_mode = target_mode
        self.damage: int = damage
        self.costs = costs or {}


class Ability(LoadableMixin, RequirementsMixin, TagMixin, AbilityBase):
    """
    Ability objects represent 'moves' that can be used by CombatEntity's during
    Combat.

    Abilities are one of the two ways that a CombatEntity may be assigned a
    CombatEffect.
    """

    def __init__(self, *args, **kwargs):
        """
        kwargs:
            name: Name of the Ability. Also functions as a global ID
            description: User-facing description of ability.
            on_use: A string printed to user when
            effects: A map of CombatEffects to their respective trigger phases
            target_mode: Which target mode the Ability should use
            damage: Flat value for how much raw damage the Ability should deal
            costs: Any resource costs associated with using the Ability
            requirements: A list of Requirement objects that restrict conditions
                for using the Ability
            tags: A dict of tags associated with the Ability. The keys are the
                tag names and the values are always None.
        """
        super().__init__(*args, **kwargs)

        # For each cost, insert a ResourceRequirement that matches the cost to
        # enforce resource-minimums without extra logic.
        for resource_name, cost_quantity in self.costs.items():
            logger.debug(f"Adding ResourceRequirement to {self.name}: {resource_name} : {cost_quantity}")
            self.requirements.append(ResourceRequirement(resource_name, cost_quantity))

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Ability", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads an Ability object from a JSON blob.

        Required JSON fields:
        - name: str
        - description: str
        - on_use: str
        - target_mode: str
        - damage: int

        Optional JSON fields:
        - effects: dict[CombatPhase:[CombatEffect]]
        - costs: dict[str: int | float]
        - requirements: list[Requirement]
        """

        required_fields: list[tuple[str, type]] = [
            ("name", str),
            ("description", str),
            ("on_use", str),
            ("target_mode", str),
            ("damage", int),
        ]

        optional_fields = [("effects", dict), ("requirements", list), ("costs", dict), ("tags", list)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "Ability":
            raise ValueError("Incorrect class designation!")

        # Build complex optional field collections
        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json, False)

        # Build, verify and store effects
        if "effects" in json:
            effects = {}  # Pass to kwargs once filled

            # Sort Effects into lists by phase; iterate through phase
            for phase in json["effects"]:
                if phase not in CombatPhase.list():  # Catch bad phase
                    raise ValueError(f"Unknown combat phase: {phase}")

                # Catch broken formatting
                if type(json["effects"][phase]) is not list:
                    raise TypeError(
                        f"Expected phase {phase} to map to a list, got {type(json['effects'][phase])} instead!"
                    )

                # If the phase hasn't been observed yet, make a list for it
                if CombatPhase(phase) not in effects:
                    effects[CombatPhase(phase)] = []

                # Load the effect via class-field (raw_effect['class'])
                for raw_effect in json["effects"][phase]:
                    effects[CombatPhase(phase)].append(LoadableFactory.get(raw_effect))

            kwargs["effects"] = effects

        return Ability(
            name=json["name"],
            description=json["description"],
            on_use=json["on_use"],
            damage=json["damage"],
            target_mode=TargetMode(json["target_mode"]),
            **kwargs,  # Optional fields might not be present, so store and split via dict unpacking
        )
