from enum import Enum

import game
from game.cache import from_cache, cached
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import ComponentFactory
from game.systems.dialog.dialog import DialogNode, Dialog
from game.systems.event import Event
from game.systems.event.events import TextEvent


class DialogEvent(Event):
    """
    An Event that hosts the Dialog objects logic and manages spawning
    TextEvents for it.
    """

    class States(Enum):
        """
        Internal Enum for FSD states.
        """

        DEFAULT = 0
        VISIT_NODE = 1
        TERMINATE = -1

    @property
    def current_node(self) -> DialogNode | None:
        """
        Fetches a reference to the DialogNode the player is visiting.
        Returns:
            A DialogNode if the player is visiting a valid DialogNode. Otherwise
            returns None.
        """
        return self.dialog.get()

    @current_node.setter
    def current_node(self, value: int) -> None:
        """
        Set the current_node.

        Args:
            value: The ID of the new DialogNode to set to current_node

        Returns: None

        """
        if not isinstance(value, int):
            raise ValueError(f"Cannot set current_node to value of type {type(value)}! " f"Expected an int!")

        self.dialog.current_node = value

    def __init__(self, dialog_id: int, **kwargs):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT, **kwargs)

        self.dialog: Dialog = None

        @self.state_logic(self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self.dialog = from_cache("managers.DialogManager")[dialog_id]
            self.set_state(self.States.VISIT_NODE)

            # Ensure that the initial state is valid.
            if not self.current_node:
                raise RuntimeError(
                    f"Failed to start Dialog with id {self.dialog.id}! "
                    f"Initial state of id {self.dialog.current_node} returned "
                    f"None!"
                )

        @self.state_logic(
            self.States.VISIT_NODE,
            InputType.INT,
            input_min=0,
            input_max=lambda: len(self.current_node.get_option_text()) - 1,
        )
        def _logic(user_input: int):
            self.current_node.visited = True
            user_choice: str = self.current_node.get_option_text()[user_input][0]
            next_node: int = self.current_node.options[user_choice]
            if next_node < 0:
                self.set_state(self.States.TERMINATE)
                return

            self.current_node = self.dialog.nodes[next_node].node_id
            if self.current_node.should_trigger_events():
                self.current_node.trigger_events()

                if self.current_node.text_before_events:
                    # Add a text event on top of the triggered events with the
                    # node's main text.
                    # This will allow the user to read the text of the node
                    # before "seeing" the triggered events.
                    game.add_state_device(TextEvent(self.current_node.text))

        @self.state_content(self.States.VISIT_NODE)
        def _content() -> dict:
            return ComponentFactory.get([self.current_node.text], self.current_node.get_option_text())

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "DialogEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a LearnRecipeEvent object from a JSON blob.

        Required JSON fields:
        - dialog_id (int)
        """

        required_fields = [("dialog_id", int)]

        LoadableFactory.validate_fields(required_fields, json)

        if json["class"] != "DialogEvent":
            raise ValueError()

        return DialogEvent(json["dialog_id"])
