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

# Public API will be exported here after implementation
__all__ = []
