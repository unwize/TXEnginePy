from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.systems.faction.faction import Faction
from game.util.asset_utils import get_asset


class FactionManager(Manager):
    FACTION_ASSET_PATH = "factions"

    def __init__(self):
        super().__init__()
        self._manifest: dict[int, Faction] = {}

    def __contains__(self, item) -> bool:
        return self._manifest.__contains__(item)

    def __getitem__(self, item) -> Faction:
        return self._manifest.__getitem__(item)

    def get_affinity(self, faction_id: int) -> int:
        """
        Retrieve the affinity for a given faction
        """
        if faction_id not in self:
            raise ValueError(f"Unknown faction with id: {faction_id}")

        return self[faction_id].affinity

    def adjust_affinity(self, faction_id: int, quantity: int | float) -> None:
        """
        Adjust the affinity for a given faction.
        """
        if faction_id not in self:
            raise ValueError(f"Unknown faction with id: {faction_id}")

        self[faction_id].adjust_affinity(quantity)

    def register_faction(self, faction: Faction) -> None:
        """
        Register a Faction with the manager.
        """

        if faction.id in self:
            raise ValueError(f"Cannot register faction {faction.name}! A faction with id {faction.id} already exists!")

        self._manifest[faction.id] = faction

    def load(self) -> None:
        raw_asset: dict[str, any] = get_asset(self.FACTION_ASSET_PATH)
        for raw_faction in raw_asset["content"]:
            faction = LoadableFactory.get(raw_faction)
            if not isinstance(faction, Faction):
                raise TypeError(f"Expected object of type Faction, got {type(faction)} instead!")

            self.register_faction(faction)

    def save(self) -> None:
        pass
