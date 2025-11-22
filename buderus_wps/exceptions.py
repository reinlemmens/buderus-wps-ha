"""
Exception hierarchy for Buderus CAN communication library.

This module defines all custom exceptions used throughout the library,
providing clear error messages with diagnostic context.

Exception Hierarchy:
    BuderusCANException (base)
    ├── ConnectionError
    │   ├── DeviceNotFoundError
    │   ├── DevicePermissionError
    │   ├── DeviceDisconnectedError
    │   ├── DeviceInitializationError
    │   └── DeviceCommunicationError
    ├── TimeoutError
    │   ├── ReadTimeoutError
    │   └── WriteTimeoutError
    ├── CANError
    │   ├── CANBusOffError
    │   ├── CANBitrateError
    │   └── CANFrameError
    └── ConcurrencyError
"""

from typing import Any, Dict, Optional


class BuderusCANException(Exception):
    """
    Base exception for all Buderus CAN communication errors.

    All custom exceptions in this library inherit from this class,
    allowing broad exception handling when needed.

    Attributes:
        message: Human-readable error description
        context: Additional context information (port, timeout, etc.)
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize exception with message and optional context.

        Args:
            message: Error description
            context: Additional diagnostic information
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Format exception with context information."""
        base_msg = self.message
        if self.context:
            ctx_items = [f"{k}={v}" for k, v in self.context.items()]
            return f"{base_msg} ({', '.join(ctx_items)})"
        return base_msg


# Connection Exceptions


class ConnectionError(BuderusCANException):
    """Base class for connection-related errors."""

    pass


class DeviceNotFoundError(ConnectionError):
    """Serial port device not found or not accessible."""

    pass


class DevicePermissionError(DeviceNotFoundError):
    """Insufficient permissions to access serial port."""

    pass


class DeviceDisconnectedError(ConnectionError):
    """Device disconnected during operation."""

    pass


class DeviceInitializationError(ConnectionError):
    """USBtin initialization sequence failed."""

    pass


class DeviceCommunicationError(ConnectionError):
    """Communication error with device during operation."""

    pass


# Timeout Exceptions


class TimeoutError(BuderusCANException):
    """Base class for timeout-related errors."""

    pass


class ReadTimeoutError(TimeoutError):
    """Timeout while waiting to receive data from device."""

    pass


class WriteTimeoutError(TimeoutError):
    """Timeout while attempting to send data to device."""

    pass


# CAN Bus Exceptions


class CANError(BuderusCANException):
    """Base class for CAN bus protocol errors."""

    pass


class CANBusOffError(CANError):
    """CAN controller entered bus-off state due to too many errors."""

    pass


class CANBitrateError(CANError):
    """CAN bitrate mismatch between adapter and bus."""

    pass


class CANFrameError(CANError):
    """Malformed or invalid CAN frame."""

    pass


# Concurrency Exception


class ConcurrencyError(BuderusCANException):
    """Concurrent operation attempted on non-thread-safe adapter."""

    pass
