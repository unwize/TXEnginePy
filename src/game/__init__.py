from .engine import Engine
from .game_state_controller import GameStateController

engine: Engine = None
if engine is None:
    engine = Engine()

state_device_controller: GameStateController = GameStateController()


def add_state_device(device) -> None:
    """
    Add a state device to the global instance state device controller.

    Args:
        device: The StateDevice object to add to the top of the stack

    Returns: None
    """

    if state_device_controller:
        state_device_controller.add_state_device(device)

    else:
        raise RuntimeError("Cannot add a StateDevice to the stack! Game state controller has not been initialized!")
