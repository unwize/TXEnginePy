from enum import Enum

from game.cache import cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems.event.events import Event


class UseItemEvent(Event):
    class States(Enum):
        DEFAULT = 0
        USE_ITEM = 1
        NOT_USABLE = 2
        NOT_REQUIREMENTS = 3
        TERMINATE = -1

    def __init__(self, item_id: int, target=None):
        """
        Args:
            item_id: The id of the item to use
            target: The entity to pull items from
        """
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self.item_id: int = item_id
        self._target = target  # Type Entity
        self._item_instance = None

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self._item_instance = from_cache("managers.ItemManager").get_instance(item_id)

            # Check that the entity actually owns enough of the item to use it.
            # If not, raise and Error since it
            # shouldn't be possible to get to this point normally.
            if self.target.inventory.total_quantity(self.item_id) < 1:
                raise RuntimeError(
                    f"Cannot use an item with quantity less than 1! {self.target} failed to use item {self._item_instance}"
                )

            from game.systems.item.item import Usable

            if isinstance(self._item_instance, Usable):
                if self._item_instance.is_requirements_fulfilled(self.target):
                    self.set_state(self.States.USE_ITEM)
                else:
                    self.set_state(self.States.NOT_REQUIREMENTS)

            else:
                self.set_state(self.States.NOT_USABLE)

        @FiniteStateDevice.state_logic(self, self.States.NOT_REQUIREMENTS, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.NOT_REQUIREMENTS)
        def _content(_: any) -> dict:
            c = [
                "Failed to use ",
                StringContent(value=self._item_instance.name, formatting="item_name"),
                ". Requirements are not met.",
            ]
            return ComponentFactory.get(c, self._item_instance.get_requirements_as_options())

        @FiniteStateDevice.state_logic(self, self.States.NOT_USABLE, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.NOT_USABLE)
        def _content() -> dict:
            return ComponentFactory.get(
                [StringContent(value=self._item_instance.name, formatting="item_name"), " cannot be used."]
            )

        @FiniteStateDevice.state_logic(self, self.States.USE_ITEM, InputType.ANY)
        def _logic(_: any) -> None:
            self._item_instance.use(self.target)

            if self._item_instance.consumable:
                self.target.inventory.consume_item(self.item_id, 1)

            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.USE_ITEM)
        def _content() -> dict:
            return ComponentFactory.get(["You used ", self._item_instance.name, "."])

    @property
    def target(self):
        return self._target or from_cache("player")

    def __copy__(self):
        return UseItemEvent(self.item_id, target=self._target)

    def __deepcopy__(self, memodict={}):
        return self.__copy__()

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "UseItemEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        raise RuntimeError("UseItemEvent does not support JSON loading!")
