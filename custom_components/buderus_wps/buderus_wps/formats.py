"""FHEM-compatible format specifications for Buderus WPS heat pump.

# PROTOCOL: Matches %KM273_format hash from fhem/26_KM273v018.pm:2011-2025

This module provides format specifications matching the FHEM reference
implementation exactly. Each format defines:
- factor: Scaling factor for encoding/decoding
- unit: Display unit string
- select: Optional list of enumeration values (for selector formats)

Example:
    >>> from buderus_wps.formats import FHEM_FORMATS
    >>> fmt = FHEM_FORMATS['tem']
    >>> raw_value = 530
    >>> decoded = raw_value * fmt['factor']  # 53.0°C
"""

from typing import Any, Dict, List, Optional

# PROTOCOL: Exact copy of %KM273_format from fhem/26_KM273v018.pm:2011-2025
FHEM_FORMATS: Dict[str, Dict[str, Any]] = {
    "int": {"factor": 1, "unit": ""},
    "t15": {"factor": 1, "unit": ""},
    "hm1": {"factor": 1, "unit": "s"},
    "hm2": {"factor": 10, "unit": "s"},
    "tem": {"factor": 0.1, "unit": "°C"},
    "pw2": {"factor": 0.01, "unit": "kW"},
    "pw3": {"factor": 0.001, "unit": "kW"},
    "sw1": {"factor": 1, "unit": ""},
    "sw2": {"factor": 1, "unit": ""},
    "rp1": {
        "factor": 1,
        "unit": "",
        "select": [
            "0:HP_Optimized",
            "1:Program_1",
            "2:Program_2",
            "3:Family",
            "4:Morning",
            "5:Evening",
            "6:Seniors",
        ],
    },
    "rp2": {
        "factor": 1,
        "unit": "",
        "select": [
            "0:Automatic",
            "1:Normal",
            "2:Exception",
            "3:HeatingOff",
        ],
    },
    "dp1": {
        "factor": 1,
        "unit": "",
        "select": [
            "0:Always_On",
            "1:Program_1",
            "2:Program_2",
        ],
    },
    "dp2": {
        "factor": 1,
        "unit": "",
        "select": [
            "0:Automatic",
            "1:Always_On",
            "2:Always_Off",
        ],
    },
}


# PROTOCOL: DEAD sensor value from fhem/26_KM273v018.pm:2877
# Raw value 0xDEAD (-8531 as signed 16-bit) indicates disconnected sensor
DEAD_VALUE = -8531


def get_format_factor(format_type: str) -> float:
    """Get the scaling factor for a format type.

    Args:
        format_type: Format name (e.g., 'tem', 'pw2')

    Returns:
        Scaling factor (1.0 if format unknown)
    """
    fmt = FHEM_FORMATS.get(format_type, {})
    return float(fmt.get("factor", 1))


def get_format_unit(format_type: str) -> str:
    """Get the unit string for a format type.

    Args:
        format_type: Format name (e.g., 'tem', 'pw2')

    Returns:
        Unit string (empty if format unknown)
    """
    fmt = FHEM_FORMATS.get(format_type, {})
    return str(fmt.get("unit", ""))


def get_format_select(format_type: str) -> Optional[List[str]]:
    """Get the select options for a format type.

    Args:
        format_type: Format name (e.g., 'rp1', 'dp2')

    Returns:
        List of select options or None if not a selector format
    """
    fmt = FHEM_FORMATS.get(format_type, {})
    return fmt.get("select")


def is_dead_value(value: int) -> bool:
    """Check if a raw value indicates a dead/disconnected sensor.

    # PROTOCOL: DEAD value 0xDEAD from fhem/26_KM273v018.pm:2877

    Args:
        value: Raw signed integer value

    Returns:
        True if value indicates dead sensor
    """
    return value == DEAD_VALUE


def decode_select_value(raw_value: int, format_type: str) -> str:
    """Decode a raw value to its selector string.

    # PROTOCOL: Select decoding from fhem/26_KM273v018.pm:2714-2724

    Args:
        raw_value: Raw integer value
        format_type: Format name (e.g., 'rp1', 'dp2')

    Returns:
        Selector string (e.g., '0:Automatic') or raw value as string if not found
    """
    select_list = get_format_select(format_type)
    if select_list is None:
        return str(raw_value)

    # FHEM: Match by finding the value at the start of the option string
    for option in select_list:
        if option.startswith(f"{raw_value}:"):
            return option

    return str(raw_value)


def encode_select_value(value: str, format_type: str) -> int:
    """Encode a selector string to its raw integer value.

    # PROTOCOL: Select encoding from fhem/26_KM273v018.pm:2714-2724

    Args:
        value: Selector string (e.g., '0:Automatic' or just '0')
        format_type: Format name (e.g., 'rp1', 'dp2')

    Returns:
        Raw integer value

    Raises:
        ValueError: If value cannot be matched to a selector option
    """
    select_list = get_format_select(format_type)

    # Try to parse as plain integer first
    try:
        return int(value)
    except ValueError:
        pass

    # Extract numeric part from selector string (e.g., '0:Automatic' -> 0)
    if ":" in value:
        try:
            return int(value.split(":")[0])
        except ValueError:
            pass

    # Search for matching option
    if select_list:
        for option in select_list:
            if value in option:
                try:
                    return int(option.split(":")[0])
                except ValueError:
                    pass

    raise ValueError(f"Cannot encode '{value}' for format '{format_type}'")
