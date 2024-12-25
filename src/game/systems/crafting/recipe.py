from abc import ABC

from game.cache import cached, from_cache
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent
from game.systems.requirement.requirements import RequirementsMixin


class RecipeBase(ABC):
    """Base class for Recipe objects that defines class-specific properties"""

    def __init__(
        self,
        recipe_id: int,
        items_in: list[tuple[int, int]],
        items_out: list[tuple[int, int]],
        name: str = None,
        xp_reward: dict[int, int] = None,
    ):
        self.id: int = recipe_id  # Unique identifier for recipe
        self.items_in: tuple[tuple[int, int]] = tuple(items_in or [])  # Items that are consumed
        self.items_out: tuple[tuple[int, int]] = tuple(items_out or [])  # Items returned to the crafter
        self.name: str = name  # Name of the ingredient
        self.xp_reward = xp_reward or {}  # A map of skill-id-xp-quantity that is rewarded on completion of the recipe

        # If a name is not provided, supply a default name in the format of "ingredients -> products"
        if name is None:
            from game.systems.item import item_manager

            ingredients = [item_manager.get_name(id) for id, _ in self.items_in]
            products = [item_manager.get_name(id) for id, _ in self.items_out]

            self.name = ", ".join(ingredients) + " -> "[:-2] + ", ".join(products)[:-2]  # Skip trailing ', '

        # Detect and throw duplicate item ids in ingredients and products
        observed_item_ids = set()
        for item_id, _ in self.items_in:
            if item_id not in observed_item_ids:
                observed_item_ids.add(item_id)
            else:
                raise ValueError(f"Duplicate ingredient ID detected! {item_id}! All ingredient entries must be unique")

        observed_item_ids = set()
        for item_id, _ in self.items_out:
            if item_id not in observed_item_ids:
                observed_item_ids.add(item_id)
            else:
                raise ValueError(f"Duplicate product ID detected! {item_id}! All products entries must be unique")

    def get_ingredients_as_options(self, num_crafts: int = 1) -> list[list[str | StringContent]]:
        opts = []

        for item_id, required_quantity in self.items_in:
            opts.append(
                [
                    StringContent(value=from_cache("managers.ItemManager").get_name(item_id), formatting="item_name"),
                    "\t",
                    StringContent(value=f"x{required_quantity * num_crafts}"),
                ]
            )
            return opts


class Recipe(LoadableMixin, RequirementsMixin, RecipeBase):
    """Proper class for Recipe objects. Inherits from multiple mixins.

    A Recipe defines a required list of ingredients and a list of products. When successfully executed, a Recipe
    consumes the ingredients from the Entity's inventory and returns the products to the Entity's inventory.
    A recipe may only be learned by an Entity that meets all of its Requirements.
    """

    def __init__(self, id: int, items_in: list[tuple[int, int]], items_out: list[tuple[int, int]], **kwargs):
        super().__init__(recipe_id=id, items_in=items_in, items_out=items_out, **kwargs)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Recipe", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Instantiate a Recipe object from a JSON blob.

        Args:
            json: a dict-form representation of a json object

        Returns: a Recipe instance with the properties defined in the JSON

        Required JSON fields:
        - id (int)
        - items_in: [[int, int]]
        - items_out: [[int, int]]

        Optional JSON fields:
        - requirements: list[Requirements]
        - name: str
        - xp_reward: dict[int, int]
        """

        required_fields = [("id", int), ("items_in", list), ("items_out", list)]
        optional_fields = [("name", str), ("requirements", list), ("xp_reward", dict)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        # Convert xp_reward dict from being str-keyed to being int-keyed
        if "xp_reward" in kwargs:
            kwargs["xp_reward"] = {int(k): v for k, v in kwargs["xp_reward"].items()}

        return Recipe(json["id"], json["items_in"], json["items_out"], **kwargs)
