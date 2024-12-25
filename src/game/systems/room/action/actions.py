"""
A collection of base Action classes and simple utility Action subclasses.
"""

import enum
from abc import ABC
from enum import Enum

import game
import game.cache as cache
import game.systems.event.events as events
import game.systems.room as room
from game.structures.enums import InputType
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.state_device import FiniteStateDevice, StateDevice
from game.systems.requirement.requirements import RequirementsMixin


class Action(LoadableMixin, RequirementsMixin, FiniteStateDevice, ABC):
    """
    Base class for all actions.
    """

    def __init__(
        self,
        menu_name: str,
        activation_text: str,
        states: type[enum.Enum],
        default_state,
        default_input_type: InputType,
        visible: bool = True,
        reveal_after_use: list[str] = None,
        hide_after_use: bool = False,
        persistent: bool = False,
        tags: list[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(
            default_input_type=default_input_type, states=states, default_state=default_state, *args, **kwargs
        )

        self._menu_name: str = menu_name  # Name of the Action when viewed from a room
        self.activation_text: str = activation_text  # Text that is printed when the Action is run
        self.visible: bool = visible  # If True, visible in the owning Room
        self.hide_after_use: bool = hide_after_use  # If True, the action will set itself to hidden after being used
        self.reveal_after_use: list[str] = reveal_after_use  # Hide other actions in the room after this action is used
        self.room: room.Room = None  # The Room that owns this action. Should ONLY be a weakref.proxy
        self.persistent: bool = persistent
        self.tags: list[str] = tags  # Arbitrary string tags assigned to the action by the game designer

    @property
    def menu_name(self) -> str:
        """
        Programmatically return menu name. Some subclasses of Action may need to dynamically adjust this property.
        """

        return self._menu_name


class ExitAction(Action):
    """
    An Action that signals to the state_device_controller that the containing Room StateDevice should be terminated
    """

    class States(Enum):
        DEFAULT = 0
        TERMINATE = -1

    def __init__(
        self,
        target_room: int,
        menu_name: str = None,
        activation_text: str = None,
        visible: bool = True,
        reveal_after_use: list[str] = None,
        hide_after_use: bool = False,
        on_exit: list[events.Event] = None,
        *args,
        **kwargs,
    ):
        super().__init__(
            menu_name,
            activation_text or "",
            ExitAction.States,
            ExitAction.States.DEFAULT,
            InputType.SILENT,
            visible,
            reveal_after_use,
            hide_after_use,
            *args,
            **kwargs,
        )

        # Set instance variables
        self.target_room = target_room
        self.__on_exit: list[events.Event] = on_exit or []
        self._menu_name = menu_name

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def logic(_: any) -> None:
            cache.get_cache()["player_location"] = self.target_room
            room.room_manager.visit_room(self.room.id)  # Inform the room manager that this room has been "visited"
            self.set_state(self.States.TERMINATE)

    @property
    def menu_name(self) -> str:
        """
        Dynamically return a menu name that retrieves the room_name of the target Room
        """
        return self._menu_name or f"Move to {room.room_manager.get_name(self.target_room)}"

    @staticmethod
    @cache.cached([LoadableMixin.LOADER_KEY, "ExitAction", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        required_fields = [("target_room", int)]

        optional_fields = [
            ("menu_name", str),
            ("visible", bool),
            ("reveal_after_use", list),
            ("hide_after_use", bool),
            ("requirements", list),
            ("on_exit", list),
            ("tags", list),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)
        kwargs = LoadableFactory.collect_optional_fields(optional_fields, json)

        return ExitAction(json["target_room"], **kwargs)


class WrapperAction(Action):
    """Simply wrap and launch a state device. This Action is mostly designed to be used as a shortcut for debugging!"""

    class States(Enum):
        DEFAULT = 0
        TERMINATE = -1

    def __init__(self, menu_name: str, activation_text: str, wrap: StateDevice | list[StateDevice], *args, **kwargs):
        super().__init__(
            menu_name,
            activation_text,
            WrapperAction.States,
            WrapperAction.States.DEFAULT,
            InputType.SILENT,
            *args,
            **kwargs,
        )

        if not isinstance(wrap, StateDevice) and not isinstance(wrap, list):
            raise TypeError(f"Cannot wrap object of type {type(wrap)}! Must be a subclass of StateDevice!")

        self.wrapped_device = wrap

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def logic(_: any) -> None:
            if self.wrapped_device is None:
                raise TypeError("Cannot launch WrapperAction, wrapped_device is None!")

            if type(self.wrapped_device) is list:
                for device in self.wrapped_device:
                    game.add_state_device(device)

            elif isinstance(self.wrapped_device, StateDevice):
                game.add_state_device(self.wrapped_device)

            else:
                raise TypeError(f"Invalid type of wrapped object: {type(self.wrapped_device)}!")

            self.set_state(self.States.TERMINATE)

    @staticmethod
    @cache.cached([LoadableMixin.LOADER_KEY, "WrapperAction", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        """
        Required JSON fields:
        - menu_name: str
        - activation_text: str,
        - wrap: Event

        Optional JSON fields:
        - visible: bool
        - hide_after_use: bool
        - reveal_after_use: list[str]
        - tags: list[str]
        - requirements: list[Requirement]
        """

        required_fields = [("menu_name", str), ("activation_text", str), ("wrap", (dict, list))]

        optional_fields = [
            ("visible", bool),
            ("reveal_after_use", list),
            ("hide_after_use", bool),
            ("requirements", list),
            ("on_exit", list),
            ("tags", list),
        ]

        LoadableFactory.validate_fields(required_fields, json)
        kw = LoadableFactory.collect_optional_fields(optional_fields, json)

        if type(json["wrap"]) is dict:
            wrap = LoadableFactory.get(json["wrap"])
        elif type(json["wrap"]) is list:
            wrap = [LoadableFactory.get(j) for j in json["wrap"]]
        else:
            raise TypeError("Unknown type for field 'wrap'")

        return WrapperAction(json["menu_name"], json["activation_text"], wrap, **kw)
