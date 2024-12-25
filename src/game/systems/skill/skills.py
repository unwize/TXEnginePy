from __future__ import annotations

import copy
from abc import ABC

import game
from game.cache import cached
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.systems.event.events import Event


class SkillBase(ABC):
    def __init__(
        self,
        name: str,
        id: int,
        description: str,
        level: int = 1,
        xp: int = 0,
        initial_level_up_limit: int = 5,
        next_level_ratio: float = 1.3,
        level_up_events: dict[int, list[Event]] = None,
    ):
        self.name: str = name  # Skill name
        self.id: int = id  # Unique id associate with this skill
        self.description: str = description

        self.initial_level_up_limit: int = initial_level_up_limit  # How much XP is required to go from lvl 1 to lvl 2
        self.next_level_ratio: float = next_level_ratio  # Additional XP required to go from lvl 2 to lvl3, etc

        self.level: int = level  # Skill's current level
        self.xp: int = xp  # Skill's current xp quantity
        self.level_up_limit: int = self._xp_ceiling(self.level)  # Current limit to level up against

        self.level_up_events: dict[int, list[Event]] = (
            level_up_events or {}
        )  # events.Events that are triggered on level up

        # Detect invalid next_level_ratios
        if self.next_level_ratio < 1.0:
            raise ValueError(f"Invalid next_level_ratio for Skill {self.name}: {self.next_level_ratio}")

        # Detect xp-level mismatches
        if self.xp >= self.level_up_limit:
            raise ValueError(
                f"Skill {self.name}'s XP level does not match it's level! {self.xp} >= {self.level_up_limit}"
            )

    def _xp_ceiling(self, level: int) -> int:
        """
        Calculate the level_up value for a given level
        """
        _sum = self.initial_level_up_limit
        for i in range(level - 1):
            _sum = round(_sum * self.next_level_ratio)

        return _sum

    def _trigger_level_up_events(self, level: int) -> None:
        """
        For a given level, add all level-up-events to the device stack
        """

        if type(level) is not int:
            raise TypeError("Level must be an int!")

        if level in self.level_up_events:
            for event in self.level_up_events[level]:
                game.add_state_device(copy.deepcopy(event))

        from game.systems.event.events import TextEvent

        # Add user prompt for level-up LAST so that it is executed before all
        # the level-up events
        game.add_state_device(
            TextEvent(
                [
                    "Congratulations! ",
                    StringContent(value=self.name, formatting="skill_name"),
                    f" reached level {level}!",
                ]
            )
        )

    def force_level_up(self) -> None:
        """
        Force a skill to level up regardless of state.

        This increments the level, increments the level_up_limit, and sets XP to 0.
        """
        self.level += 1
        self.xp = 0
        self.level_up_limit = self._xp_ceiling(self.level)
        self._trigger_level_up_events(self.level)

    def _check_level_up(self) -> None:
        """
        A helper function that detects if enough xp has been gained to level the
         skill up. If so, all appropriate events are scheduled and the level and
          level_up fields are updated. If there is enough remaining xp to level
          up again, return True
        """

        if self.xp >= self.level_up_limit:  # Check for a level-up
            # Calculate how much xp carries into the next level
            remaining_xp = self.xp - self.level_up_limit

            # Update level_up_limit
            self.level += 1
            self.level_up_limit = self._xp_ceiling(self.level)

            self.xp = remaining_xp  # Update xp value to carry-over value
            cur_level = self.level
            if self.xp >= self.level_up_limit:  # Detect a hanging level up
                # Recursive call. Lowest-level events resolve first.
                self._check_level_up()

            self._trigger_level_up_events(cur_level)

    def gain_xp(self, xp: int) -> None:
        """
        Add XP to the skill. This will automatically trigger a level-up event if
        necessary.
        """
        self.xp += xp
        self._check_level_up()

    @property
    def remaining_xp(self) -> int:
        return self.level_up_limit - self.xp


class Skill(LoadableMixin, SkillBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Skill", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate a Skill object from a JSON blob.

        Args:
            json: a dict-form representation of a json object

        Returns: a Skill instance with the properties defined in the JSON

        Required JSON fields:
        - name: str
        - id: int
        - level_up_events: {str(int), list[events.Event]}

        Optional JSON fields:
        - level: int
        - xp: int
        - initial_level_up_limit: int
        - next_level_ratio: float
        """

        # Validate required fields exist
        required_fields = [("name", str), ("id", int), ("description", str), ("level_up_events", dict)]

        LoadableFactory.validate_fields(required_fields, json)

        level_up_events: dict[int, list[Event]] = {}

        for str_level in json["level_up_events"]:
            try:
                true_level = int(str_level)
            except TypeError:
                raise TypeError(f"Cannot convert level {str_level} to int!")

            if true_level in level_up_events:
                raise ValueError(f"Duplicate entries for level {true_level}!")

            level_up_events[true_level] = []

            from game.systems.event.events import Event

            for raw_event in json["level_up_events"][str_level]:
                obj = LoadableFactory.get(raw_event)
                if not isinstance(obj, Event):
                    raise TypeError(f"Cannot add object of type {type(obj)} to " f"level_up_event list!")
                level_up_events[true_level].append(obj)

        # Verify that the optional fields are typed correctly if they're present
        optional_fields = [("level", int), ("xp", int), ("initial_level_up_limit", int), ("next_level_ratio", float)]
        LoadableFactory.validate_fields(optional_fields, json, required=False)
        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        return Skill(
            name=json["name"], id=json["id"], description=json["description"], level_up_events=level_up_events, **kwargs
        )
