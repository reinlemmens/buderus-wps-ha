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

from .can_adapter import USBtinAdapter
from .can_message import (
    CANMessage,
    CAN_PREFIX_COUNTER,
    CAN_PREFIX_DATA,
    CAN_PREFIX_STATUS,
    ELEMENT_CONFIG,
    ELEMENT_COUNTER,
    ELEMENT_E21,
    ELEMENT_E22,
    ELEMENT_E31,
    ELEMENT_E32,
)
from .exceptions import (
    BuderusCANException,
    ConnectionError,
    DeviceCommunicationError,
    DeviceDisconnectedError,
    DeviceInitializationError,
    DeviceNotFoundError,
    DevicePermissionError,
    TimeoutError,
)
from .heat_pump import HeatPumpClient
from .parameter_registry import Parameter, ParameterRegistry
from .program_switching import (
    ParameterIO,
    ProgramState,
    ProgramSwitchConfig,
    ProgramSwitchingController,
)
from .value_encoder import ValueEncoder

__all__ = [
    # Exceptions
    "BuderusCANException",
    "ConnectionError",
    "DeviceCommunicationError",
    "DeviceDisconnectedError",
    "DeviceInitializationError",
    "DeviceNotFoundError",
    "DevicePermissionError",
    "TimeoutError",
    # CAN Message and Adapter
    "CANMessage",
    "USBtinAdapter",
    # CAN ID Constants (Hardware Verified 2025-12-05)
    "CAN_PREFIX_COUNTER",
    "CAN_PREFIX_DATA",
    "CAN_PREFIX_STATUS",
    "ELEMENT_CONFIG",
    "ELEMENT_COUNTER",
    "ELEMENT_E21",
    "ELEMENT_E22",
    "ELEMENT_E31",
    "ELEMENT_E32",
    # Heat Pump Interface
    "HeatPumpClient",
    "Parameter",
    "ParameterIO",
    "ParameterRegistry",
    "ProgramState",
    "ProgramSwitchConfig",
    "ProgramSwitchingController",
    # Utilities
    "ValueEncoder",
]
