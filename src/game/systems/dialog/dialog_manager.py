"""
A singleton manager class that handles the master instances of each Dialog.
"""

import copy

from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
from game.systems.dialog.dialog import Dialog
from game.util.asset_utils import get_asset


class DialogManager(Manager):
    """
    A singleton manager class that handles the master instances of each Dialog.
    """

    DIALOG_ASSET_PATH = "dialogs"

    def __init__(self):
        super().__init__()
        self._manifest: dict[int, Dialog] = {}

    def __contains__(self, item) -> bool:
        return self._manifest.__contains__(item)

    def __getitem__(self, item) -> Dialog:
        return self._manifest.__getitem__(copy.deepcopy(item))

    def register_dialog(self, dialog: Dialog) -> None:
        """
        Register a Dialog with the manager.
        """

        if dialog.id in self:
            raise ValueError(f"Cannot register Dialog {dialog.id}! A Dialog with id {dialog.id} already exists!")

        self._manifest[dialog.id] = dialog

    def load(self) -> None:
        raw_asset: dict[str, any] = get_asset(self.DIALOG_ASSET_PATH)
        for raw_dialog in raw_asset["content"]:
            dialog = LoadableFactory.get(raw_dialog)
            if not isinstance(dialog, Dialog):
                raise TypeError(f"Expected object of type Faction, got {type(dialog)} instead!")

            self.register_dialog(dialog)

    def save(self) -> None:
        pass
