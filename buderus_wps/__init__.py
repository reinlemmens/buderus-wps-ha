"""
Buderus WPS Heat Pump CAN Bus Communication Library.

This library provides communication with Buderus WPS heat pumps via CAN bus
using USBtin adapters. It implements the SLCAN (Lawicel) protocol for serial
communication and provides type-safe message handling with comprehensive
error reporting.

Core Components:
    - CANMessage: Immutable CAN message representation
    - USBtinAdapter: Serial connection and message transmission
    - ValueEncoder: Temperature and integer encoding utilities

Example:
    >>> from buderus_wps import USBtinAdapter, CANMessage
    >>> with USBtinAdapter('/dev/ttyACM0') as adapter:
    ...     msg = CANMessage(arbitration_id=0x31D011E9, data=b'\\x01', is_extended_id=True)
    ...     response = adapter.send_frame(msg)

Constitution Compliance:
    - Library-first architecture (Principle I)
    - SLCAN protocol fidelity (Principle II)
    - Input validation and error handling (Principle III)
    - 100% test coverage (Principle IV)
    - Protocol documentation (Principle V)
"""

__version__ = "0.1.0"
__author__ = "Buderus WPS HA Project"
__license__ = "MIT"

from .can_message import CANMessage
from .can_adapter import USBtinAdapter
from .exceptions import (
    AlarmNotClearableError,
    BuderusCANException,
    CircuitNotAvailableError,
    ConnectionError,
    DeviceCommunicationError,
    DeviceDisconnectedError,
    DeviceInitializationError,
    DeviceNotFoundError,
    DevicePermissionError,
    MenuAPIError,
    MenuNavigationError,
    ParameterNotFoundError,
    ReadOnlyError,
    TimeoutError,
    ValidationError,
)
from .program_switching import (
    ProgramSwitchingController,
    ProgramSwitchConfig,
    ProgramState,
    ParameterIO,
)
from .value_encoder import ValueEncoder
from .parameter_registry import ParameterRegistry, Parameter
from .heat_pump import HeatPumpClient
from .enums import (
    AlarmCategory,
    CircuitType,
    DHWProgramMode,
    OperatingMode,
    RoomProgramMode,
)
from .schedule_codec import ScheduleCodec, ScheduleSlot, WeeklySchedule
from .menu_api import (
    Alarm,
    AlarmController,
    Circuit,
    EnergyView,
    HotWaterController,
    MenuAPI,
    MenuNavigator,
    StatusSnapshot,
    StatusView,
    VacationController,
    VacationPeriod,
)
from .menu_structure import MenuItem
from .broadcast_monitor import (
    BroadcastMonitor,
    BroadcastReading,
    BroadcastCache,
    decode_can_id,
    encode_can_id,
    KNOWN_BROADCASTS,
)

__all__ = [
    # Exceptions
    "AlarmNotClearableError",
    "BuderusCANException",
    "CircuitNotAvailableError",
    "ConnectionError",
    "DeviceCommunicationError",
    "DeviceDisconnectedError",
    "DeviceInitializationError",
    "DeviceNotFoundError",
    "DevicePermissionError",
    "MenuAPIError",
    "MenuNavigationError",
    "ParameterNotFoundError",
    "ReadOnlyError",
    "TimeoutError",
    "ValidationError",
    # Core classes
    "CANMessage",
    "HeatPumpClient",
    "Parameter",
    "ParameterIO",
    "ParameterRegistry",
    "ProgramState",
    "ProgramSwitchConfig",
    "ProgramSwitchingController",
    "USBtinAdapter",
    "ValueEncoder",
    # Menu API enums
    "AlarmCategory",
    "CircuitType",
    "DHWProgramMode",
    "OperatingMode",
    "RoomProgramMode",
    # Menu API data classes
    "Alarm",
    "MenuItem",
    "ScheduleSlot",
    "StatusSnapshot",
    "VacationPeriod",
    "WeeklySchedule",
    # Menu API controllers
    "AlarmController",
    "Circuit",
    "EnergyView",
    "HotWaterController",
    "MenuAPI",
    "MenuNavigator",
    "ScheduleCodec",
    "StatusView",
    "VacationController",
    # Broadcast monitor
    "BroadcastCache",
    "BroadcastMonitor",
    "BroadcastReading",
    "decode_can_id",
    "encode_can_id",
    "KNOWN_BROADCASTS",
]
