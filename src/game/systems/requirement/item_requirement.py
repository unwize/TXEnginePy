import game
from game.cache import cached, from_cache
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent
from game.systems import item as item
from game.systems.event.events import TextEvent
from game.systems.requirement.requirements import Requirement


class ItemRequirement(Requirement):
    """
    Enforce that the player must have 'n' of a given item in his/her inventory.
    """

    def __init__(self, item_id: int, item_quantity: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_id: int = item_id
        self.item_quantity: int = item_quantity

    def fulfilled(self, entity) -> bool:
        return entity.inventory.total_quantity(self.item_id) >= self.item_quantity

    @property
    def description(self) -> list[str | StringContent]:
        return [
            "You must have at least ",
            StringContent(value=f"{self.item_quantity}x", formatting="item_quantity"),
            " ",
            StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
            "!",
        ]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ItemRequirement", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a ItemRequirement object from a JSON blob.

        Required JSON fields:
        - item_id (int)
        - item_quantity (int)
        """

        required_fields = [("item_id", int), ("item_quantity", int)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "ItemRequirement":
            raise ValueError()

        return ItemRequirement(json["item_id"], json["item_quantity"])


class ConsumeItemRequirement(ItemRequirement):
    """
    Enforce that the player must have and consume 'n' of a given item in his/her inventory.
    """

    def __init__(self, item_id: int, item_quantity: int):
        super().__init__(item_id, item_quantity)

    def fulfilled(self, entity) -> bool:
        if entity.inventory.total_quantity(self.item_id) < self.item_quantity:
            return False

        prompt = [
            "You consumed ",
            StringContent(value=f"{self.item_quantity}x ", formatting="item_quantity"),
            " ",
            StringContent(value=f"{from_cache('managers.ItemManager').get_instance(self.item_id).name}."),
        ]

        entity.inventory.consume_item(self.item_id, self.item_quantity)
        game.add_state_device(TextEvent(prompt))
        return True

    @property
    def description(self) -> list[str | StringContent]:
        return [
            "You must have at least ",
            StringContent(value=f"{self.item_quantity}x", formatting="item_quantity"),
            " ",
            StringContent(value=f"{item.item_manager.get_name(self.item_id)}", formatting="item_name"),
            "!",
        ]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ConsumeItemRequirement", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a ConsumeItemRequirement object from a JSON blob.

        Required JSON fields:
        - item_id (int)
        - item_quantity (int)
        """

        required_fields = [("item_id", int), ("item_quantity", int)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "ConsumeItemRequirement":
            raise ValueError()

        return ConsumeItemRequirement(json["item_id"], json["item_quantity"])
