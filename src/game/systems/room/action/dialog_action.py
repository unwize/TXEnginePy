import enum

import game
from game.cache import cached
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.systems.event.dialog_event import DialogEvent
from game.systems.room.action.actions import Action


class DialogAction(Action):
    """
    A simple wrapper for a DialogEvent.
    """

    class States(enum.Enum):
        """
        The DialogEvent will self-terminate, so only one real state is needed.
        """

        DEFAULT = 0
        TERMINATE = -1

    def __init__(self, menu_name: str, activation_text: str, dialog_id: int, *args, **kwargs):
        super().__init__(
            menu_name, activation_text, self.States, self.States.DEFAULT, InputType.SILENT, *args, **kwargs
        )

        self.dialog_id = dialog_id

        @self.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_) -> None:
            game.add_state_device(DialogEvent(self.dialog_id))
            self.set_state(self.States.TERMINATE)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "DialogAction", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a DialogAction object from a JSON blob.

        Required JSON fields:
        - menu_name: str
        - activation_text: str
        - dialog_id: int

        Optional JSON fields:
        - visible: bool
        - reveal_after_use: list[str]
        - persistent: bool
        - tags: list[str]

        Args:
            json: A raw JSON dict

        Returns:
            A DialogNode converted from the supplied JSON dict

        Raises:
            ValueError: Incorrect field value was supplied
            TypeError: Incorrect field type was supplied

        """

        required_fields = [("menu_name", str), ("activation_text", str), ("dialog_id", int)]

        optional_fields = [("visible", bool), ("reveal_after_use", list), ("persistent", bool), ("tags", list)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "DialogAction":
            raise ValueError()

        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        return DialogAction(json["menu_name"], json["activation_text"], json["dialog_id"], **kwargs)
