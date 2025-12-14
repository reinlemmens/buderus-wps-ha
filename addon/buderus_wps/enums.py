"""
Enumeration types for the Heat Pump Menu API.

This module defines all enums used across the Menu API to represent
operating modes, program modes, circuit types, and alarm categories.
"""

from enum import Enum, auto


class OperatingMode(Enum):
    """Heat pump operating states."""

    STANDBY = 0
    HEATING = 1
    COOLING = 2
    DHW_PRIORITY = 3
    DEFROST = 4


class RoomProgramMode(Enum):
    """Room heating program modes."""

    HP_OPTIMIZED = 0
    PROGRAM_1 = 1
    PROGRAM_2 = 2
    FAMILY = 3
    MORNING = 4
    EVENING = 5
    SENIORS = 6


class DHWProgramMode(Enum):
    """DHW (hot water) program modes."""

    ALWAYS_ON = 0
    PROGRAM_1 = 1
    PROGRAM_2 = 2


class CircuitType(Enum):
    """Heating circuit types."""

    UNMIXED = auto()  # Primary circuit (circuit 1)
    MIXED = auto()  # Secondary circuits (2-4) with mixing valve


class AlarmCategory(Enum):
    """Alarm severity categories."""

    INFO = 0
    WARNING = 1
    ALARM = 2
