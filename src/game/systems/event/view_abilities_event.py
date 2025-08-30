from enum import Enum

from game.cache import cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory
from game.systems.event import Event


class ViewAbilitiesEvent(Event):
    class States(Enum):
        DEFAULT = 0
        VIEW_ABILITIES = 1
        INSPECT_ABILITY = 2
        EMPTY = 3
        TERMINATE = -1

    @property
    def selected_ability_instance(self):
        """
        Fetch an instance of the Ability that the user selected
        Returns: An Ability object selected by the user
        """

        # Check if an instance was cached
        if self._selected_instance:
            return self._selected_instance

        inst = from_cache("managers.AbilityManager").get_instance(self.selected_ability)
        self._selected_instance = inst  # Cache instance in attr

        return inst

    def __init__(self, target=None):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self.target = target  # Defaults to the player at runtime
        self.selected_ability: str | None = None
        self._selected_instance = None

        @self.state_logic(self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self._selected_instance = None
            self.selected_ability = None

            if self.target is None:
                self.target = from_cache("player")

            from game.systems.entity.mixins.ability_mixin import AbilityMixin

            if not isinstance(self.target, AbilityMixin):
                raise TypeError(f"Cannot view Abilities for non-AbilityMixin entity! ({self.target})")

            if len(self.target.ability_controller.abilities) < 1:
                self.set_state(self.States.EMPTY)
                return

            self.set_state(self.States.VIEW_ABILITIES)

        # This state is highly inefficient. TODO: Improve
        @self.state_logic(
            self.States.VIEW_ABILITIES,
            InputType.INT,
            -1,
            lambda: len(list(self.target.ability_controller.abilities)) - 1,
        )
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            self.selected_ability = list(self.target.ability_controller.abilities)[user_input]
            self.set_state(self.States.INSPECT_ABILITY)

        @self.state_content(self.States.VIEW_ABILITIES)
        def _content() -> dict:
            return ComponentFactory.get(
                [f"{self.target.name}'s abilities: "], self.target.ability_controller.get_abilities_as_options()
            )

        @self.state_logic(self.States.INSPECT_ABILITY, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.DEFAULT)

        # TODO: Improve state to account for zero tags
        @self.state_content(self.States.INSPECT_ABILITY)
        def _content() -> dict:
            return ComponentFactory.get(
                [
                    self.selected_ability + "\n",
                    self.selected_ability_instance.description + "\n\n",
                    "Types: \n",
                    "\n".join([f"- {t}" for t in self.selected_ability_instance.tags]),
                ],
                self.selected_ability_instance.get_requirements_as_options(),
            )

        @self.state_logic(self.States.EMPTY, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @self.state_content(self.States.EMPTY)
        def _content() -> dict:
            return ComponentFactory.get(["No learned abilities!"])

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ViewAbilitiesEvent", LoadableMixin.ATTR_KEY])
    def from_json(_) -> any:
        return ViewAbilitiesEvent()
