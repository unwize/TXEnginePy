from enum import Enum

from game.structures.enums import InputType
from game.structures.messages import ComponentFactory
from game.structures.state_device import FiniteStateDevice

import pytest


class MockFiniteStateDevice(FiniteStateDevice):
    class States(Enum):
        DEFAULT = 0
        A = 1
        B = 2
        C = 3
        TERMINATE = -1

    def __init__(self):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self.counter: int = 0

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self.set_state(self.States.A)
            self.counter += 1

        @FiniteStateDevice.state_content(self, self.States.DEFAULT)
        def _content() -> dict:
            return ComponentFactory.get()

        @FiniteStateDevice.state_logic(self, self.States.A, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.B)
            self.counter += 1

        @FiniteStateDevice.state_content(self, self.States.A)
        def _content() -> dict:
            return ComponentFactory.get()

        @FiniteStateDevice.state_logic(self, self.States.B, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.C)
            self.counter += 1

        @FiniteStateDevice.state_content(self, self.States.B)
        def _content() -> dict:
            return ComponentFactory.get()

        @FiniteStateDevice.state_logic(self, self.States.C, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)
            self.counter += 1

        @FiniteStateDevice.state_content(self, self.States.C)
        def _content() -> dict:
            return ComponentFactory.get()

        @FiniteStateDevice.state_logic(self, self.States.TERMINATE, InputType.ANY, override=True)
        def _logic(_: any) -> None:
            self.counter += 1


def test_init_trivial():
    """Test that a trivial subclass of FiniteStateDevice initializes without error"""
    md = MockFiniteStateDevice()
    assert md.counter == 0  # No logic is run on init
    assert md.states is not None  # State enums are set correctly
    assert md.states == md.States  # State enums are set correctly
    assert md.current_state == md.default_state
    assert len(md.state_data) == len([e.value for e in md.states])  # State data created


def test_init_state_history():
    """Verify that FiniteStateDevice::init correctly initializes state_history"""
    md = MockFiniteStateDevice()
    assert md.state_history is not None
    assert len(md.state_history) == 1


@pytest.mark.parametrize("state", MockFiniteStateDevice.States)
def test_init_state_data(state):
    """Verify that the state data of each state in a FiniteStateDevice are correctly initialized"""
    md = MockFiniteStateDevice()
    dd = md.state_data[state.value]

    # The state has a correct copy of
    assert len(dd) == len(md.state_data_dict)

    # No domain values are set
    assert dd["min"] is None
    assert dd["max"] is None
    assert dd["len"] is None

    # Logic provider is set
    assert dd["logic"] is not None
    assert callable(dd["logic"])

    # Content provider is set
    assert dd["content"] is not None
    assert callable(dd["content"])


state_logic_decorator_cases_good = [
    [MockFiniteStateDevice.States.A, InputType.ANY, None, None, None, ""],  # ANY Trivial
    [MockFiniteStateDevice.States.A, InputType.SILENT, None, None, None, ""],  # SILENT Trivial
    [MockFiniteStateDevice.States.A, InputType.AFFIRMATIVE, None, None, None, "yes"],  # AFFIRMATIVE Trivial
    [MockFiniteStateDevice.States.A, InputType.INT, None, None, None, 16],  # ANY Trivial
    [MockFiniteStateDevice.States.A, InputType.INT, 0, None, None, 1],  # INT lonely min
    [MockFiniteStateDevice.States.A, InputType.INT, 0, 1, None, 1],  # INT ranged
    [MockFiniteStateDevice.States.A, InputType.INT, None, 1, None, -1],  # INT lonely max
    [MockFiniteStateDevice.States.A, InputType.INT, lambda: pow(-1, 2), None, None, 1],  # INT lonely callable min
    [MockFiniteStateDevice.States.A, InputType.INT, lambda: pow(-1, 2), lambda: pow(2, 2), None, 4],  # lambdas
    [MockFiniteStateDevice.States.A, InputType.ANY, None, lambda: pow(2, 3), None, 8],  # INT lonely callable max
    [MockFiniteStateDevice.States.A, InputType.STR, None, None, None, "A String"],  # STR Trivial
    [MockFiniteStateDevice.States.A, InputType.STR, None, None, 1, "f"],  # Constant len
    [MockFiniteStateDevice.States.A, InputType.STR, None, None, lambda: pow(2, 4), "AStringWithLen16"],
]


@pytest.mark.parametrize("state, input_type, i_min, i_max, i_len, payload", state_logic_decorator_cases_good)
def test_state_logic_decorator_integration(state, input_type, i_min, i_max, i_len, payload):
    """An integration test that validates the full chain of state parameter assignment down to input handling.

    - Tests that the state_logic decorator correctly assigns the logic operator to the state
    - Tests that FiniteStateDevice::set_state correctly executes the state transition
    """

    md = MockFiniteStateDevice()

    @FiniteStateDevice.state_logic(md, state, input_type, i_min, i_max, i_len, True)
    def _logic(_: any) -> None:
        md.counter += 1

    md.set_state(state)  # State transition
    assert md.current_state == state  # Assess state

    # Verify input domain has changed
    assert md.input_type == md.state_data[state.value]["input_type"]
    assert (
        md.domain_min == md.state_data[state.value]["min"]
        if not callable(md.state_data[state.value]["min"])
        else md.state_data[state.value]["min"]()
    )
    assert (
        md.domain_max == md.state_data[state.value]["max"]
        if not callable(md.state_data[state.value]["max"])
        else md.state_data[state.value]["max"]()
    )
    assert (
        md.domain_length == md.state_data[state.value]["len"]
        if not callable(md.state_data[state.value]["len"])
        else md.state_data[state.value]["len"]()
    ), f"i_len:{md.domain_length}"

    # Assign a valid input
    assert md.input(payload)  # Verify accepted
    assert md.counter == 1  # Verify logic was executed


# Generic branching FiniteStateDevice used for branching state tests
class MockBranchingStateDevice(FiniteStateDevice):
    class States(Enum):
        DEFAULT = 0
        A = 1
        B = 2
        C = 3
        TERMINATE = -1

    state_branch = {
        "Go to B": States.B,
        "Go to C": States.C,
    }

    def __init__(self):
        super().__init__(InputType.SILENT, self.States)

        @FiniteStateDevice.state_logic(self, self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any):
            self.set_state(self.States.A)

        @FiniteStateDevice.state_content(self, self.States.DEFAULT)
        def _content():
            return ComponentFactory.get()

        FiniteStateDevice.user_branching_state(self, self.States.A, self.state_branch)

        @FiniteStateDevice.state_logic(self, self.States.B, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.C)

        @FiniteStateDevice.state_content(self, self.States.B)
        def _content() -> dict:
            return ComponentFactory.get()

        @FiniteStateDevice.state_logic(self, self.States.C, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.TERMINATE)

        @FiniteStateDevice.state_content(self, self.States.C)
        def _content() -> dict:
            return ComponentFactory.get()


def test_user_branching_state_trivial():
    # Initialize FSD with a user_branching_state
    md = MockBranchingStateDevice()

    # Check that the code for setting the state was run
    dd = md.state_data[MockBranchingStateDevice.States.A.value]
    assert len(dd) == len(md.state_data_dict)

    # domain values are set
    assert dd["min"] == 0
    assert dd["max"] == 1
    assert dd["len"] is None

    # Logic provider is set
    assert dd["logic"] is not None
    assert callable(dd["logic"])

    # Content provider is set
    assert dd["content"] is not None
    assert callable(dd["content"])

    for opt in MockBranchingStateDevice.state_branch:
        assert [opt] in dd["content"]()["options"]


def test_user_branching_state_behavior():
    md = MockBranchingStateDevice()

    assert md.current_state.value == md.States.DEFAULT.value
    md.input(None)
    assert md.current_state.value == md.States.A.value
    assert md.input_type == InputType.INT
    md.input(0)
    assert md.current_state.value == md.States.B.value

    md = MockBranchingStateDevice()
    md.input(None)
    md.input(1)
    assert md.current_state.value == md.States.C.value
