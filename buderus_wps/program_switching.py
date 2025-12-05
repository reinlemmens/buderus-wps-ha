"""
Program-based switching control for Buderus WPS heat pump functions.

This module provides a thin controller for toggling functions (DHW, buffer
heating) by switching between predefined program modes:
- program1: always-off
- program2: always-on

Behavior follows Feature Spec 003 (Program-Based Switching Control).
"""

from dataclasses import dataclass
from typing import Protocol


class ParameterIO(Protocol):
    """Minimal interface for reading/writing heat pump parameters."""

    def read(self, parameter: str) -> int:  # pragma: no cover - interface only
        ...

    def write(
        self, parameter: str, value: int
    ) -> None:  # pragma: no cover - interface only
        ...


@dataclass(frozen=True)
class ProgramSwitchConfig:
    """Configuration for program-based switching."""

    dhw_program_param: str = "DHW_PROGRAM_MODE"
    buffer_program_param: str = "ROOM_PROGRAM_MODE"
    program_off: int = 1  # program1: always-off
    program_on: int = 2  # program2: always-on


@dataclass(frozen=True)
class ProgramState:
    """Aggregated enablement state for supported functions."""

    dhw_enabled: bool
    buffer_heating_enabled: bool


class ProgramSwitchingController:
    """
    Controller that toggles heat pump functions by switching program modes.

    Functions are considered enabled when their program mode is set to the
    configured "always-on" program, and disabled when set to the "always-off"
    program. Unknown program values raise ValueError to surface misconfiguration.
    """

    def __init__(
        self, io: ParameterIO, config: ProgramSwitchConfig | None = None
    ) -> None:
        if io is None:
            raise ValueError("io cannot be None")
        self._io = io
        self._config = config or ProgramSwitchConfig()
        self._validate_program_value(self._config.program_off)
        self._validate_program_value(self._config.program_on)

    # Public API: DHW control
    def enable_dhw(self) -> None:
        self._set_program(self._config.dhw_program_param, enabled=True)

    def disable_dhw(self) -> None:
        self._set_program(self._config.dhw_program_param, enabled=False)

    def is_dhw_enabled(self) -> bool:
        return self._is_enabled(self._config.dhw_program_param)

    # Public API: Buffer heating control
    def enable_buffer_heating(self) -> None:
        self._set_program(self._config.buffer_program_param, enabled=True)

    def disable_buffer_heating(self) -> None:
        self._set_program(self._config.buffer_program_param, enabled=False)

    def is_buffer_heating_enabled(self) -> bool:
        return self._is_enabled(self._config.buffer_program_param)

    def get_state(self) -> ProgramState:
        """Return current enablement state for all supported functions."""
        return ProgramState(
            dhw_enabled=self.is_dhw_enabled(),
            buffer_heating_enabled=self.is_buffer_heating_enabled(),
        )

    # Internal helpers
    def _set_program(self, parameter: str, *, enabled: bool) -> None:
        target = self._config.program_on if enabled else self._config.program_off
        current = self._io.read(parameter)
        # No-op on idempotent calls
        if current == target:
            return
        self._io.write(parameter, target)

    def _is_enabled(self, parameter: str) -> bool:
        value = self._io.read(parameter)
        return self._program_value_to_bool(parameter, value)

    def _program_value_to_bool(self, parameter: str, value: int) -> bool:
        if value == self._config.program_on:
            return True
        if value == self._config.program_off:
            return False
        raise ValueError(
            f"Unexpected program value for {parameter}: {value}. "
            f"Expected {self._config.program_off} (off) or {self._config.program_on} (on)."
        )

    @staticmethod
    def _validate_program_value(value: int) -> None:
        if value not in (1, 2):
            raise ValueError(f"Program values must be 1 (off) or 2 (on). Got {value}.")
