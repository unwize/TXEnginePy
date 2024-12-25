import random

import pytest

from game.structures.enums import InputType
from game.structures.state_device import StateDevice
from game.structures.messages import ComponentFactory
from game.util import input_utils
from game.util.input_utils import to_range


class MockDevice(StateDevice):
    """
    A trivial subclass of StateDevice designed to allow for easy testing of commonly-used StateDevice functions.
    """

    def __init__(self, input_type: InputType):
        super().__init__(input_type)

        self.counter: int = 0

    @property
    def components(self) -> dict[str, any]:
        return ComponentFactory.get([str(self.counter)])

    def _logic(self, user_input: any) -> None:
        self.counter = self.counter + 1


def test_init():
    """
    Test that a basic subclass of StateDevice is correctly initialized
    """
    md = MockDevice(InputType.ANY)
    assert isinstance(md, StateDevice)
    assert md.name == "StateDevice::MockDevice"
    assert type(md._input_range) is dict
    assert "max" in md._input_range
    assert "min" in md._input_range
    assert "len" in md._input_range
    assert md.input_type == InputType.ANY
    assert not md._controller


def test_components_trivial():
    """
    Test that StateDevice::components returns the correct value in a trivial case
    """
    md = MockDevice(InputType.ANY)
    res = md.components
    assert res
    assert type(res) is dict
    assert "content" in res
    assert type(res["content"]) is list
    assert len(res["content"]) == 1
    assert res["content"][0] == "0"


domain_min_set_cases_good = [0, -1, 2222222, None]


@pytest.mark.parametrize("value", domain_min_set_cases_good)
def test_domain_min_set_good(value):
    """
    Test that a given valid value is correctly set using StateDevice::min
    property.

    Note that correctness is dependent on input_utils.is_valid_range
    """
    md = MockDevice(InputType.INT)
    md.domain_min = value

    assert md.input_domain["min"] == value


domain_min_set_cases_bad = [2.2, lambda: pow(2, 2), "5"]


@pytest.mark.parametrize("value", domain_min_set_cases_bad)
def test_domain_min_set_bad(value):
    """
    Test that StateDevice::domain_min setter rejects badly-typed values

    Note that correctness is dependent on input_utils.is_valid_range
    """
    with pytest.raises(ValueError):
        md = MockDevice(InputType.INT)
        md.domain_min = value


domain_max_set_cases_good = [0, -1, 2222222, None]


@pytest.mark.parametrize("value", domain_max_set_cases_good)
def test_domain_max_set_good(value):
    """
    Test that a given valid value is correctly set using StateDevice::domain_max property.

    Note that correctness is dependent on input_utils.is_valid_range
    """
    md = MockDevice(InputType.INT)
    md.domain_max = value

    assert md.input_domain["max"] == value


domain_max_set_cases_bad = [2.2, lambda: pow(2, 2), "5"]


@pytest.mark.parametrize("value", domain_max_set_cases_bad)
def test_domain_max_set_bad(value):
    """
    Test that StateDevice::domain_max setter rejects badly-typed values

    Note that correctness is dependent on input_utils.is_valid_range
    """
    with pytest.raises(ValueError):
        md = MockDevice(InputType.INT)
        md.domain_max = value


domain_len_set_cases_good = [1, 2222222, None]


@pytest.mark.parametrize("value", domain_len_set_cases_good)
def test_domain_len_set_good(value):
    """
    Test that a given valid value is correctly set using StateDevice::domain_length property.

    Note that correctness is dependent on input_utils.is_valid_range
    """
    md = MockDevice(InputType.STR)
    md.domain_length = value

    assert md.input_domain["len"] == value


domain_len_set_cases_bad = [2.2, lambda: pow(2, 2), "5", 0, -1]


@pytest.mark.parametrize("value", domain_len_set_cases_bad)
def test_domain_len_set_bad(value):
    """
    Test that StateDevice::domain_length setter rejects badly-typed values

    Note that correctness is dependent on input_utils.is_valid_range
    """
    with pytest.raises(ValueError):
        md = MockDevice(InputType.STR)
        md.domain_length = value


setter_mixed_cases_good = [
    # Trivial
    [InputType.INT, None, None, None],
    [InputType.STR, None, None, None],
    [InputType.ANY, None, None, None],
    [InputType.AFFIRMATIVE, None, None, None],
    [InputType.SILENT, None, None, None],
    # Int
    [InputType.INT, 0, None, None],
    [InputType.INT, -1, None, None],
    [InputType.INT, 1, None, None],
    [InputType.INT, 1000, None, None],
    [InputType.INT, 0, 0, None],
    [InputType.INT, -1, 0, None],
    [InputType.INT, -1, -1, None],
    [InputType.INT, 0, 1, None],
    [InputType.INT, -1, 1, None],
    [InputType.INT, -1, 13, None],
    [InputType.INT, -100, -20, None],
    # Str
    [InputType.STR, None, None, 1],
    [InputType.STR, None, None, 10],
]


@pytest.mark.parametrize("input_type, i_min, i_max, i_len", setter_mixed_cases_good)
def test_domain_setters_mixed(input_type: InputType, i_min: int | None, i_max: int | None, i_len: int | None):
    md = MockDevice(input_type)
    md.domain_min = i_min
    md.domain_max = i_max
    md.domain_length = i_len


@pytest.mark.parametrize("input_type, i_min, i_max, i_len", setter_mixed_cases_good)
def test_input_domain_property_setter(input_type: InputType, i_min: int | None, i_max: int | None, i_len: int | None):
    md = MockDevice(input_type)
    md.input_domain = to_range(i_min, i_max, i_len)


setter_mixed_cases_bad = [
    # INT
    [InputType.INT, 1, -1, None],  # Inverted min/max
    [InputType.INT, 6, 3, None],
    [InputType.INT, 3, 6, 5],  # Extraneous length
    [InputType.INT, None, None, 1],
    [InputType.INT, "3", 6, None],  # Bad types
    [InputType.INT, 3, "6", None],
    [InputType.INT, 3.2, 6, None],
    [InputType.INT, 3, 6.2, None],
    [InputType.INT, 3, 6, 1.1],
    [InputType.INT, 3, 6, "Definitely a number"],
    [InputType.INT, lambda: pow(2, 2), 6, None],
    [InputType.INT, -1, lambda: pow(2, 2), None],
    # STR
    [InputType.STR, None, None, 0],  # Bad length value
    [InputType.STR, None, None, -1],
    [InputType.STR, 3, 6, 0],
    [InputType.STR, 3, 6, -1],
    [InputType.STR, 3, 6, None],  # Extraneous values
    [InputType.STR, 3, 6, 1],
    [InputType.STR, True, 6, None],
    [InputType.STR, 3, False, None],
    [InputType.STR, None, False, 4],
]


@pytest.mark.parametrize("input_type, i_min, i_max, i_len", setter_mixed_cases_bad)
def test_domain_setters_mixed_bad(input_type, i_min, i_max, i_len):
    with pytest.raises(ValueError):
        md = MockDevice(input_type)
        md.domain_min = i_min
        md.domain_max = i_max
        md.domain_length = i_len


@pytest.mark.parametrize("input_type, i_min, i_max, i_len", setter_mixed_cases_bad)
def test_input_domain_property_setter_bad(input_type, i_min, i_max, i_len):
    with pytest.raises(ValueError):
        md = MockDevice(input_type)
        md.input_domain = to_range(i_min, i_max, i_len)


def test_input_any():
    """
    Test that StateDevice::input() correctly handles an input when
    state_device.input_type == InputType.ANY

    A counter must be tracked, so parameterization doesn't work on this test.
    """
    md = MockDevice(InputType.ANY)

    various_inputs = ["", " ", None, 1, True]

    assert md.counter == 0

    for idx, val in enumerate(various_inputs):
        assert md.input(val)
        assert md.counter == idx + 1


test_input_int_cases_good = [
    [0, 0, 0],  # Trivial
    [-1, 0, 0],  # Negative min, zero payload
    [-1, 0, -1],  # Negative min, inclusive payload
    [None, None, -1],  # Unbound, negative payload
    [None, None, 0],  # Unbound, zero payload
    [None, None, 1],  # Unbound, positive payload
    [None, None, random.Random().randint(-100000, 999999)],  # Unbound, random payload
    [None, 1, -1],  # Sole max, negative payload
    [None, 1, 1],  # Sole max, positive payload inclusive
    [None, 1, 0],  # Sole max, zero payload
    [1, None, 1],  # Sole min, inclusive payload
    [1, None, 2],  # Sole min, positive payload
]


@pytest.mark.parametrize("i_min, i_max, payload", test_input_int_cases_good)
def test_input_int_good(i_min, i_max, payload):
    """
    Test that StateDevice::input() correctly accepts valid inputs for InputType.INT
    """
    md = MockDevice(InputType.INT)
    md.domain_min = i_min
    md.domain_max = i_max
    assert md.input(payload)
    assert md.counter == 1


test_input_int_cases_bad = [
    [None, None, None],  # Bad payload type, None
    [1, None, None],
    [1, 1, None],
    [None, 1, None],
    [None, None, lambda: pow(2, 2)],  # Bad typed
    [-1, 0, 1],  # Out of bounds, large
    [None, 2, 3],  # Out of bounds, large
    [-1, None, -3],  # Out of bounds, small
    [1, 4, 0],  # Out of bounds, small
]


@pytest.mark.parametrize("i_min, i_max, payload", test_input_int_cases_bad)
def test_input_int_bad(i_min, i_max, payload):
    """Test that StateDevice::input correctly rejects invalid input payloads"""
    md = MockDevice(InputType.INT)
    md.domain_min = i_min
    md.domain_max = i_max
    assert not md.input(payload)
    assert md.counter == 0


test_input_affirmative_cases_good = input_utils.affirmative_range


@pytest.mark.parametrize("payload", test_input_affirmative_cases_good)
def test_input_affirmative_good(payload: str):
    """Test that StateDevice::input correctly accepts and transforms valid input payloads when InputType.AFFIRMATIVE"""
    md = MockDevice(InputType.AFFIRMATIVE)
    assert md.input(payload)
    assert md.counter == 1
    assert md.input(payload.upper())
    assert md.counter == 2


test_input_affirmative_cases_bad = ["nah", "sure", 0, 1, None, True, False, "g", "G", "l", "K"]


@pytest.mark.parametrize("payload", test_input_affirmative_cases_bad)
def test_input_affirmative_bad(payload):
    """Test that StateDevice::input correctly reject invalid input payloads when InputType.AFFIRMATIVE"""
    md = MockDevice(InputType.AFFIRMATIVE)
    assert not md.input(payload)
    assert md.counter == 0


def test_frame():
    """Tests whether a StateDevice correctly converts itself to a Frame object"""
