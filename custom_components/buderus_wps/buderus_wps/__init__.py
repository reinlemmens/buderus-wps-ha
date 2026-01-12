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

from .broadcast_monitor import (
    KNOWN_BROADCASTS,
    BroadcastCache,
    BroadcastMonitor,
    BroadcastReading,
    decode_can_id,
    encode_can_id,
)
from .can_adapter import USBtinAdapter
from .can_message import (
    CAN_PREFIX_COUNTER,
    CAN_PREFIX_DATA,
    CANMessage,
)
from .config import (
    CircuitConfig,
    DHWConfig,
    HeatingType,
    InstallationConfig,
    SensorMapping,
    SensorType,
    get_default_config,
    get_default_sensor_map,
    load_config,
)
from .element_discovery import (
    ELEMENT_COUNT_REQUEST_ID,
    ELEMENT_COUNT_RESPONSE_ID,
    ELEMENT_DATA_REQUEST_ID,
    ELEMENT_DATA_RESPONSE_ID,
    DiscoveredElement,
    ElementDiscovery,
    ElementListParser,
)
from .energy_blocking import (
    BlockingResult,
    BlockingState,
    BlockingStatus,
    EnergyBlockingControl,
)
from .enums import (
    AlarmCategory,
    CircuitType,
    DHWProgramMode,
    OperatingMode,
    RoomProgramMode,
)
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
from .heat_pump import HeatPumpClient
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
from .parameter import HeatPump, Parameter
from .program_switching import (
    ParameterIO,
    ProgramState,
    ProgramSwitchConfig,
    ProgramSwitchingController,
)
from .schedule_codec import ScheduleCodec, ScheduleSlot, WeeklySchedule
from .value_encoder import ValueEncoder

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
    # CAN Message and Adapter
    "CANMessage",
    "USBtinAdapter",
    # CAN ID Constants (Hardware Verified 2025-12-05)
    # Heat Pump Interface
    "HeatPump",
    "HeatPumpClient",
    "Parameter",
    "ParameterIO",
    "ProgramState",
    "ProgramSwitchConfig",
    "ProgramSwitchingController",
    # Utilities
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
    # Configuration
    "CircuitConfig",
    "DHWConfig",
    "HeatingType",
    "InstallationConfig",
    "SensorMapping",
    "SensorType",
    "get_default_config",
    "get_default_sensor_map",
    "load_config",
    # Energy Blocking
    "BlockingResult",
    "BlockingState",
    "BlockingStatus",
    "EnergyBlockingControl",
    # Element Discovery
    "DiscoveredElement",
    "ElementDiscovery",
    "ElementListParser",
    "ELEMENT_COUNT_REQUEST_ID",
    "ELEMENT_COUNT_RESPONSE_ID",
    "ELEMENT_DATA_REQUEST_ID",
    "ELEMENT_DATA_RESPONSE_ID",
]
