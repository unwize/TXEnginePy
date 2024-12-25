import copy

from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.systems.crafting.recipe import Recipe
from game.util.asset_utils import get_asset


class RecipeManager(Manager):
    RECIPE_ASSET_PATH = "recipes"

    def __init__(self):
        super().__init__()
        self._manifest: dict[int, Recipe] = {}

    def __contains__(self, item) -> bool:
        return self._manifest.__contains__(item)

    def __getitem__(self, item) -> Recipe:
        return self._manifest.__getitem__(item)

    def register_recipe(self, recipe: Recipe) -> None:
        """
        Register a Recipe object with the manager.
        """
        if type(recipe.id) is not int:
            raise TypeError(f"recipe_id must be an int! Got {type(recipe.id)} instead.")

        if type(recipe) is not Recipe:
            raise TypeError(f"recipe must be a Recipe! Got {type(recipe)} instead!")

        if recipe.id in self._manifest:
            raise ValueError(f"Recipe with id {recipe.id} already exists!")

        self._manifest[recipe.id] = recipe

    def get_recipe(self, recipe_id: int) -> Recipe:
        """
        Returns a deep-copy of the Recipe with the specified id.
        """
        return copy.deepcopy(self._manifest[recipe_id])

    def load(self) -> None:
        raw_asset: dict[str, any] = get_asset(self.RECIPE_ASSET_PATH)
        for raw_recipe in raw_asset["content"]:
            recipe = LoadableFactory.get(raw_recipe)

            if not isinstance(recipe, Recipe):
                raise TypeError(f"Expected object of type Recipe, got type {type(recipe)} instead!")

            self.register_recipe(recipe)

    def save(self) -> None:
        pass
