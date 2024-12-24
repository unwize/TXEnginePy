import enum

from game.structures.enums import InputType
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

    def __init__(self, menu_name: str, activation_text: str, states: type[enum.Enum], dialog_id: int, *args, **kwargs):
        super().__init__(menu_name, activation_text, states, self.States.DEFAULT, InputType.SILENT, *args, **kwargs)

        self.dialog_id = dialog_id




