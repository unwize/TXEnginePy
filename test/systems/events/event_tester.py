from typing import Callable

from loguru import logger

import game
from game.systems.event import Event


class EventTester:
    def __init__(self, event: Event, inputs: list[str | int], tests: list[Callable], show_frames: bool = False):
        self._event: Event = event
        self._inputs: list[str | int] = inputs
        self._tests: list[Callable] = tests
        self._show_frames: bool = show_frames

    def run_tests(self):
        """
        Simulate the user submitting inputs to the state device by placing it on the state device stack.

        After the inputs are exhausted, for each test in tests assert test(event) == True.
        Note that since this tester relies on an external instance of the state device controller, multiple tests
        cannot be run simultaneously on a single instance of TXEnginePy
        """

        # TODO: Use an internal copy of the state device controller
        game.state_device_controller.state_device_stack.clear()
        game.add_state_device(self._event)
        game.state_device_controller.get_current_frame()

        previous_state = None

        for user_input in self._inputs:
            logger.debug(f"Running input: {user_input}")
            assert game.state_device_controller.state_device_stack[0][0].current_state.value != previous_state
            previous_state = game.state_device_controller.state_device_stack[0][0].current_state.value
            logger.debug(f"Current_state: {previous_state}")
            if self._show_frames:
                logger.debug(self._event.to_frame())
            game.state_device_controller.deliver_input(user_input)

        for test in self._tests:
            assert test(game.state_device_controller.state_device_stack[0][0]) is True
