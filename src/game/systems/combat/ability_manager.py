import copy

from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.systems.combat.ability import Ability
from game.util.asset_utils import get_asset


class AbilityManager(Manager):
    ABILITY_ASSET_PATH = "abilities"

    def __init__(self):
        super().__init__()
        self._manifest: dict[str, Ability] = {}

    def register_ability(self, ability: Ability) -> None:
        if ability.name in self._manifest:
            raise ValueError(f"Ability with name {ability.name} already exists!")

        self._manifest[ability.name] = ability

    def is_ability(self, ability_name: str) -> bool:
        return ability_name in self._manifest

    def get_instance(self, ability_name) -> Ability:
        if ability_name not in self._manifest:
            raise ValueError(f"{ability_name} is not a valid ability!")

        return copy.deepcopy(self._manifest[ability_name])

    def load(self) -> None:
        """
        Load Ability objects from JSON.

        Dispatch dict-form ability data to the 'from_json' assigned to Ability class via LoadableFactory.
        """
        raw_asset: dict[str, any] = get_asset(self.ABILITY_ASSET_PATH)
        for raw_ability in raw_asset["content"]:
            ability = LoadableFactory.get(raw_ability)
            if not isinstance(ability, Ability):
                raise TypeError(f"Expected object of type Ability, got {type(ability)} instead!")

            self.register_ability(ability)

    def save(self) -> None:
        pass
