from enum import Enum

import game
from game.cache import cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems.event.events import EntityTargetMixin, Event
from game.systems.event.inspect_item_event import InspectItemEvent


class ViewInventoryEvent(EntityTargetMixin, Event):
    """
    An Event that allows the player to browse an Entity's InventoryController, but not edit it.
    """

    class States(Enum):
        DEFAULT = 0
        CHOOSE_ITEM = 1
        EMPTY = 2
        CALCULATE_INSPECTION_OPTIONS = 3
        CHOOSE_ITEM_INSPECTION_OPTION = 4
        VIEW_DESC = 5
        VIEW_ITEM_VALUE = 6
        VIEW_FUNCTIONAL_DESC = 7
        VIEW_ITEM_STATS = 8
        TERMINATE = -1

    @classmethod
    def get_item_inspection_options(cls):
        """
        Get a list of tuples in the following format: (`type`, `listing text`, `transit state`)
        """
        from game.systems.item.item import Item, Usable, Equipment

        return [
            (Item, "View description", cls.States.VIEW_DESC),
            (Item, "View value", cls.States.VIEW_ITEM_VALUE),
            (Usable, "View functional description", cls.States.VIEW_FUNCTIONAL_DESC),
            (Equipment, "View functional description", cls.States.VIEW_FUNCTIONAL_DESC),
            (Equipment, "View stats", cls.States.VIEW_ITEM_STATS),
        ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        from game.systems.entity.mixins.inventory_mixin import InventoryMixin

        if not isinstance(self.target, InventoryMixin):
            raise TypeError("Cannot view inventory of Entity not of type InventoryMixin!")

        self.stack_index: int | None = None

        self._setup_states()

    def _get_available_inspection_options(self, item_id: int) -> dict[str, States]:
        """
        For a given item id, check which inspection options are available for that type of item and return a dict
        formatted for FiniteStateDevice.user_branching_state.

        The returned format is a dict where the key is a str shown to the user and the value is the state to transition
        to if the str is selected.

        args:
            item_id: an int representing the ID of the item to check against

        returns: a dict formatted to be compatible with FiniteStateDevice.user_branching_state
        """
        inst = from_cache("managers.ItemManager").get_instance(item_id)

        return {text: state for cls, text, state in self.get_item_inspection_options() if isinstance(inst, cls)}

    def _setup_states(self) -> None:
        @self.state_logic(self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any):
            if self.target.inventory.size == 0:
                self.set_state(self.States.EMPTY)

            else:
                self.set_state(self.States.CHOOSE_ITEM)

        @self.state_logic(self.States.CHOOSE_ITEM, InputType.INT, -1, lambda: self.target.inventory.size - 1)
        def _logic(user_input: int) -> None:
            if user_input == -1:
                self.set_state(self.States.TERMINATE)
            else:
                self.stack_index = user_input
                self.set_state(self.States.CALCULATE_INSPECTION_OPTIONS)

        @self.state_content(self.States.CHOOSE_ITEM)
        def _content() -> dict:
            return ComponentFactory.get(["What stack would you like to inspect?"], self.target.inventory.to_options())

        @self.state_logic(self.States.CALCULATE_INSPECTION_OPTIONS, InputType.SILENT)
        def _logic(_: any) -> None:
            # Fetch available inspection options
            opt = self._get_available_inspection_options(self.stack_index)

            # Build the CHOOSE_ITEM_INSPECTION_OPTION state in real time using the results in opt
            FiniteStateDevice.user_branching_state(
                self, self.States.CHOOSE_ITEM_INSPECTION_OPTION, opt, back_out_state=self.States.CHOOSE_ITEM
            )
            self.set_state(self.States.CHOOSE_ITEM_INSPECTION_OPTION)

        @self.state_logic(self.States.VIEW_DESC, InputType.SILENT)
        def _logic(_: any) -> None:
            game.add_state_device(InspectItemEvent(self.target.inventory.items[self.stack_index].id))
            self.set_state(self.States.CHOOSE_ITEM_INSPECTION_OPTION)

        @self.state_logic(self.States.VIEW_FUNCTIONAL_DESC, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.CHOOSE_ITEM_INSPECTION_OPTION)

        @self.state_content(self.States.VIEW_FUNCTIONAL_DESC)
        def _content() -> dict:
            """
            Return a content dict displaying the selected-item's name and description
            """
            return ComponentFactory.get(
                [
                    StringContent(value=self.target.inventory.items[self.stack_index].ref.name, formatting="item_name"),
                    "\n",
                    self.target.inventory.items[self.stack_index].ref.functional_description,
                ]
            )

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ViewSkillsEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        raise NotImplementedError("ViewInventoryEvent does not support JSON loading!")
