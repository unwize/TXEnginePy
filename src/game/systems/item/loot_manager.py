from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.systems.item.loot import LootTable
from game.util.asset_utils import get_asset


class LootManager(Manager):
    """
    The global manager for reusable loot tables
    """

    LOOT_ASSET_PATH = "loot"

    def __init__(self):
        super().__init__()
        self._manifest: dict[int, LootTable] = {}

    def register_loot_table(
        self,
        loot_table_id: int,
        item_probabilities: dict[int, float] = None,
        drop_probabilities: dict[int, float] = None,
        instance: LootTable = None,
    ):
        """
        Register a LootTable with the manager.

        Supply `item_probabilities` and `drop_probabilities` or provide an instance of an existing LootTable.

        args:
            loot_table_id: A unique ID to register the LootTable to
            item_probabilities: A dict where the key is an Item ID and the value is the probability it is dropped
            drop_probabilities: a dict where the key is a quantity of Items to drop and the value is the probability
            instance: An instance of the LootTable class
        """
        if loot_table_id in self._manifest:
            raise ValueError(f"LootTable with id {loot_table_id} already exists!")

        if instance is not None:
            self._manifest[instance.id] = instance
        else:
            self._manifest[loot_table_id] = LootTable(loot_table_id, item_probabilities, drop_probabilities)

    def get_instance(self, loot_table_id: int) -> LootTable:
        return self._manifest[loot_table_id]

    def load(self) -> None:
        """
        Load LootTable objects from disk and register them with the Manager.
        """
        raw_asset: dict[str, any] = get_asset(self.LOOT_ASSET_PATH)
        for raw_loot_table in raw_asset["content"]:
            table = LoadableFactory.get(raw_loot_table)
            if not isinstance(table, LootTable):
                raise TypeError(f"Expected object of type Ability, got {type(table)} instead!")

            self.register_loot_table(table.id, instance=table)

    def save(self) -> None:
        pass
