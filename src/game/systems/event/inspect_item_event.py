from __future__ import annotations

from enum import Enum

from game.cache import from_cache
from game.structures.enums import InputType
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.event import Event


class InspectItemEvent(Event):
    """
    A simple Event that prints the inspection details of a specific Item to
    the player.

    InspecItemEvent checks the subtype of Item fetched and will display extra
    information accordingly.
     - An Item has its description and values printed.
     - A Usable prints what Item prints and adds its functional description.
     - An Equipment prints what Item prints and adds tags and stats.
    """

    class States(Enum):
        DEFAULT = 0
        CHECK_TYPE = 1
        INSPECT_ITEM = 2
        INSPECT_USABLE = 3
        INSPECT_EQUIPMENT = 4
        TERMINATE = -1

    def __init__(self, item_id: int):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self.item_id = item_id
        self.ref = from_cache("managers.ItemManager").get_instance(self.item_id)

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self.set_state(self.States.CHECK_TYPE)

        @FiniteStateDevice.state_logic(self, self.States.CHECK_TYPE, InputType.SILENT)
        def _logic(_: any) -> None:
            from game.systems.item.item import Item, Usable, Equipment

            if isinstance(self.ref, Equipment):
                self.set_state(self.States.INSPECT_EQUIPMENT)
            elif isinstance(self.ref, Usable):
                self.set_state(self.States.INSPECT_USABLE)
            elif isinstance(self.ref, Item):
                self.set_state(self.States.INSPECT_ITEM)
            else:
                raise TypeError("ref did not fetch an Item instance!")

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_ITEM, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSPECT_ITEM)
        def _content() -> dict:
            return ComponentFactory.get(
                [
                    self.ref.name,
                    "'s Summary",
                    "\n",
                    self.ref.description,
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in self.ref.market_values]),
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_USABLE, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSPECT_USABLE)
        def _content() -> dict:
            return ComponentFactory.get(
                [
                    self.ref.name,
                    "'s Summary",
                    "\n",
                    self.ref.functional_description,
                    "\n",
                    self.ref.description,
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in self.ref.market_values]),
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_EQUIPMENT, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.INSPECT_EQUIPMENT)
        def _content() -> dict:
            """
            Print in the following format:
                * item.name
                * Value:
                * |cur.name\t|cur.value\t|
                * item.desc
            """
            return ComponentFactory.get(
                [
                    self.ref.name,
                    "'s Summary",
                    "\n",
                    self.ref.functional_description,
                    "\n",
                    self.ref.description,
                    "\n",
                    "Stats:",
                    "\n",
                    "\n".join([f" - {k}: {v}" for k, v in self.ref.get_stats().items()]),
                ]
                + (
                    [
                        "\n\n" "Type Resistances:",
                        "\n",
                        "\n".join([f" - {t}: {v * 100}%" for t, v in self.ref.tags.items()]),
                    ]
                    if len(self.ref.tags)
                    else []
                )
                + [
                    "\n\n",
                    "Market Values:",
                    "\n",
                    "\n".join([f" - {c.name}: {str(c)}" for c in self.ref.market_values]),
                ]
            )
