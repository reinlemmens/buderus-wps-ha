import pytest

from buderus_wps.program_switching import (
    ProgramSwitchConfig,
    ProgramSwitchingController,
)


class InMemoryIO:
    """Simple parameter store for testing."""

    def __init__(self, initial=None):
        self.values = dict(initial or {})
        self.writes = []

    def read(self, parameter: str) -> int:
        return self.values.get(parameter)

    def write(self, parameter: str, value: int) -> None:
        self.values[parameter] = value
        self.writes.append((parameter, value))


def test_enable_disable_dhw_switches_program_mode():
    io = InMemoryIO({"DHW_PROGRAM_MODE": 1})
    controller = ProgramSwitchingController(io)

    controller.enable_dhw()
    assert io.values["DHW_PROGRAM_MODE"] == 2
    assert controller.is_dhw_enabled() is True

    controller.disable_dhw()
    assert io.values["DHW_PROGRAM_MODE"] == 1
    assert controller.is_dhw_enabled() is False


def test_buffer_switching_independent_from_dhw():
    io = InMemoryIO({"DHW_PROGRAM_MODE": 1, "ROOM_PROGRAM_MODE": 1})
    controller = ProgramSwitchingController(io)

    controller.enable_buffer_heating()
    state = controller.get_state()

    assert io.values["ROOM_PROGRAM_MODE"] == 2
    assert io.values["DHW_PROGRAM_MODE"] == 1
    assert state.buffer_heating_enabled is True
    assert state.dhw_enabled is False


def test_idempotent_calls_do_not_rewrite_same_value():
    io = InMemoryIO({"DHW_PROGRAM_MODE": 2})
    controller = ProgramSwitchingController(io)

    controller.enable_dhw()
    assert io.writes == []  # already set to on

    controller.disable_dhw()
    assert io.writes == [("DHW_PROGRAM_MODE", 1)]


def test_unknown_program_value_raises():
    io = InMemoryIO({"DHW_PROGRAM_MODE": 3})
    controller = ProgramSwitchingController(io)

    with pytest.raises(ValueError):
        controller.is_dhw_enabled()


def test_custom_param_names_and_program_values():
    config = ProgramSwitchConfig(
        dhw_program_param="CUSTOM_DHW",
        buffer_program_param="CUSTOM_BUF",
        program_off=1,
        program_on=2,
    )
    io = InMemoryIO({"CUSTOM_DHW": 1, "CUSTOM_BUF": 1})
    controller = ProgramSwitchingController(io, config=config)

    controller.enable_dhw()
    controller.enable_buffer_heating()

    assert io.values["CUSTOM_DHW"] == 2
    assert io.values["CUSTOM_BUF"] == 2
