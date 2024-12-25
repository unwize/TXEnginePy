from __future__ import annotations

from enum import Enum

from game.cache import cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems.entity.mixins.skill_mixin import SkillMixin
from game.systems.event.events import Event


class ViewSkillsEvent(Event):
    class States(Enum):
        DEFAULT = 0
        VIEW_SKILLS = 1
        SKILL_SELECTED = 2
        TERMINATE = -1

    def __init__(self, target: SkillMixin = None):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self._selected_skill: int | None = None
        self._target: SkillMixin | None = target

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def logic(_: any) -> None:
            self._selected_skill = None
            self.set_state(self.States.VIEW_SKILLS)

        @FiniteStateDevice.state_logic(
            self,
            self.States.VIEW_SKILLS,
            InputType.INT,
            -1,
            lambda: len(self.target.skill_controller.skills.keys()) - 1,
        )
        def logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            self._selected_skill = list(self.target.skill_controller.skills.keys())[user_input]
            self.set_state(self.States.SKILL_SELECTED)

        @FiniteStateDevice.state_content(self, self.States.VIEW_SKILLS)
        def content() -> dict:
            return ComponentFactory.get(["Skills: "], self.target.skill_controller.get_skills_as_options())

        @FiniteStateDevice.state_logic(self, self.States.SKILL_SELECTED, InputType.ANY)
        def logic(_: any) -> None:
            self.set_state(self.States.VIEW_SKILLS)

        @FiniteStateDevice.state_content(self, self.States.SKILL_SELECTED)
        def content() -> dict:
            return ComponentFactory.get(
                [
                    StringContent(
                        value=self.target.skill_controller.skills[self._selected_skill].name, formatting="skill_name"
                    ),
                    self.target.skill_controller.get_skill_as_option(self._selected_skill),
                    "\n",
                    self.target.skill_controller.skills[self._selected_skill].description,
                ]
            )

    @property
    def target(self) -> SkillMixin:
        """
        Returns the event's target. If no target is specified, return a reference to the player.
        """
        return self._target or from_cache("player")

    @target.setter
    def target(self, entity: SkillMixin):
        """
        Set the target of the event to a combat entity
        """

        if not isinstance(entity, SkillMixin):
            raise TypeError(
                f"ViewSummaryEvent target must be an instance of class SkillMixin! Got {type(entity)} instead!"
            )

        self._target = entity

    def __copy__(self):
        return ViewSkillsEvent()

    def __deepcopy__(self, memodict={}):
        return ViewSkillsEvent()

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ViewSkillsEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        return NotImplemented("ViewSkillsEvent does not support JSON loading!")
