from enum import Enum

import game
from game.cache import from_cache, cached
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.entity import Entity
from game.systems.entity.mixins.resource_mixin import ResourceMixin
from game.systems.entity.mixins.skill_mixin import SkillMixin
from game.systems.entity.mixins.equipment_mixin import EquipmentMixin
from game.systems.entity.mixins.ability_mixin import AbilityMixin
from game.systems.event import Event
from game.systems.event.events import ViewResourcesEvent
from game.systems.event.view_abilities_event import ViewAbilitiesEvent
from game.systems.event.view_equipment_event import ViewEquipmentEvent
from game.systems.event.view_skills_event import ViewSkillsEvent


class ViewSummaryEvent(Event):
    class States(Enum):
        DEFAULT = 0
        EXECUTE_OPTION = 1
        TERMINATE = -1

    def __init__(self, target=None):
        super().__init__(InputType.INT, self.States, self.States.DEFAULT)

        self._target: Entity = target

        # Map user-selectable option text to a spawnable Event and the classes required
        self._options: dict[str, dict[str, any]] = {
            "View Resources": {  # Text shown to user
                "class": ViewResourcesEvent,  # What event to spawn if options is selected
                "required_classes": [ResourceMixin],  # Target must be an instance of these classes for option to show
            },
            "View Abilities": {"class": ViewAbilitiesEvent, "required_classes": [AbilityMixin]},
            "View Skills": {"class": ViewSkillsEvent, "required_classes": [SkillMixin]},
            "View Equipment": {"class": ViewEquipmentEvent, "required_classes": [EquipmentMixin]},
        }

        self.setup_states()

    @property
    def options(self) -> list[list[str]]:
        """
        Compute available options based on the classes inherited by the Event's target
        """
        available_options = []
        for option in self._options:  # For all potential options
            if isinstance(self.target, tuple(self._options[option]["required_classes"])):  # Filter by inheritance
                available_options.append([option])  # Append option

        return available_options

    @property
    def target(self) -> Entity:
        """
        Returns the event's target. If no target is specified, return a reference to the player.
        """
        return self._target or from_cache("player")

    @target.setter
    def target(self, entity):
        """
        Set the target of the event to a combat entity
        """
        from game.systems.entity.entities import Entity

        if not isinstance(entity, Entity):
            raise TypeError(
                f"ViewSummaryEvent target must be an instance of class CombatEntity! Got {type(entity)} instead!"
            )

        self._target = entity

    def setup_states(self):
        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.INT, -1, lambda: len(self.options))
        def logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            selected_option = self.options[user_input][0]
            game.add_state_device(self._options[selected_option]["class"](self.target))

        @FiniteStateDevice.state_content(self, self.States.DEFAULT)
        def content() -> dict:
            return ComponentFactory.get(["What would you like to do?"], self.options)

    def __copy__(self):
        return ViewSummaryEvent(self.target)

    def __deepcopy__(self, memodict={}):
        return ViewSummaryEvent(self.target)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ViewSummaryEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        return ViewSummaryEvent()
