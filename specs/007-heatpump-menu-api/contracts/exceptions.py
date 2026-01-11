"""
API Contract: Exceptions

This file defines the exception hierarchy for the Menu API.

Note: This is a design document, not implementation code.
"""

from typing import Any, Optional, Tuple


class MenuAPIError(Exception):
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
        allowed_range: Optional[Tuple[Any, Any]] = None,
    ):
        self.field = field
        self.value = value
        self.constraint = constraint
        self.allowed_range = allowed_range

        msg = f"Validation failed for '{field}': {constraint}"
        if allowed_range:
            msg += f" (allowed: {allowed_range[0]} to {allowed_range[1]})"
        msg += f". Got: {value}"

        super().__init__(msg)


class ReadOnlyError(MenuAPIError):
    """
    Raised when attempting to write to a read-only parameter.

    Attributes:
        parameter: The read-only parameter name
    """

    def __init__(self, parameter: str):
        self.parameter = parameter
        super().__init__(f"Parameter '{parameter}' is read-only")


class ParameterNotFoundError(MenuAPIError):
    """
    Raised when a parameter is not available on this heat pump model.

    Attributes:
        parameter: The parameter that was not found
    """

    def __init__(self, parameter: str):
        self.parameter = parameter
        super().__init__(f"Parameter '{parameter}' not available on this heat pump")


class MenuNavigationError(MenuAPIError):
    """
    Raised when menu navigation fails.

    Attributes:
        path: The path that could not be navigated
        available: List of available paths at the failure point
    """

    def __init__(self, path: str, available: list):
        self.path = path
        self.available = available
        super().__init__(
            f"Menu path '{path}' not found. Available: {', '.join(available)}"
        )


class AlarmNotClearableError(MenuAPIError):
    """
    Raised when attempting to clear an alarm that cannot be cleared.

    Attributes:
        alarm_code: The alarm code
        reason: Why the alarm cannot be cleared
    """

    def __init__(
        self, alarm_code: int, reason: str = "underlying condition not resolved"
    ):
        self.alarm_code = alarm_code
        self.reason = reason
        super().__init__(f"Alarm {alarm_code} cannot be cleared: {reason}")


class CircuitNotAvailableError(MenuAPIError):
    """
    Raised when accessing a circuit that is not configured on this installation.

    Attributes:
        circuit: The circuit number
        available_circuits: List of available circuit numbers
    """

    def __init__(self, circuit: int, available_circuits: list):
        self.circuit = circuit
        self.available_circuits = available_circuits
        super().__init__(
            f"Circuit {circuit} not available. Available circuits: {available_circuits}"
        )
