"""
The foundational building block classes of TXEngine.

Every "activity" in TXEngine is encapsulated in a self-contained StateDevice
object, the vast majority of which are actually further sub-divided into states
within a FiniteStateDevice object.
"""

import copy
import enum
import inspect
import weakref
from abc import abstractmethod, ABC
from typing import Callable

from loguru import logger

import game
from game.structures import enums
from game.structures.enums import InputType
from game.structures.errors import StateDeviceInternalError
from game.structures.messages import Frame, ComponentFactory
from game.util.input_utils import is_valid_range, to_range, affirmative_range, affirmative_to_bool


class StateDevice(ABC):
    """
    An abstract class that defines an object that represents game logic.

    The StateDevice object is a loosely-formalized representation of internal
    state progression within the engine. It takes an input of a specific type
    and domain and increments its internal logic in response. The increment in
    internal logic in turn adjusts the "frame" output of the device, modifying
    the text shown to the end user.

    In general, one should avoid using a bare StateDevice and instead opt to use
    a FiniteStateDevice.
    """

    def __init__(self, input_type: InputType, input_range: dict[str, int] = None, name: str = None):
        self._input_type: InputType = input_type
        self._input_range: dict[str, int] = input_range or to_range()
        self.name: str = name or f"StateDevice::{self.__class__.__name__}"
        self._controller: any = None  # Only set by the GameStateController

    @property
    def input_type(self) -> InputType:
        """
        The input type currently expected by the state device.
        Returns: InputType of the state device

        """
        return self._input_type

    @input_type.setter
    def input_type(self, value: InputType) -> None:
        """
        Sets the InputType of the state device.
        Args:
            value: The InputType to set to.

        Returns: None

        """
        if not isinstance(value, InputType):
            raise TypeError(f"Cannot set input_type to object of type {type(value)}")

        self._input_type = value

    @property
    def controller(self) -> any:
        """
        Get a reference to the StateDeviceController that hosts the state device
        Returns: A StateDeviceController reference
        """

        # TODO: The controller can be accessed globally. Is this obsolete?
        return self._controller

    @controller.setter
    def controller(self, engine_in) -> None:
        """
        Weakrefs an instance of an engine and stores it.
        Args:
            engine_in: The engine to weakref

        Returns: None

        """
        self._controller = weakref.ref(engine_in)

    @property
    def domain_min(self) -> int | None:
        """
        The minimum value the StateDevice can accept

        Returns: None or an int representing the lowest acceptable value.

        """
        return self._input_range["min"]

    @domain_min.setter
    def domain_min(self, val: int | None) -> None:
        """
        Validate a value as being acceptable as a minimum value and set it.

        Args:
            val: The value to validate

        Returns: None
        """

        if is_valid_range(self.input_type, val, self.domain_max, self.domain_length):
            self._input_range["min"] = val
        else:
            raise ValueError(f"Tried to set lower limit of " f"{self.input_type} to value of type {type(val)}!")

    @property
    def domain_max(self) -> int | None:
        """
        An optional value that determines the maximum value of a submitted int.

        Returns: The maximum value allowed for the current InputType
        """
        return self._input_range["max"]

    @domain_max.setter
    def domain_max(self, val: int | None) -> None:
        if is_valid_range(self.input_type, self.domain_min, val, self.domain_length):
            self._input_range["max"] = val
        else:
            raise ValueError(f"Tried to set lower limit of " f"{self.input_type} to value of type {type(val)}!")

    @property
    def domain_length(self) -> int | None:
        """
        An optional value that determines the maximum length of a submitted str.
        """
        if "len" not in self._input_range:
            return None

        return self._input_range["len"]

    @domain_length.setter
    def domain_length(self, val: int | None) -> None:
        if is_valid_range(self.input_type, self.domain_min, self.domain_max, val):
            self._input_range["len"] = val
        else:
            raise ValueError(f"Tried to set lower limit of " f"{self.input_type} to value of type {type(val)}!")

    @property
    def input_domain(self) -> dict[str, any]:
        """
        A map that stores the domain of the allowed values for the StateDevice.
        """
        return self._input_range

    @input_domain.setter
    def input_domain(self, range_dict: dict[str : int | None]) -> None:
        if is_valid_range(self.input_type, range_dict["min"], range_dict["max"], range_dict["len"]):
            self._input_range = range_dict

        else:
            raise ValueError(
                f"""Invalid input domain values for type {self.input_type}:\n
                    min: {range_dict['min']}\n
                    max: {range_dict['max']}\n
                    length: {range_dict['max']}
                """
            )

    def reset(self) -> None:
        """
        Resets the FiniteStateDevice to some pre-determined state.

        Not every StateDevice needs a reset method, but its there and should be
        overridden should the need arise.
        """
        pass

    # TODO: Can _link or link be be standardized/parameterized? There shouldn't be two layers of undefined logic.
    def _link(self) -> dict[str, str]:
        """
        Internal link logic that is responsible for acquiring storage keys,
        creating the returned dict, and storing the storage keys internally.

        Intended to be overridden.
        """
        return {}

    def link(self) -> dict[str, str]:
        """
        Reserve a set number of keys in storage and map them to a specific use
        case within the StateDevice.

        Intended to be overriden.
        """
        return self._link()

    @property
    @abstractmethod
    def components(self) -> dict[str, any]:
        """
        The basic display components of the device
        """

    def validate_input(self, input_value) -> bool:
        """
        Compare the user's input against the allowed values to determine if it is valid.

        Args:
            input_value: The user's input

        Returns: True if the input value is valid, False otherwise
        """

        # SILENT and ANY input types don't care. Just return True.
        if self.input_type in [InputType.SILENT, InputType.ANY]:
            return True

        # Input must be str matching the set of strings in the array
        elif self.input_type == InputType.AFFIRMATIVE:
            if type(input_value) is str and str.lower(input_value) in affirmative_range:
                return True
            else:
                logger.warning(f"[{self}]: Failed to validate input! " f"{input_value} must be in {affirmative_range}")
                return False

        # Input must be an int that is below the maximum and above the minimum
        elif self.input_type == InputType.INT:
            try:
                true_input = int(input_value)

                if self.domain_min is not None and true_input < self.domain_min:
                    logger.warning(
                        f"[{self}]: Failed to validate input! " f"{true_input} must be >= {self._input_range['min']}"
                    )
                    return False

                if self.domain_max is not None and (true_input > self.domain_max):
                    logger.warning(
                        f"[{self}]: Failed to validate input! " f"{true_input} must be <= {self._input_range['max']}"
                    )
                    return False

                return True

            except (ValueError, TypeError):
                logger.warning(f"input_type.INT requires int not type: " f"{type(input_value)}!")
                return False

        # Input must be a str shorter than length
        elif self.input_type == InputType.STR:
            if type(input_value) is str:
                if self._input_range["len"] is not None:
                    if len(input_value) <= self._input_range["len"]:
                        return True

                    else:
                        return False

                else:
                    return True
            logger.warning(
                f"[{self}]: "
                f"Failed to validate input! {input_value} "
                f"is not a str of len <= {self._input_range['len']}"
            )
            return False
        else:
            raise ValueError(f"Unknown InputType: {self.input_type.name}!")

    @abstractmethod
    def logic(self, user_input: any) -> None:
        """
        The actual game logic. This must be overriden by subclasses.

        Args:
            user_input:

        Returns: None

        """

    def input(self, user_input: any) -> bool:
        """
        Submits the user's input to the state device. The state device advances
        its internal logic and modifies its output. If the input is not valid,
        it is rejected.

        Args:
            user_input: The value passed by the user

        Returns: True if the input is valid, False otherwise

        """
        if self.validate_input(user_input):
            # Intercept affirmative input values and transform them
            if self.input_type == enums.InputType.AFFIRMATIVE:
                self.logic(affirmative_to_bool(user_input))

            elif self.input_type == enums.InputType.INT:
                self.logic(int(user_input))
            else:  # Handle all other input values normally
                self.logic(user_input)
            return True

        return False

    # TODO: Does anything else define __frame__? If so, why is this not a mixin? If not, why do we need both to_frame and __frame__?
    def __frame__(self) -> Frame:
        """
        A method to convert a state device into a corresponding frame.

        Returns: The Frame-equivalent of a given state device

        """
        return Frame(
            components=self.components,
            input_type=self.input_type,
            input_range=self._input_range,
            frame_type=self.__class__.__name__,
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.__class__.__name__})"

    def to_frame(self) -> Frame:
        """
        A method to convert a state device into a corresponding frame.

        Returns: The Frame-equivalent of a given state device

        """
        return self.__frame__()


class FiniteStateDevice(StateDevice, ABC):
    """
    A subclass of StateDevice that adds support for explicit state ordering and
    transitions.
    """

    state_data_dict = {
        "input_type": enums.InputType.ANY,
        "min": None,
        "max": None,
        "len": None,
        "logic": None,
        "content": None,
    }

    class States(enum.Enum):
        """
        The default inner-class for States.

        Proper convention for designing FiniteStateDevices requires:
        - State flow starts with DEFAULT and ends with TERMINATE
        - No state calls state_device_controller.set_dead() except for TERMINATE
        - TERMINATE must call game.state_device_controller.set_dead()
        - TERMINATE == -1, DEFAULT == 0
        - No two states have the same value
        - States are assigned INT values
        """

        DEFAULT = 0
        TERMINATE = -1

    def __init__(self, default_input_type: InputType, states: type[enum.Enum], default_state=States.DEFAULT):
        super().__init__(default_input_type)

        self.states: type[enum.Enum] = states
        self.current_state = self.default_state = default_state
        self.state_data: dict[states, dict] = {k.value: copy.deepcopy(self.state_data_dict) for k in self.states}
        self.state_history: list[states] = [self.current_state]
        self.set_defaults()

    def set_state(self, next_state) -> None:
        if next_state.value not in self.state_data:
            raise StateDeviceInternalError(f"Unknown state {next_state}!")

        self.current_state = next_state
        self.input_type = self.state_data[next_state.value]["input_type"]

        # Assign min
        if callable(self.state_data[next_state.value]["min"]):
            self.domain_min = self.state_data[next_state.value]["min"]()
        else:
            self.domain_min = self.state_data[next_state.value]["min"]

        # Assign max
        if callable(self.state_data[next_state.value]["max"]):
            self.domain_max = self.state_data[next_state.value]["max"]()
        else:
            self.domain_max = self.state_data[next_state.value]["max"]

        # Assign length
        if callable(self.state_data[next_state.value]["len"]):
            self.domain_length = self.state_data[next_state.value]["len"]()
        else:
            self.domain_length = self.state_data[next_state.value]["len"]

        # Append history for debugging purposes
        self.state_history.append(next_state)

    # Custom Decorators
    def state_logic(
        self,
        state,
        input_type: enums.InputType,
        input_min: int | Callable = None,
        input_max: int | Callable = None,
        input_len: int = None,
        override: bool = False,
    ):
        """
        A decorator factory that registers a function as a logic provider within
        an instance of FiniteStateDevice and stores auxiliary state information
        such as input type and input range.

        Args:
            state: The state to map 'func' to
            input_type: The input type for this state
            input_min:
                The input range's min for this state. This may be an int or
                a callable that returns an int.
            input_max:
                The input range's max for this state. This may be an int or a
                callable that returns an int.
            input_len:
                The input range's length for this state. This must be an int.
            override: If True, ignore collision errors

        Returns:
            callable: A decorator that registers the wrapped function and passed
            input information to 'instance'

        """

        if state not in self.state_data and state.value not in self.state_data:
            raise StateDeviceInternalError(f"Unknown state {state}:{state.value}!")

        if not override and self.state_data[state.value]["logic"]:
            raise StateDeviceInternalError(
                f"State.logic collision! {state} already has a logic function " f"registered."
            )

        if input_min is not None and (not callable(input_min) and type(input_min) is not int):
            raise StateDeviceInternalError(
                f"input_min must be an int or a callable! Got {type(input_min)}" f" instead."
            )

        if input_max is not None and (not callable(input_max) and type(input_max) is not int):
            raise StateDeviceInternalError(
                f"input_max must be an int or a callable! Got {type(input_max)}" f" instead."
            )

        if input_len is not None and (not callable(input_len) and type(input_len) is not int):
            raise StateDeviceInternalError(
                f"input_len must be an int or a callable! Got {type(input_len)}" f" instead."
            )

        def decorate(fn):
            """
            Register to instance and then return the function untouched.
            """

            spec = inspect.getfullargspec(fn)
            if len(spec.args) != 1:
                raise ValueError(
                    f"""Error registering logic provider for state {state}.
                    State logic functions must accept only a single positional 
                    argument, not {len(spec.args)}!"""
                )

            self.state_data[state.value]["input_type"] = input_type
            self.state_data[state.value]["min"] = input_min
            self.state_data[state.value]["max"] = input_max
            self.state_data[state.value]["len"] = input_len
            self.state_data[state.value]["logic"] = fn

            return fn

        return decorate

    def state_content(self, state, override: bool = False):
        """
        A decorator factory that returns a factory that registers the wrapped
        function as the content provider for state 'state'.

        Args:
            instance: An instance of the FiniteStateDevice to modify
            state: The state to register the content function to
            override: If True, ignore collisions

        Returns:
            A decorator function that registers the wrapped function as a
            content provider for a given state
        """

        if state.value not in self.state_data:
            raise StateDeviceInternalError(f"Unknown state {state}!")
        if self.state_data[state.value]["content"] and not override:
            raise StateDeviceInternalError(
                f"State.content collision! {state} already has a content " f"function registered."
            )

        # Inner decorator that receives the function
        def decorate(fn):
            """
            A simple decorator that registers the wrapped function to the passed
            instance.
            """
            self.state_data[state.value]["content"] = fn
            return fn

        return decorate

    def _update_dynamic_input_domains(self) -> None:
        """
        When the user transitions to a state, check if the min and/or max are
        defined dynamically. If so, force the value to refresh.
        """

        if callable(self.state_data[self.current_state.value]["max"]):
            self.domain_max = self.state_data[self.current_state.value]["max"]()

        if callable(self.state_data[self.current_state.value]["min"]):
            self.domain_min = self.state_data[self.current_state.value]["min"]()

    def logic(self, user_input: any) -> None:
        self._update_dynamic_input_domains()

        # Check for bad state data
        if self.current_state.value not in self.state_data:
            raise ValueError(f"State {self.current_state} " f"has not been registered with {self.name}!")

        if (
            "logic" not in self.state_data[self.current_state.value]
            or not self.state_data[self.current_state.value]["logic"]
        ):
            raise StateDeviceInternalError(
                f"No logical provider has been registered for state " f"{self.current_state}!", {KeyError: ""}
            )
        self.state_data[self.current_state.value]["logic"](user_input)

    @property
    def components(self) -> dict[str, any]:
        self._update_dynamic_input_domains()

        # Check for bad state data
        if self.current_state.value not in self.state_data:
            raise ValueError(f"State {self.current_state} " f"has not been registered with {self.name}!")

        # If the state is silent, simply return an empty component dict.
        # This circumvents checks for silent states
        if self.state_data[self.current_state.value]["input_type"] == InputType.SILENT:
            return ComponentFactory.get()

        if (
            "content" not in self.state_data[self.current_state.value]
            or not self.state_data[self.current_state.value]["content"]
        ):
            raise KeyError(
                f"No content provider has been registered for state " f"{self.current_state} in device {self.name}!"
            )

        return self.state_data[self.current_state.value]["content"]()

    def reset(self) -> None:
        self.set_state(self.default_state)

    def set_defaults(self) -> None:
        @self.state_logic(self.States.TERMINATE, InputType.SILENT)
        def _logic(_: any):
            game.state_device_controller.set_dead()

        @self.state_content(self.States.TERMINATE)
        def _content():
            return ComponentFactory.get()

    @staticmethod
    def user_branching_state(
        instance: "FiniteStateDevice",
        state,
        branch_map: dict[str, any],
        prompt: str = "Choose an option",
        back_out_state=None,
        cache_choice_in_attr: str = None,
    ):
        """
        Build a simple branching state. Uses the state map defined in branch_map
        to define a list of options for the user to chose from, then updates the
        FiniteStateDevice's current state to the state mapped to the user's '
        choice.

        Args:
            instance:
                The instance of FiniteStateDevice in which to create the state.
            state:
                The state that the branching-state should be created in
            branch_map:
                A map of strings (Options to show in the choice-selection list)
                to states.
            prompt:
                The prompt that is shown to the user when asked to choose
            back_out_state:
                The state that should be mapped to a choice of -1.
                If None, there is no -1 choice.
            cache_choice_in_attr:
                If not set to none, attempt to store the choice in str form
                inside the given attr
        """

        if instance is None:
            raise TypeError("Expected type of argument: instance to be FiniteStateDevice. " "Got None instead.")

        if state.value not in instance.state_data:
            raise ValueError(f"Unknown state: {state} in FiniteStateDevice: {instance.name}")

        if len(branch_map.keys()) < 2:
            raise ValueError("Branch map must be of size >= 2!")

        if cache_choice_in_attr is not None:
            if type(cache_choice_in_attr) is not str:
                raise TypeError(
                    f"cache_choice_in_attr must be of type str or None! " f"Invalid type: {type(cache_choice_in_attr)}"
                )
            if not hasattr(instance, cache_choice_in_attr):
                raise ValueError(f"instance: {instance.name} has to attr: " f"{cache_choice_in_attr}!")

        @instance.state_logic(
            state,
            input_type=InputType.INT,
            input_min=-1 if back_out_state is not None else 0,
            input_max=len(branch_map.keys()) - 1,
        )
        def _logic(user_input: int) -> None:
            # If back_out_state is enabled and the user entered -1, set the
            # state to the defined back-out state
            if back_out_state is not None and user_input == -1:
                instance.set_state(back_out_state)

                # Terminate the function to prevent fall-through state setting.
                return

            # Convert the user's choice from an index to a str
            choice_as_str = list(branch_map.keys())[user_input]

            # If cache_choice_in_attr is enabled, store the user's choice
            # (in str form) in that attr.
            if cache_choice_in_attr:
                setattr(instance, cache_choice_in_attr, choice_as_str)

            # Using the converted choice, set the next state via the branch_map
            instance.set_state(branch_map[choice_as_str])

        @instance.state_content(state)
        def _content():
            return ComponentFactory.get([prompt], [[s] for s in branch_map.keys()])
