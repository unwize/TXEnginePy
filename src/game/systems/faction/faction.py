from abc import ABC

from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory


class FactionBase(ABC):
    """
    A Faction represents a thematic group set within a game world. A faction's
    affinity represents how positively or negatively that faction feels towards
    the player.

    Faction affinity may be increased or decreased via Events and can be checked
    via Requirements.
    """

    def __init__(self, name: str, id: int, tags: list[str] = None, affinity: int = 0):
        self.name = name
        self.id = id
        self.tags = tags or []
        self._affinity = affinity

    @property
    def affinity(self) -> int:
        return self._affinity

    @affinity.setter
    def affinity(self, value: int) -> None:
        assert type(value) is int
        self._affinity = value

    def adjust_affinity(self, quantity: int | float) -> None:
        """
        Adjust the value of the Faction's affinity.

        If an int is passed, adjust by a flat value. If a float is passed,
        adjust by a percentage where % change = quantity * 100

        Args:
            quantity: The quantity by which to adjust affinity

        Returns: None
        """
        if type(quantity) is int:
            self._affinity += quantity
        elif type(quantity) is float:
            self._affinity += self._affinity * quantity
        else:
            raise TypeError(f"Cannot adjust affinity by type {type(quantity)} Must be an int or float!")


class Faction(LoadableMixin, FactionBase):
    def __init__(self, name: str, id: int, tags: list[str] = None, affinity: int = 0, **kwargs):
        super().__init__(name=name, id=id, tags=tags, affinity=affinity, **kwargs)

    @staticmethod
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a Faction object from a JSON blob.

        Required JSON fields:
        name: (str)
        id: (int)
        tags: [str]
        affinity: (int)
        """

        required_fields = [("name", str), ("id", int), ("tags", list), ("affinity", int)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "Faction":
            raise ValueError()

        return Faction(json["name"], json["id"], json["tags"], json["affinity"])
