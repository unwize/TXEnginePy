"""
All Dialog system related classes. Includes the Dialog logical components, JSON
translation functions, and related Events.
"""

import copy
import dataclasses
import weakref
from abc import ABC

from loguru import logger

import game
from game.cache import cached, from_cache
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.systems.event import Event
from game.systems.requirement.requirements import RequirementsMixin


@dataclasses.dataclass
class DialogNodeBase(ABC):
    """
    Abstract base class for DialogNode

    The DialogNodeBase is a self-contained data structure containing all the
    information required to run a particular "conversation node" with a greater
    Dialog object. DialogNodeBase is highly configurable but only requires a few
    values.
    Note that each DialogNodeBase within a Dialog must have an internally-unique
    node_id.

    Attributes:
        node_id: An internal unique identifier for the node.
        options: A list of responses the player can select for the text prompt.
        text:
            The text prompt shown to the user. This simulates the "speech" of
            the NPC on the other side of the Dialog
        visited: Has the node been visited by the player before?
        allow_multiple_visits:
            If False, the node will be hidden from `options` if visited==True
        multiple_event_triggers:
            If True, `on_enter` events will trigger each time node is visited.
            If False, only once.
        persistent: If True, node states are cached, saved, and loaded.
        on_enter: A collection of Events to be run when the node is visited
        text_before_events:
            If True, a TextEvent will be spawned on top of the `on_enter` events
            containing `text`.
    """

    node_id: int  # Unique ID for the node
    options: dict[str, int]  # A map of "options" to their corresponding nodes
    text: str
    visited: bool = False
    allow_multiple_visits: bool = True
    multiple_event_triggers: bool = False  # Events run each visit
    persistent: bool = False  # If True, properties will persist in storage
    on_enter: list[Event] = dataclasses.field(default_factory=list)
    text_before_events: bool = True
    __dialog_ref: "Dialog" = None

    def is_option_visible(self, option_text: str) -> bool:
        """
        Check that the target node specified by the provided option_text allows
        itself to be visited again and should be shown in the options list.

        Args:
            option_text: The node to check

        Returns: True if the option should be displayed
        """
        if not isinstance(option_text, str):
            raise TypeError(f"option_text must be a str! Got a " f"{type(option_text)} instead!")

        if self.owner is None:
            raise RuntimeError("Cannot check if a node is valid when " "`owner` is None!")

        dialog_option_target: int = self.options[option_text]

        # Early return, -1 is always valid and should make the dialog end
        if dialog_option_target == -1:
            return True

        if dialog_option_target not in self.owner.nodes:
            raise RuntimeError(
                f"Dialog: {self.owner.id}, Node: {self.node_id} has invalid"
                f" option: {option_text}. No such node with id "
                f"{dialog_option_target}!"
            )

        target_node: DialogNode = self.owner.nodes[dialog_option_target]

        return not target_node.visited or target_node.allow_multiple_visits

    def is_option_valid(self, option_text: str) -> bool:
        """
        Check if an option is visible and that its requirements are met (by the
        Player).

        Args:
            option_text: The node to check

        Returns: True if the node can be visited, otherwise False
        """
        if not isinstance(option_text, str):
            raise TypeError(f"option_text must be a str! Got a " f"{type(option_text)} instead!")

        if self.owner is None:
            raise RuntimeError("Cannot check if a node is valid when " "`owner` is None!")

        dialog_option_target: int = self.options[option_text]

        # Early return, -1 is always valid and should make the dialog end
        if dialog_option_target == -1:
            return True

        if dialog_option_target not in self.owner.nodes:
            raise RuntimeError(
                f"Dialog: {self.owner.id}, Node: {self.node_id} has invalid"
                f" option: {option_text}. No such node with id "
                f"{dialog_option_target}!"
            )

        target_node: DialogNode = self.owner.nodes[dialog_option_target]

        return target_node.is_requirements_fulfilled(from_cache("player")) and self.is_option_visible(option_text)

    @property
    def owner(self) -> "Dialog":
        return self.__dialog_ref

    @owner.setter
    def owner(self, dialog: "Dialog") -> None:
        if not isinstance(dialog, Dialog):
            raise TypeError("A DialogNode's owner must be of type Dialog! Got" f" type {type(dialog)} instead!")

        self.__dialog_ref = weakref.proxy(dialog)

    def get_option_text(self) -> list[list[str]]:
        """
        Return a list containing all the strings for each option in the node
        """

        return [[s] for s in self.options.keys() if self.is_option_visible(s)]

    def should_trigger_events(self) -> bool:
        """
        Determine if events should be triggered.
        """

        return not self.visited or self.multiple_event_triggers

    def get_events(self) -> list[Event]:
        """
        Return a deep copy of each on_enter Event object.

        If an Event does not implement a custom __deep_copy__ method, unexpected
        behavior is likely.
        """
        return [copy.deepcopy(e) for e in self.on_enter]

    def trigger_events(self) -> None:
        """
        Run a deep copy of each event, as supplied by `get_events`
        """

        for event in self.get_events():
            game.add_state_device(event)


class DialogNode(RequirementsMixin, LoadableMixin, DialogNodeBase):
    """
    A DialogNodeBase that implements the Requirement interface and Loadable
    interface.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.persistent:
            # TODO: Handle fetching properties from storage
            pass

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "DialogNode", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a DialogNode object from a JSON blob.

        Required JSON fields:
        - node_id: int
        - options: dict[str, int]
        - text: str

        Optional JSON fields:
        - visited: bool
        - allow_multiple_visits: bool
        - multiple_event_triggers: bool
        - persistent: bool
        - on_enter: list[Event]
        - text_before_events: bool

        Args:
            json: A raw JSON dict

        Returns:
            A DialogNode converted from the supplied JSON dict

        Raises:
            ValueError: Incorrect field value was supplied
            TypeError: Incorrect field type was supplied

        """

        required_fields = [("node_id", int), ("options", dict), ("text", str)]

        optional_fields = [
            ("visited", bool),
            ("allow_multiple_visits", bool),
            ("multiple_event_triggers", bool),
            ("persistent", bool),
            ("on_enter", list),
            ("text_before_events", bool),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "DialogNode":
            raise ValueError()

        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        if "on_enter" in kwargs:
            actual_events = []
            for raw_event in kwargs["on_enter"]:
                try:
                    actual_events.append(LoadableFactory.get(raw_event))
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Caught an error generated by a loader while "
                        f"attempting to load a DialogNode with id"
                        f" {json['node_id']}!"
                    )
                    raise e

            kwargs["on_enter"] = actual_events

        return DialogNode(node_id=json["node_id"], options=json["options"], text=json["text"], **kwargs)


class DialogBase(ABC):
    """
    Abstract base Class for Dialog objects that implements all non-interface
    functionality of Dialog.

    Attributes:
        id: A globally-unique identifier for the Dialog
        nodes: A collection of DialogNodes
        initial_node_id: Which node the Dialog should start from
        _current_node: The id of the node the player is currently on
    """

    def __init__(self, dialog_id: int, nodes: list[DialogNode], initial_node_id: int = 0):
        if len(nodes) < 1:
            raise ValueError("Unable to instantiate Dialog Object with zero nodes!")
        self.id = dialog_id
        self.nodes: dict[int, DialogNode] = {n.node_id: n for n in nodes}
        self.initial_node_id: int = initial_node_id
        self._current_node: int = initial_node_id

        if initial_node_id not in self.nodes:
            raise ValueError(f"Invalid starting node id {initial_node_id} " f"for Dialog with id {self.id}")

        # Ensure all nodes have owner set correctly
        for node in self.nodes.values():
            node.owner = self

    @property
    def current_node(self) -> int:
        """
        A simple wrapper for the internal _current_node value
        Returns:
            _current_node, the ID of the DialogNode currently being visited by
            the player.

        """
        return self._current_node

    @current_node.setter
    def current_node(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError(f"current_node must be of type int! Got object of type  " f"{type(value)} instead.")

        if value not in self.nodes:
            raise ValueError(f"Unknown DialogNode with id {value}!")

        self._current_node = value

    def get(self) -> DialogNode:
        """
        Return the instance of the node the player is currently on.

        Returns:
            None if the player wants to terminate the Dialog. Otherwise, returns
            a reference to the DialogNode that the player is currently visiting.
        """
        return self.nodes[self._current_node] if self._current_node >= 0 else None


class Dialog(LoadableMixin, DialogBase):
    """
    A class that implements a logic back-end and datastructure for NPC
    dialog. Intended to be embedded within FiniteStateDevice objects.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Dialog", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Loads a Dialog object from a JSON blob.

        Required JSON fields:
        - id: int
        - nodes: list[DialogNode]

        Optional JSON fields:
        - single-use: bool
        """

        required_fields = [("id", int), ("nodes", list)]

        optional_fields = [("single-use", bool)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "Dialog":
            raise ValueError()

        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        real_nodes = []
        for raw_node in json["nodes"]:
            try:
                real_nodes.append(LoadableFactory.get(raw_node))
            except Exception as e:
                logger.error(f"Something went wrong while loading a DialogNode" f"for Dialog with id:{json['id']}!")
                raise e

        return Dialog(dialog_id=json["id"], nodes=real_nodes, **kwargs)
