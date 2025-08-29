"""
GameStateController manages the execution of StateDevice object across the
entirety of TXEngine.

StateDevices are executed in LIFO order. Adding a StateDevice to the stack of
devices mid-state does not interrupt the state (states within FiniteStateDevices
are atomic).
"""

import asyncio
import dataclasses

from loguru import logger

import game.cache as cache
import game.structures.messages as messages
import game.structures.state_device as sd
import game.systems.room as room
from game.structures import enums


@dataclasses.dataclass
class StackState:
    """
    A simple struct to store the properties of the top sd.StateDevice. Only the
    state of the top device matters--extracting these properties and storing
    them independently of the sd.StateDevice class saves on time and memory.
    """

    dead: bool = False
    error: bool = False
    recoverable: bool | None = None


class GameStateController:
    """
    An object that manages game states.

    GameStateController is singleton class that transforms sd.StateDevices into
    Frames and delivering user inputs to the correct sd.StateDevices.
    """

    def __init__(self):
        self.state_device_stack: list[tuple[sd.StateDevice, StackState]] = []
        self.add_state_device(room.room_manager.get_room(cache.get_cache()["player_location"]))
        self.input_lock: asyncio.Lock = asyncio.Lock()

    # Built-ins

    # Private functions

    def _burn_dead_devices(self) -> None:
        """
        Pops the state device stack until a live state device is on top
        """
        while len(self.state_device_stack) > 0 and self.state_device_stack[-1][1].dead:
            self._pop_state_device()

        if len(self.state_device_stack) < 1:
            self.add_state_device(room.room_manager.get_room(cache.get_cache()["player_location"]))

    def _get_state_device(self, idx: int = -1) -> sd.StateDevice:
        """
        Return the state device at the given index within the stack. By default,
        this returns the device on the top of the stack.

        Args:
            idx: The index of the sd.StateDevice to return. By default, this is
            '-1' (the top element)

        Returns: The requested sd.StateDevice

        """
        if len(self.state_device_stack) < 1:
            raise ValueError("No sd.StateDevice loaded!")

        self._burn_dead_devices()

        return self.state_device_stack[idx][0]

    def _pop_state_device(self) -> sd.StateDevice:
        """
        Remove the top sd.StateDevice from the state_device_stack and return it.

        Returns: The top sd.StateDevice on the state_device_stack

        """
        logger.info(f"Popping state device: {str(self.state_device_stack[-1])}")
        return self.state_device_stack.pop()[0]

    def _advance_if_silent(self):
        # There has got to be a better way to do this.
        while self._get_state_device().input_type == enums.InputType.SILENT:
            logger.info(f"Detected silent state in device: " f"{self._get_state_device()}. Skipping...")
            if hasattr(self._get_state_device(), "current_state"):
                logger.info(f"State: {self._get_state_device().current_state}")

            if not self._get_state_device().input(""):
                logger.error("Input rejected while in a Silent state!")
                logger.debug(repr(self._get_state_device()))
                logger.debug(self._get_state_device().to_frame())

                if hasattr(self._get_state_device(), "current_state"):
                    logger.info(f"State: {self._get_state_device().current_state}")
                    logger.debug(self._get_state_device().state_data)
                raise RuntimeError("Input rejected while in Silent State!")

    # Public functions
    def deliver_input(self, user_input: any) -> bool:
        """
        Deliver the user's input to the top sd.StateDevice. Returns True if the
        device accepts the input.

        Args:
            user_input: Input that the user delivers to the service via the API

        Returns: True if the input is accepted, False otherwise.
        """

        if self._get_state_device().validate_input(user_input):
            self._get_state_device().input(user_input)
            return True

        return False

    async def deliver_input_async(self, user_input: any) -> bool:
        """
        Deliver the user's input to the top sd.StateDevice. Returns True if the
        device accepts the input.

        Args:
            user_input: Input that the user delivers to the service via the API

        Returns: True if the input is accepted, False otherwise.
        """
        async with self.input_lock:
            if self._get_state_device().validate_input(user_input):
                self._get_state_device().input(user_input)
                return True

            return False

    def add_state_device(self, device: sd.StateDevice) -> None:
        """
        Appends a sd.StateDevice to the top of the state_device_stack

        Args:
            device: The device to append

        Returns: None

        """
        if not isinstance(device, sd.StateDevice):
            raise TypeError("device must be of type sd.StateDevice!")

        logger.info(f"Adding state device: {str(device)}")
        device.reset()
        self.state_device_stack.append((device, StackState()))

    def set_dead(self, val: bool = True) -> None:
        """
        A public function that allows state devices to mark themselves as
        terminated at a global scope. This is the proper way for a
        sd.StateDevice to inform the game engine that it should be removed from
        the stack

        Args:
            val: If the sd.StateDevice is dead, True. Otherwise, False.

        Returns: None
        """
        logger.info(f"Marking {self._get_state_device()} as dead...")
        self.state_device_stack[-1][1].dead = val

    def get_current_frame(self) -> messages.Frame:
        """
        Convert the top sd.StateDevice into a Frame and return it.

        Returns: The Frame generated by the top sd.StateDevice in the
        state_device_stack

        """

        # Intercept the request for a frame to detect a SILENT state. If the
        # state is SILENT, advance the state device until it is no longer
        # silent, or it is dead.
        self._advance_if_silent()

        return self._get_state_device().to_frame()
