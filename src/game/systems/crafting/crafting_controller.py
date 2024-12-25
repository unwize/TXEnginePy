import game
from game.cache import from_cache
from game.structures.messages import StringContent
from game.systems.crafting import recipe_manager

from loguru import logger


class CraftingController:
    """
    Manages crafting, learning of recipes, and event dispatching for a given Entity.
    """

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, entity) -> None:
        from game.systems.entity.entities import Entity

        if entity is not None and not isinstance(entity, Entity):
            raise TypeError(f"Cannot assign object of type {type(entity)} as owner!")
        self._owner = entity

    def __init__(self, recipe_manifest: list[int] = None, owner=None):
        from game.systems.entity.entities import Entity

        # Detect any non-existent recipe ids in the manifest
        if recipe_manifest is not None:
            for recipe in recipe_manifest:
                if recipe not in recipe_manager:
                    raise ValueError(f"Unknown recipe id! {str(recipe)}")

        self.learned_recipes: list[int] = recipe_manifest if recipe_manifest is not None else []
        self._owner: Entity = None
        self.owner: Entity = owner

    def can_learn_recipe(self, recipe_id) -> bool:
        """
        Check if the owning Entity meets the requirements to learn the recipe
        """
        return recipe_manager[recipe_id].is_requirements_fulfilled(self.owner)

    def learn_recipe(self, recipe_id: int) -> None:
        """
        Adds a recipe ID to the learned recipes set.

        This method does not prevent and Entity from learning a Recipe even if it does not meet the requirements. To
        check requirements before learning, use a LearnRecipeEvent.
        """
        if recipe_id not in recipe_manager:
            raise ValueError(f"Unknown recipe with ID {recipe_id}")

        if recipe_id in self.learned_recipes:
            logger.warning(f"Recipe with ID {recipe_id} already learned by {self.owner.name}")

        if not self.can_learn_recipe(recipe_id):
            logger.warning(f"{self.owner.name} has learned recipe with ID {recipe_id} without meeting requirements!")

        if recipe_id not in self.learned_recipes:
            self.learned_recipes.append(recipe_id)

    def get_missing_ingredients(self, recipe_id: int) -> list[tuple[int, int]]:
        """
        Check if the owning Entity has sufficient ingredients to execute the recipe and return a list of missing items
        """
        missing_items = []
        for item_id, quantity in recipe_manager[recipe_id].items_in:
            in_inv = self.owner.inventory.total_quantity(item_id)
            if in_inv < quantity:
                missing_items.append((item_id, quantity - in_inv))

        return missing_items

    def has_sufficient_ingredients(self, recipe_id: int) -> bool:
        """
        Check if the owning Entity has sufficient quantity of ingredients to execute the recipe
        """
        return len(self.get_missing_ingredients(recipe_id)) < 1

    def get_max_crafts(self, recipe_id) -> int:
        """
        Get the maximum number of times that this recipe can be crafted.

        The maximum number of crafts is determined by the limiting ingredient, aka whichever ingredient of the recipe
        has the lowest quantity_in_inventory / quantity_demand_from_recipe.
        """

        min_crafts: int = 9999999
        for ingredient_id, ingredient_quantity in recipe_manager[recipe_id].items_in:  # For each ingredient bundle
            in_inv: int = self.owner.inventory.total_quantity(ingredient_id)  # Check amount the user has
            max_crafts: int = int(in_inv / ingredient_quantity)  # Calculate how many bundles are available from the inv
            min_crafts = max_crafts if max_crafts < min_crafts else min_crafts  # Update minimum bundle quantity

        # The maximum number of crafts for the recipe is determined by the ingredient with the lowest relative quantity
        return min_crafts

    def get_recipes_as_options(self) -> list[list[str | StringContent]]:
        """
        This function is primarily used to translate the Player's learned recipes into a list of options to embedded into
        a Frame via a StateDevice.

        Returns a formatted list of lists of strings/StringContents.
        """

        opts: list[list[str | StringContent]] = []

        for recipe in self.learned_recipes:
            if self.has_sufficient_ingredients(recipe):
                opts.append([StringContent(value=recipe_manager.get_recipe(recipe).name, formatting="valid_recipe")])
            else:
                opts.append([StringContent(value=recipe_manager.get_recipe(recipe).name, formatting="invalid_recipe")])

        return opts

    def get_missing_ingredients_as_options(self, recipe_id) -> list[list[str | StringContent]]:
        """
        Retrieve a list of missing ingredients for a given recipe and format them into a Frame-compatible,
        text-formatted list.
        """
        payload = []

        for ingredient_id, ingredient_quantity in self.get_missing_ingredients(recipe_id):
            opt = [
                StringContent(value=from_cache("managers.ItemManager").get_name(ingredient_id), fomatting="item_name"),
                f"\tx{ingredient_quantity}",
                f"\t({self.get_max_crafts(recipe_id)})",
            ]
            payload.append(opt)

        return payload

    def perform_recipe(self, recipe_id: int, num_crafts: int = 1) -> None:
        """
        Execute the specified recipe by consuming the required items and spawning AddItemEvents for the products.

        This method assumes that all ingredients are present and that all requirements are met. If either of those
        conditions are not met, an error will be raised.

        args:
            recipe_id: The id of the recipe to perform
            num_crafts: The number of times to perform the recipe
        """

        if num_crafts > self.get_max_crafts(recipe_id):
            raise ValueError(f"Cannot execute recipe:{recipe_id} {num_crafts} " f"times! Insufficient ingredients!")

        if not recipe_manager.get_recipe(recipe_id).is_requirements_fulfilled(self._owner):
            raise RuntimeError("Cannot perform recipe, requirements not met!")

        from game.systems.event.add_item_event import AddItemEvent

        # Consume each ingredient in recipe 'n' times, where 'n' is num_crafts
        for item_id, quantity in recipe_manager.get_recipe(recipe_id).items_in:
            self._owner.inventory.consume_item(item_id, quantity * num_crafts)

        # Insert each product of the recipe into the player's inventory 'n'
        # times, where 'n' is num_crafts
        for item_id, quantity in recipe_manager.get_recipe(recipe_id).items_out:
            game.add_state_device(AddItemEvent(item_id, quantity * num_crafts))

        from game.systems.event.events import SkillXPEvent

        # Give skill-xp as needed
        for skill_id, skill_xp in recipe_manager.get_recipe(recipe_id).xp_reward.items():
            game.add_state_device(SkillXPEvent(skill_id, skill_xp * num_crafts))
