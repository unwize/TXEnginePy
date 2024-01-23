from __future__ import annotations

import random

from loguru import logger

import game
from game.cache import from_cache
from game.structures.enums import TargetMode
from game.structures.errors import CombatError
from game.systems.combat.combat_engine.choice_data import ChoiceData
from game.systems.event import ResourceEvent
from game.systems.requirement.requirements import ResourceRequirement, ConsumeResourceRequirement


class CombatAgentMixin:
    """
    A mixin that allows for CombatEngine integration. Mixin MUST be applied to a CombatEntity instance.
    """
    PRIMARY_RESOURCE_DANGER_THRESHOLD: float = 0.33

    def __init__(self, naive: bool = True, **kwargs):
        super().__init__(**kwargs)

        self.naive = naive

        from game.systems.entity.entities import CombatEntity
        if not isinstance(self, CombatEntity):
            raise TypeError("CombatAgentMixin must mixed with a CombatEntity instance!")

    @property
    def usable_abilities(self) -> list[str]:
        """
        Returns a list of Abilities with fulfilled Requirements
        """

        return [
            ab for ab in self.ability_controller.abilities if from_cache(
                "managers.AbilityManager"
            ).get_instance(ab).is_requirements_fulfilled(self)
        ]

    @property
    def usable_items(self) -> list["Usable"]:
        """
        Returns a list of Usable Items with fulfilled Requirements
        """
        from game.systems.item.item import Usable

        stacks = self.inventory.filter_stacks(
            lambda stack: isinstance(stack, Usable) and stack.is_requirements_fulfilled(self)
        )

        return [s.ref for s in stacks]

    @classmethod
    def _is_restorative_item(cls, usable: "Usable", resource_name: str) -> bool:
        """Attempt to classify a Usable as 'restorative'. If the Usable adds value to primary_resource, then it is
        counted as restorative."""
        for e in usable.on_use_events:
            if isinstance(e, ResourceEvent):
                if e.stat_name == resource_name and not e.harmful:
                    return True

        return False

    @property
    def in_danger(self) -> bool:
        """A bool that represents if the entity is in danger and needs to restore primary_resource"""

        return self.resource_controller.primary_resource.percent_remaining < self.PRIMARY_RESOURCE_DANGER_THRESHOLD

    @property
    def restorative_items(self) -> list["Usable"]:
        """A list of Usables that restore primary_resource"""

        return [
            u for u in self.usable_items if self._is_restorative_item(u, self.resource_controller.primary_resource.name)
        ]

    def get_resource_fix_items(self, ability: str) -> list["Usable"]:
        """
        For a given ability, if it can't be used due to resource depletion, return a list of Usables that restore
        the missing resource
        """
        instance: "Ability" = from_cache("managers.AbilityManager").get_instance(ability)
        depleted_resources = set()
        for requirement in instance.requirements:
            if isinstance(requirement, ResourceRequirement) or isinstance(requirement, ConsumeResourceRequirement):
                depleted_resources.add(requirement.resource_name)

        results = set()
        for u in self.usable_items:
            for resource in depleted_resources:
                if self._is_restorative_item(u, resource):
                    results.add(u)

        return list(results)

    @property
    def offensive_abilities(self) -> list["Ability"]:
        """Returns a list of abilities that can be used to deal damage to enemies"""
        res = []

        for ability_name in self.ability_controller.abilities:
            instance: "Ability" = from_cache("managers.AbilityManager").get_instance(ability_name)

            # Check if the ability deals damage and can be used to target enemies
            if instance.damage > 0 and instance.target_mode not in [
                TargetMode.ALL_ALLY, TargetMode.SELF, TargetMode.SINGLE_ALLY
            ]:
                res.append(instance)

        return res

    def naive_choice_logic(self) -> ChoiceData:

        # If the entity doesn't know any abilities, just pass
        if len(self.ability_controller.abilities) < 1:
            return ChoiceData(ChoiceData.ChoiceType.PASS)

        r = random.Random()
        ab: str = r.choice(self.ability_controller.abilities)
        targets = from_cache("combat").get_ability_targets(self, ab)

        target = r.choice(targets)

        return ChoiceData(ChoiceData.ChoiceType.ABILITY, ability_name=ab, ability_target=target)

    def intelligent_choice_logic(self) -> ChoiceData:

        # If the entity is in danger, use an item to restore primary_resource
        if self.in_danger:
            logger.debug(f"{self.name}: In danger! ({self.resource_controller.primary_resource.percent_remaining})")
            restoratives = self.restorative_items
            if len(restoratives) > 0:
                logger.debug("Found restorative items!")
                # TODO: Improve item selection logic
                return ChoiceData(ChoiceData.ChoiceType.ITEM, item_id=random.Random().choice(restoratives).id)

        offensive_abilities = self.offensive_abilities
        if len(offensive_abilities) > 0:
            logger.debug("Found offensive abilities!")
            # sort by damage in desc order
            offensive_abilities = sorted(
                offensive_abilities,
                key=lambda x: x.damage,
                reverse=True)

            # Attempt to figure out which offensive abilities are usable
            for ab in offensive_abilities:  # Starting with ability that does the most damage
                logger.debug(f"Evaluating ability: {ab.name}")

                # If the ability cannot be used for some reason
                if not ab.is_requirements_fulfilled(self):
                    logger.debug(f"Requirements not met for {ab.name}")

                    # See if there are any items that can fix the situation
                    resource_fixers = self.get_resource_fix_items(ab.name)
                    if len(resource_fixers) < 1:
                        logger.debug("No fixer items located. Skipping.")
                        # There are no items that can help, so skip this ability
                        continue

                    # There is an item that can help, so just use the first one available
                    logger.debug(f"Fixer item found: {resource_fixers[0].name} (id: {resource_fixers[0].id})")
                    return ChoiceData(ChoiceData.ChoiceType.ITEM, item_id=resource_fixers[0].id)

                else:

                    # Check if it is a single-target ability
                    if ab.target_mode in [TargetMode.SINGLE, TargetMode.SINGLE_ENEMY, TargetMode.NOT_SELF]:
                        logger.debug(
                            f"Selecting single target for ability: {ab.target_mode} via mode {ab.target_mode}")
                        targets = from_cache("combat").get_ability_targets(self, ab.name)
                        t = \
                        sorted(targets, key=lambda x: x.resource_controller.primary_resource.value, reverse=True)[0]

                        logger.debug(f"Selected {t.name}!")
                        return ChoiceData(ChoiceData.ChoiceType.ABILITY, ability_name=ab.name, ability_target=t)

                    # If ability is group-target, just choose it
                    else:
                        logger.debug(f"Group selected for ability: {ab.name}")
                        return ChoiceData(
                            ChoiceData.ChoiceType.ABILITY,
                            ability_name=ab.name,
                            ability_target=from_cache("combat").get_ability_targets(self, ab.name)
                        )

        return ChoiceData(ChoiceData.ChoiceType.PASS)

    def _choice_logic(self) -> ChoiceData:
        """
        Get an Entity's choice for its turn during Combat.

        An entity may do one of three things:
        - Pass
        - Use an Item
        - Use an Ability

        To collect information about the combat's context, retrieve it via  from_cache("combat")
        """
        if self.naive:
            return self.naive_choice_logic()

        return self.intelligent_choice_logic()

    def make_choice(self) -> None:
        """
        A wrapper for _choice_logic that performs instance checking and validation before submitting the entity choice
        to the combat engine.
        """

        from_cache("combat").submit_entity_choice(self, self._choice_logic())


class PlayerAgentMixin(CombatAgentMixin):
    """
    A CombatAgentMixin that makes the player choose what to do.
    """

    def _choice_logic(self) -> ChoiceData:
        """
        Dead method. Ignore.
        """
        pass

    def make_choice(self) -> None:
        """
        Spawn a 'PlayerCombatChoiceEvent' and let it handle submitting combat choices to the global combat instance.
        """
        if not from_cache("combat"):
            raise CombatError("Unable to retrieve valid combat instance!")

        # Spawn an event to handle player choice flow.
        # Note that this method does not submit anything to the combat engine directly, all of that is handled within
        # the PlayerCombatChoiceEvent's logic.
        from game.systems.combat.combat_engine.player_combat_choice_event import PlayerCombatChoiceEvent
        game.state_device_controller.add_state_device(PlayerCombatChoiceEvent(self))
