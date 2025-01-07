import weakref
from enum import Enum

from game.cache import from_cache, cached
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems.crafting import recipe_manager
from game.systems.entity import entities as entities
from game.systems.event.events import Event


class CraftingEvent(Event):
    """
    Provide a standardized flow for guiding the Player through the process of crafting items via Recipes.
    """

    class States(Enum):
        DEFAULT = 0  # Pre-logic
        DISPLAY_RECIPES = 2  # Choose a recipe
        NUM_CRAFTS = 3  # How many times to execute recipe
        CONFIRM_RECIPE = 4  # Confirm usage
        INSUFFICIENT_INGREDIENTS = 5  # Missing items
        REQUIREMENTS_NOT_MET = 6
        EXECUTE_RECIPE = 7
        TERMINATE = -1

    def __init__(self):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)

        self._player_ref: entities.Player | None = None
        self._chosen_recipe: int | None = None
        self._chosen_num_crafts: int | None = None

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any):
            """
            Set up the event. Grab a reference to the player and clear any stateful variables.
            """

            # Fetch ref it hasn't already been fetched.
            if self._player_ref is None:
                self._player_ref = weakref.proxy(from_cache("player"))

            # Reset in case the event is visited more than once
            self._chosen_recipe = self._chosen_num_crafts = None
            self.set_state(self.States.DISPLAY_RECIPES)

        @FiniteStateDevice.state_logic(
            self,
            self.States.DISPLAY_RECIPES,
            InputType.INT,
            -1,
            lambda: len(self._player_ref.crafting_controller.learned_recipes) - 1,
        )
        def _logic(user_input: int):
            # Go back to start
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
                return

            self._chosen_recipe = self._player_ref.crafting_controller.learned_recipes[user_input]

            # Ask number of times to execute recipe
            if self._player_ref.crafting_controller.has_sufficient_ingredients(
                self._chosen_recipe
            ) and recipe_manager.get_recipe(self._chosen_recipe).is_requirements_fulfilled(self._player_ref):
                self.set_state(self.States.NUM_CRAFTS)

            elif not self._player_ref.crafting_controller.has_sufficient_ingredients(self._chosen_recipe):
                self.set_state(self.States.INSUFFICIENT_INGREDIENTS)

            # Can't execute the recipe
            elif not recipe_manager.get_recipe(self._chosen_recipe).is_requirements_fulfilled(self._player_ref):
                self.set_state(self.States.REQUIREMENTS_NOT_MET)

            else:
                raise RuntimeError("Invalid state transition!")

        @FiniteStateDevice.state_content(self, self.States.DISPLAY_RECIPES)
        def _content():
            return ComponentFactory.get(
                ["Choose a recipe:"], self._player_ref.crafting_controller.get_recipes_as_options()
            )

        @FiniteStateDevice.state_logic(
            self,
            self.States.NUM_CRAFTS,
            InputType.INT,
            -1,
            lambda: self._player_ref.crafting_controller.get_max_crafts(self._chosen_recipe),
        )
        def _logic(user_input: int) -> None:
            if user_input < 1:
                self.set_state(self.States.DEFAULT)
                return

            # Store user's choice then transition to the confirmation prompt
            self._chosen_num_crafts = user_input
            self.set_state(self.States.CONFIRM_RECIPE)

        @FiniteStateDevice.state_content(self, self.States.NUM_CRAFTS)
        def _content() -> dict:
            return ComponentFactory.get(
                [
                    "How many times would you like to craft ",
                    StringContent(value=recipe_manager.get_recipe(self._chosen_recipe).name, formatting="recipe_name"),
                    f"? (Max: {self._player_ref.crafting_controller.get_max_crafts(self._chosen_recipe)})",
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.CONFIRM_RECIPE, InputType.AFFIRMATIVE)
        def _logic(user_input: bool):
            self.set_state(self.States.EXECUTE_RECIPE if user_input else self.States.DEFAULT)

        @FiniteStateDevice.state_content(self, self.States.CONFIRM_RECIPE)
        def _content():
            return ComponentFactory.get(
                [
                    f"Are you sure you want to craft {recipe_manager.get_recipe(self._chosen_recipe).name} ",
                    f"x{self._chosen_num_crafts}?\nYou will consume: ",
                ],
                recipe_manager.get_recipe(self._chosen_recipe).get_ingredients_as_options(self._chosen_num_crafts),
            )

        @FiniteStateDevice.state_logic(self, self.States.INSUFFICIENT_INGREDIENTS, InputType.ANY)
        def _logic(_: any):
            if not recipe_manager.get_recipe(self._chosen_recipe).is_requirements_fulfilled(self._player_ref):
                self.set_state(self.States.REQUIREMENTS_NOT_MET)

            else:
                self.set_state(self.States.DEFAULT)

        @FiniteStateDevice.state_content(self, self.States.INSUFFICIENT_INGREDIENTS)
        def _content():
            return ComponentFactory.get(
                ["You are missing key ingredients for this recipe:"],
                self._player_ref.crafting_controller.get_missing_ingredients_as_options(self._chosen_recipe),
            )

        @FiniteStateDevice.state_logic(self, self.States.REQUIREMENTS_NOT_MET, InputType.ANY)
        def _logic(_: any):
            self.set_state(self.States.DEFAULT)

        @FiniteStateDevice.state_content(self, self.States.REQUIREMENTS_NOT_MET)
        def _content():
            return ComponentFactory.get(
                ["You do not meet the requirements for this recipe!"],
                recipe_manager.get_recipe().get_requirements_as_options(),
            )

        @FiniteStateDevice.state_logic(self, self.States.EXECUTE_RECIPE, InputType.ANY)
        def _logic(_: any) -> None:
            self._player_ref.crafting_controller.perform_recipe(self._chosen_recipe, self._chosen_num_crafts)
            self.set_state(self.States.DEFAULT)

        @FiniteStateDevice.state_content(self, self.States.EXECUTE_RECIPE)
        def _content() -> dict:
            return ComponentFactory.get(
                [
                    "You crafted ",
                    StringContent(value=recipe_manager.get_recipe(self._chosen_recipe).name, formatting="recipe_name"),
                    f" {self._chosen_num_crafts} times.",
                ]
            )

    def __copy__(self):
        return CraftingEvent()

    def __deepcopy__(self, memodict={}):
        return CraftingEvent()

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "CraftingEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        LoadableFactory.validate_fields([], json)

        if json["class"] != "CraftingEvent":
            raise ValueError("Invalid 'class' field!")

        return CraftingEvent()
