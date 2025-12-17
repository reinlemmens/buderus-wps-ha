"""Buderus WPS Heat Pump Parameter Class.

# PROTOCOL: This module represents parameters from the FHEM KM273_elements_default array.
# Source: fhem/26_KM273v018.pm

This module provides classes for representing and accessing Buderus WPS heat pump parameters.
The Parameter class represents a single configurable or readable value with metadata including
index, external ID, min/max constraints, format type, read-only flag, and human-readable name.

The HeatPump class provides a container for all parameters with efficient lookup by either
index number or parameter name.

Classes:
    Parameter: Immutable dataclass representing a single heat pump parameter
    HeatPump: Container providing indexed access to all heat pump parameters

Example:
    >>> from buderus_wps.parameter import HeatPump
    >>> heat_pump = HeatPump()
    >>> param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
    >>> print(f"Valid range: {param.min}-{param.max}")
    Valid range: 0-5
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Parameter:
    """Represents a single Buderus WPS heat pump parameter.

    # PROTOCOL: Maps to entries in @KM273_elements_default from fhem/26_KM273v018.pm

    This class is immutable (frozen) to prevent accidental modification of parameter
    metadata. All attributes are preserved exactly as defined in the FHEM reference
    implementation.

    Attributes:
        idx: Sequential parameter index (may have gaps in sequence, e.g., 13 missing)
        extid: External ID - 14-character hex string for CAN addressing
        min: Minimum allowed value (can be negative for temperature parameters)
        max: Maximum allowed value (must be >= min)
        format: Data format type (e.g., "int", "temp")
        read: Read-only flag (0 = writable, 1 = read-only)
        text: Human-readable parameter name in ALL_CAPS_WITH_UNDERSCORES format

    Example:
        >>> param = Parameter(
        ...     idx=1,
        ...     extid="61E1E1FC660023",
        ...     min=0,
        ...     max=5,
        ...     format="int",
        ...     read=0,
        ...     text="ACCESS_LEVEL"
        ... )
        >>> param.is_writable()
        True
        >>> param.validate_value(3)
        True
        >>> param.validate_value(10)
        False
    """

    idx: int
    extid: str
    min: int
    max: int
    format: str
    read: int
    text: str

    def is_writable(self) -> bool:
        """Check if parameter is writable (not read-only).

        Returns:
            True if parameter can be written (read=0), False if read-only (read=1)

        Example:
            >>> writable_param = Parameter(idx=1, extid="...", min=0, max=5,
            ...                            format="int", read=0, text="ACCESS_LEVEL")
            >>> writable_param.is_writable()
            True
            >>> readonly_param = Parameter(idx=22, extid="...", min=0, max=16777216,
            ...                            format="int", read=1, text="STATUS")
            >>> readonly_param.is_writable()
            False
        """
        return self.read == 0

    def validate_value(self, value: int) -> bool:
        """Validate if a value is within the allowed min/max range.

        Args:
            value: The value to validate

        Returns:
            True if min <= value <= max, False otherwise

        Example:
            >>> param = Parameter(idx=1, extid="...", min=0, max=5,
            ...                   format="int", read=0, text="ACCESS_LEVEL")
            >>> param.validate_value(3)
            True
            >>> param.validate_value(10)
            False
            >>> param.validate_value(-1)
            False
        """
        return self.min <= value <= self.max


class HeatPump:
    """Container for all Buderus WPS heat pump parameters with indexed access.

    Provides efficient O(1) lookup of parameters by either index number or
    human-readable name. Loads all parameters from parameter_data on initialization.

    Example:
        >>> heat_pump = HeatPump()
        >>> param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
        >>> print(f"{param.text}: {param.min}-{param.max}")
        ACCESS_LEVEL: 0-5
        >>> same_param = heat_pump.get_parameter_by_index(1)
        >>> assert param == same_param
    """

    def __init__(self):
        """Initialize HeatPump and load all parameters from parameter_data."""
        from buderus_wps.parameter_data import PARAMETER_DATA

        self._params_by_idx: Dict[int, Parameter] = {}
        self._params_by_name: Dict[str, Parameter] = {}

        # Load all parameters
        for param_data in PARAMETER_DATA:
            param = Parameter(**param_data)
            self._params_by_idx[param.idx] = param
            self._params_by_name[param.text] = param

    def get_parameter_by_index(self, idx: int) -> Parameter:
        """Get parameter by index number.

        Args:
            idx: Parameter index (e.g., 1 for ACCESS_LEVEL)

        Returns:
            Parameter object with all metadata

        Raises:
            KeyError: If index does not exist

        Example:
            >>> heat_pump = HeatPump()
            >>> param = heat_pump.get_parameter_by_index(1)
            >>> param.text
            'ACCESS_LEVEL'
        """
        return self._params_by_idx[idx]

    def get_parameter_by_name(self, name: str) -> Parameter:
        """Get parameter by human-readable name.

        Args:
            name: Parameter name (e.g., "ACCESS_LEVEL")

        Returns:
            Parameter object with all metadata

        Raises:
            KeyError: If name does not exist

        Example:
            >>> heat_pump = HeatPump()
            >>> param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
            >>> param.idx
            1
        """
        return self._params_by_name[name]

    def has_parameter_index(self, idx: int) -> bool:
        """Check if parameter index exists.

        Args:
            idx: Parameter index to check

        Returns:
            True if parameter exists, False otherwise

        Example:
            >>> heat_pump = HeatPump()
            >>> heat_pump.has_parameter_index(1)
            True
            >>> heat_pump.has_parameter_index(13)  # Gap in sequence
            False
        """
        return idx in self._params_by_idx

    def has_parameter_name(self, name: str) -> bool:
        """Check if parameter name exists.

        Args:
            name: Parameter name to check

        Returns:
            True if parameter exists, False otherwise

        Example:
            >>> heat_pump = HeatPump()
            >>> heat_pump.has_parameter_name("ACCESS_LEVEL")
            True
            >>> heat_pump.has_parameter_name("INVALID_NAME")
            False
        """
        return name in self._params_by_name

    def list_all_parameters(self) -> List[Parameter]:
        """Return all parameters sorted by index.

        Returns:
            List of all Parameter objects sorted by idx

        Example:
            >>> heat_pump = HeatPump()
            >>> params = heat_pump.list_all_parameters()
            >>> len(params)
            1789
            >>> params[0].idx
            0
        """
        return sorted(self._params_by_idx.values(), key=lambda p: p.idx)

    def list_writable_parameters(self) -> List[Parameter]:
        """Return only writable (read=0) parameters sorted by index.

        Returns:
            List of writable Parameter objects sorted by idx

        Example:
            >>> heat_pump = HeatPump()
            >>> writable = heat_pump.list_writable_parameters()
            >>> all(p.is_writable() for p in writable)
            True
        """
        return sorted(
            [p for p in self._params_by_idx.values() if p.is_writable()],
            key=lambda p: p.idx
        )

    def list_readonly_parameters(self) -> List[Parameter]:
        """Return only read-only (read!=0) parameters sorted by index.

        Returns:
            List of read-only Parameter objects sorted by idx

        Example:
            >>> heat_pump = HeatPump()
            >>> readonly = heat_pump.list_readonly_parameters()
            >>> all(not p.is_writable() for p in readonly)
            True
        """
        return sorted(
            [p for p in self._params_by_idx.values() if not p.is_writable()],
            key=lambda p: p.idx
        )

    def parameter_count(self) -> int:
        """Return total number of parameters.

        Returns:
            Total parameter count

        Example:
            >>> heat_pump = HeatPump()
            >>> heat_pump.parameter_count()
            1789
        """
        return len(self._params_by_idx)
