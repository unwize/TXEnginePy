from enum import Enum

import game
import game.systems.entity.entities as entities
import game.systems.item as item
from game.cache import get_cache, cached, from_cache
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent, ComponentFactory
from game.structures.state_device import FiniteStateDevice
from game.systems.event.add_item_event import AddItemEvent
from game.systems.event.inspect_item_event import InspectItemEvent
from game.systems.item.item import Item
from game.systems.room.action.actions import Action


class ShopAction(Action):
    """
    An Action that simulates the user entering a shop.

    A Shop's flow is as follows:
    - 1. Display wares
    - 2. Select a ware or exit (input_type.int[ -1 : len(wares)])
        - Go to 12 if exit
    - 3. Prompt to purchase, get description, or cancel (input_type.int[-1 : 1])
    - 4. If cancel, go to 1. If get desc, go to 5. If purchase, go to 7
    - 5. Print selected item's description (input_type.NONE)
    - 6 Go to 3
    - 7. Check if purchase can be made. If yes, go to 8
    - 8. Confirm the purchase (input_type.affirmative)
    - 9. Go to 1
    - 10. Explain that the user has insufficient funds (input_type.none)
    - 11. Go to 1
    - 12. Terminate
    """

    class States(Enum):
        """
        Enum values to be used to represent state information within the ShopAction.

        Each enum value is correlated to the states described within the ShopAction docstring.
        """

        DEFAULT = 0
        DISPLAY_WARES = (2,)
        WARE_SELECTED = (3,)
        INSPECT_WARE = (5,)
        CONFIRM_WARE_PURCHASE = (8,)
        PURCHASE_FAILURE = (10,)
        TERMINATE = -1

    def get_text_header(self) -> str:
        cur = from_cache("player").coin_purse[self.default_currency]
        return f"Your {cur.name} balance: {cur}\n\n"

    def __init__(
        self, menu_name: str, wares: list[int], default_currency: int = 0, activation_text: str = "", *args, **kwargs
    ):
        super().__init__(
            menu_name,
            activation_text,
            ShopAction.States,
            ShopAction.States.DISPLAY_WARES,
            InputType.INT,
            *args,
            **kwargs,
        )
        self.wares: list[int] = wares  # list of tuples where idx[0] == item_id and idx[1] == item_cost
        self._ware_of_interest: Item = None  # The tuple of the ware last selected by the user
        self.default_currency: int = default_currency

        @FiniteStateDevice.state_logic(self, self.States.DISPLAY_WARES, InputType.INT, -1, len(self.wares) - 1)
        def _logic(user_input: int) -> None:
            if user_input == -1:  # Chose to exit
                self.set_state(self.States.TERMINATE)
            else:  # Chose an item
                self.ware_of_interest = self.wares[user_input]
                self.set_state(self.States.WARE_SELECTED)

        @FiniteStateDevice.state_content(self, self.States.DISPLAY_WARES)
        def _content():
            return ComponentFactory.get([self.get_text_header(), self.activation_text], self._ware_to_option())

        @FiniteStateDevice.state_logic(
            self, self.States.WARE_SELECTED, InputType.INT, -1, lambda: len(self._get_ware_options()) - 1
        )
        def _logic(user_input: int) -> None:
            # TODO: Handle input dispatching better. Remove hardcoded state transitions
            if user_input == -1:
                self.set_state(self.States.DISPLAY_WARES)
            elif user_input == 0:
                self.set_state(self.States.CONFIRM_WARE_PURCHASE)
            elif user_input == 1:
                self.set_state(self.States.INSPECT_WARE)

        @FiniteStateDevice.state_content(self, self.States.WARE_SELECTED)
        def _content():
            return ComponentFactory.get(
                [
                    self.get_text_header(),
                    "What would you like to do with ",
                    StringContent(value=self.ware_of_interest.name, formatting="item_name"),
                    "?",
                ],
                self._get_ware_options(),
            )

        @FiniteStateDevice.state_logic(self, self.States.INSPECT_WARE, InputType.SILENT)
        def _logic(_: any) -> None:
            game.add_state_device(InspectItemEvent(self.ware_of_interest.id))
            self.set_state(self.States.WARE_SELECTED)

        @FiniteStateDevice.state_logic(self, self.States.CONFIRM_WARE_PURCHASE, InputType.AFFIRMATIVE)
        def _logic(user_input: bool) -> None:
            if user_input:
                player: entities.Player = get_cache()["player"]
                if player.coin_purse.test_purchase(self.ware_of_interest.id, self.default_currency):
                    player.coin_purse.spend(self.ware_of_interest.get_market_value(self.default_currency))
                    game.add_state_device(AddItemEvent(self.ware_of_interest.id))  # Spawn a new AddItemEvent
                    self.set_state(self.States.DISPLAY_WARES)

                else:
                    self.set_state(self.States.PURCHASE_FAILURE)

            else:
                self.set_state(self.States.WARE_SELECTED)

        @FiniteStateDevice.state_content(self, self.States.CONFIRM_WARE_PURCHASE)
        def _content():
            return ComponentFactory.get(
                [
                    self.get_text_header(),
                    "Are you sure that you would like to purchase 1x ",
                    StringContent(value=self.ware_of_interest.name + ":\n", formatting="item_name"),
                    " for ",
                    StringContent(
                        value=str(self.ware_of_interest.get_market_value(self.default_currency)), formatting="item_cost"
                    ),
                    "?",
                ]
            )

        @FiniteStateDevice.state_logic(self, self.States.PURCHASE_FAILURE, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.DISPLAY_WARES)

        @FiniteStateDevice.state_content(self, self.States.PURCHASE_FAILURE)
        def _content():
            return ComponentFactory.get(
                [
                    self.get_text_header(),
                    "Cannot purchase ",
                    StringContent(value=self.ware_of_interest.name, formatting="item_name"),
                    ". Item costs ",
                    StringContent(
                        value=str(self.ware_of_interest.get_market_value(self.default_currency)), formatting="item_cost"
                    ),
                    ", but you only have RETRIEVE USER CURRENCY.\nYou need USER CURRENCY - COST more to purchase.",
                ]
            )

        @FiniteStateDevice.state_content(self, self.States.TERMINATE, True)
        def _content():
            return ComponentFactory.get(["You leave the shop."])

    @property
    def ware_of_interest(self) -> Item:
        return self._ware_of_interest

    @ware_of_interest.setter
    def ware_of_interest(self, i: Item | int) -> None:
        if type(i) is int:
            self._ware_of_interest = item.item_manager.get_instance(i)
        elif isinstance(i, Item):
            self._ware_of_interest = i
        else:
            raise TypeError(f"Ware of interest cannot be set to {type(i)}. Acceptable types are int, Item.")

    def _get_ware_options(self) -> list[list[StringContent | str]]:
        return [
            [
                "Purchase ",
                StringContent(value=self.ware_of_interest.name, formatting="item_name"),
                " for ",
                StringContent(
                    value=str(self.ware_of_interest.get_market_value(self.default_currency)), formatting="item_cost"
                ),
            ],
            ["Read ", StringContent(value=self.ware_of_interest.name, formatting="item_name"), "'s description"],
        ]

    def _ware_to_option(self) -> list[list[StringContent | str]]:
        """
        Convert a list of ware tuples into formatted lists of StringContent

        Returns: A list of list[StringContent | str]. This list contains lists that contain the item available for
        purchase at the shop as well as their costs.
        """
        return [
            [
                StringContent(value=item.item_manager.get_name(item_id), formatting="item_name"),
                " : ",
                StringContent(
                    value=str(item.item_manager.get_currency_value(item_id, self.default_currency, True)),
                    formatting="item_cost",
                ),
            ]
            for item_id in self.wares
        ]

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "ShopAction", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Required JSON fields:
        - menu_name: str
        - default_currency: int
        - wares: list[int]

        Optional JSON fields:
        - activation_text: str = None
        - requirements: list[Requirement] = None
        """

        required_fields: list = [("menu_name", str), ("default_currency", int), ("wares", list)]

        optional_fields = [("activation_text", str), ("requirements", list)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "ShopAction":
            raise ValueError("Invalid class field!")

        kwargs = {"requirements": LoadableFactory.collect_requirements(json)}

        if "activation_text" in json:
            kwargs["activation_text"] = json["activation_text"]

        return ShopAction(json["menu_name"], json["wares"], json["default_currency"], **kwargs)
