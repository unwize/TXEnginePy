from abc import ABC

from game.cache import cached
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory


class BaseCurrency(ABC):
    """Currency records information about money an entity owns.

    Currency objects have a name, quantity, and one or more stages.
    A stage describes a quantified grouping. For example, USD has a stage of "cents: 1" and "dollars: 100"
    A Currency must have a first stage with a value of 1.
    """

    def __init__(self, id: int, name: str, stages: dict[str, int], quantity: int = 0, allow_negative: bool = False):
        super().__init__()

        self.id: int = id
        self.name: str = name
        self.stages: dict[str, int] = stages
        self.quantity: int = quantity
        self.allow_negative: bool = allow_negative

        # Sort the stages in ascending order, keyed by their numerical values
        self.sorted_stages = list(self.stages.items())
        self.sorted_stages.sort(key=lambda x: x[1])
        self.sorted_stages.reverse()


class Currency(LoadableMixin, BaseCurrency):
    """
    Currency records information about money an entity owns.

    Currency objects have a name, quantity, and one or more stages.
    A stage describes a quantified grouping. For example, USD has a stage of "cents: 1" and "dollars: 100"
    A Currency must have a first stage with a value of 1.
    """

    def __init__(
        self, id: int, name: str, stages: dict[str, int], quantity: int = 0, allow_negative: bool = False, **kwargs
    ):
        super().__init__(id=id, name=name, stages=stages, quantity=quantity, allow_negative=allow_negative, **kwargs)

    @property
    def key(self) -> tuple[int, str]:
        return self.id, self.name

    def __str__(self) -> str:
        base: str = ""
        working_quantity: int = self.quantity
        non_zero_stage_found: bool = False

        # If the currency is zero
        if self.quantity == 0:
            return f"0 {self.sorted_stages[-1][0]}"

        for stage_name, stage_scale in self.sorted_stages:
            stage_quantity: int = int(working_quantity / stage_scale)  # Amount of currency that fit into the stage

            if stage_quantity != 0:
                non_zero_stage_found = True

            if stage_quantity == 0 and not non_zero_stage_found:
                continue

            remainder: int = int(working_quantity - (stage_scale * stage_quantity))  # How much currency is left
            working_quantity = remainder
            stage_str = f"{stage_quantity} {stage_name} "
            base = base + stage_str

        return base.strip()

    def __repr__(self):
        return self.__str__()

    def __add__(self, other):
        # If (Currency + Currency)
        if isinstance(other, type(self)):
            if self.id != other.id:
                raise ValueError(f"Cannot add currencies of different names! {self.name}, {other.name}")

            return Currency(self.id, self.name, self.stages, self.quantity + other.quantity)

        # If (Currency + Int)
        elif isinstance(other, int):
            return Currency(self.id, self.name, self.stages, self.quantity + other)

        else:
            raise TypeError(f"Cannot add {type(self)} and {type(other)}!")

    def __sub__(self, other):
        # If (Currency - Currency)
        if isinstance(other, type(self)):
            if self.name != other.name:
                raise ValueError(f"Cannot subtract currencies of different names! {self.name}, {other.name}")

            return Currency(self.id, self.name, self.stages, self.quantity - other.quantity)

        # If (Currency - Int)
        elif isinstance(other, int):
            return Currency(self.id, self.name, self.stages, self.quantity - other)
        else:
            raise TypeError(f"Cannot subtract  {type(self)} and {type(other)}!")

    def __mul__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return Currency(self.id, self.name, self.stages, int(self.quantity * other))

        else:
            raise TypeError(f"A Currency may only be multiplied by int or float! Got {type(other)}")

    def __truediv__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return Currency(self.id, self.name, self.stages, int(self.quantity / other))

        else:
            raise TypeError(f"A Currency may only be multiplied by int or float! Got {type(other)}")

    def adjust(self, amount: int | float):
        """Adjust quantity by 'amount'.

        If amount is an int, simply add it to 'quantity' (flat adjustment).  2 + 3 = 5
        If amount is a float, multiply 'quantity' by it (percent adjustment). 2 x 0.5 = 1
        """
        if type(amount) is int:
            self.quantity = self.quantity + amount

        elif type(amount) is float:
            self.quantity = round(self.quantity * amount)

        else:
            raise TypeError(f"Unknown type: {type(amount)}! Expected type: int | float")

    def set(self, quantity: int):
        """Set 'quantity' to the passed value."""

        if type(quantity) is int:
            self.quantity = quantity
        else:
            raise TypeError(f"Cannot set a Currency's quantity to type {type(quantity)}! Must be of type int.")

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Currency", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Required JSON fields:
        - id: int
        - name: str,
        - stages: dict[str, int]

        Optional JSON fields:
        - quantity: int = 0
        - allow_negative: bool = False
        """

        required_fields = [("id", int), ("name", str), ("stages", dict)]

        optional_fields = [("quantity", int), ("allow_negative", bool)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "Currency":
            raise ValueError("Invalid class field!")

        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        return Currency(json["id"], json["name"], json["stages"], **kwargs)
