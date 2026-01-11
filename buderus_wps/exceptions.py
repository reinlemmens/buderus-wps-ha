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


# Menu API Exceptions


class MenuAPIError(BuderusCANException):
    """Base exception for all Menu API errors."""

    pass


class ValidationError(MenuAPIError):
    """
    Raised when a value fails validation before being sent to the heat pump.

    Attributes:
        field: The field that failed validation
        value: The invalid value
        constraint: Description of the violated constraint
        allowed_range: Optional tuple of (min, max) allowed values
    """

    def __init__(
        self,
        field: str,
        value: Any,
        constraint: str,
        allowed_range: Optional[tuple] = None,
    ) -> None:
        self.field = field
        self.value = value
        self.constraint = constraint
        self.allowed_range = allowed_range

        msg = f"Validation failed for '{field}': {constraint}"
        if allowed_range:
            msg += f" (allowed: {allowed_range[0]} to {allowed_range[1]})"
        msg += f". Got: {value}"

        super().__init__(msg, context={"field": field, "value": value})


class ReadOnlyError(MenuAPIError):
    """Raised when attempting to write to a read-only parameter."""

    def __init__(self, parameter: str) -> None:
        self.parameter = parameter
        super().__init__(
            f"Parameter '{parameter}' is read-only", context={"parameter": parameter}
        )


class ParameterNotFoundError(MenuAPIError):
    """Raised when a parameter is not available on this heat pump model."""

    def __init__(self, parameter: str) -> None:
        self.parameter = parameter
        super().__init__(
            f"Parameter '{parameter}' not available on this heat pump",
            context={"parameter": parameter},
        )


class MenuNavigationError(MenuAPIError):
    """Raised when menu navigation fails."""

    def __init__(self, path: str, available: list) -> None:
        self.path = path
        self.available = available
        super().__init__(
            f"Menu path '{path}' not found. Available: {', '.join(available)}",
            context={"path": path, "available": available},
        )


class AlarmNotClearableError(MenuAPIError):
    """Raised when attempting to clear an alarm that cannot be cleared."""

    def __init__(
        self, alarm_code: int, reason: str = "underlying condition not resolved"
    ) -> None:
        self.alarm_code = alarm_code
        self.reason = reason
        super().__init__(
            f"Alarm {alarm_code} cannot be cleared: {reason}",
            context={"alarm_code": alarm_code, "reason": reason},
        )


class CircuitNotAvailableError(MenuAPIError):
    """Raised when accessing a circuit that is not configured on this installation."""

    def __init__(self, circuit: int, available_circuits: list) -> None:
        self.circuit = circuit
        self.available_circuits = available_circuits
        super().__init__(
            f"Circuit {circuit} not available. Available circuits: {available_circuits}",
            context={"circuit": circuit, "available_circuits": available_circuits},
        )


# Discovery Exceptions


class DiscoveryError(BuderusCANException):
    """Base class for element discovery errors."""

    pass


class DiscoveryIncompleteError(DiscoveryError):
    """Raised when element discovery returns fewer bytes than expected.

    Attributes:
        actual_count: Number of bytes actually received
        reported_count: Number of bytes reported by the device
        completion_ratio: Ratio of actual/reported (0.0-1.0)
    """

    def __init__(self, actual_count: int, reported_count: int) -> None:
        self.actual_count = actual_count
        self.reported_count = reported_count
        self.completion_ratio = (
            actual_count / reported_count if reported_count > 0 else 0.0
        )
        super().__init__(
            f"Discovery incomplete: got {actual_count}/{reported_count} bytes "
            f"({self.completion_ratio * 100:.1f}%)",
            context={
                "actual_count": actual_count,
                "reported_count": reported_count,
                "completion_ratio": self.completion_ratio,
            },
        )


class DiscoveryRequiredError(DiscoveryError):
    """Raised when discovery is required but failed and no valid cache exists.

    This error indicates a fresh install scenario where discovery failed
    and there's no previous successful cache to fall back to. The integration
    cannot start with correct parameter indices.

    Attributes:
        reason: Description of why discovery failed
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f"Discovery required but failed: {reason}. "
            "Ensure CAN adapter is connected and heat pump is powered on, then restart.",
            context={"reason": reason},
        )
