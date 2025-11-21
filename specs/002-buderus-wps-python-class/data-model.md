# Data Model: Buderus WPS Heat Pump Python Class

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-10-24
**Status**: Complete

## Overview

This document defines the data model for representing Buderus WPS heat pump parameters in Python. The model preserves the exact structure from the FHEM KM273_elements_default array while providing Pythonic access patterns.

## Entities

### 1. Parameter

**Description**: Represents a single configurable or readable value on the Buderus WPS heat pump.

**Source**: Maps 1:1 with entries in `@KM273_elements_default` array from `fhem/26_KM273v018.pm`

**Attributes**:

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| idx | int | Sequential parameter index | >= 0, may have gaps in sequence |
| extid | str | External ID (CAN address) | 14-character hex string |
| min | int | Minimum allowed value | Can be negative (e.g., temperature) |
| max | int | Maximum allowed value | >= min |
| format | str | Data format type | Known values: "int", "temp", etc. |
| read | int | Read-only flag | 0 = writable, 1 = read-only |
| text | str | Human-readable name | ALL_CAPS_WITH_UNDERSCORES format |

**Methods**:

```python
def is_writable(self) -> bool:
    """Check if parameter is writable (not read-only)."""

def validate_value(self, value: int) -> bool:
    """Check if value is within allowed min/max range."""

def __repr__(self) -> str:
    """String representation for debugging."""
```

**Invariants**:
- Immutable (frozen dataclass)
- max >= min
- extid format matches protocol spec
- read is either 0 or 1

**Example Instances**:

```python
# Writable parameter with valid range
Parameter(
    idx=1,
    extid="61E1E1FC660023",
    min=0,
    max=5,
    format="int",
    read=0,
    text="ACCESS_LEVEL"
)

# Read-only parameter
Parameter(
    idx=22,
    extid="C02D7CE3A909E9",
    min=0,
    max=16777216,
    format="int",
    read=1,
    text="ADDITIONAL_DHW_ACKNOWLEDGED"
)

# Parameter with negative minimum (temperature)
Parameter(
    idx=11,
    extid="E555E4E11002E9",
    min=-30,
    max=40,
    format="int",
    read=0,
    text="ADDITIONAL_BLOCK_HIGH_T2_TEMP"
)

# Flag parameter (min=max=0)
Parameter(
    idx=0,
    extid="814A53C66A0802",
    min=0,
    max=0,
    format="int",
    read=0,
    text="ACCESSORIES_CONNECTED_BITMASK"
)
```

### 2. HeatPump

**Description**: Container class providing access to all heat pump parameters with efficient lookup by index or name.

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| _params_by_idx | dict[int, Parameter] | Internal index for O(1) lookup by idx |
| _params_by_name | dict[str, Parameter] | Internal index for O(1) lookup by name |

**Methods**:

```python
def get_parameter_by_index(self, idx: int) -> Parameter:
    """
    Get parameter by index value.

    Args:
        idx: Parameter index (e.g., 1 for ACCESS_LEVEL)

    Returns:
        Parameter object with all metadata

    Raises:
        KeyError: If index does not exist
    """

def get_parameter_by_name(self, name: str) -> Parameter:
    """
    Get parameter by human-readable name.

    Args:
        name: Parameter name (e.g., "ACCESS_LEVEL")

    Returns:
        Parameter object with all metadata

    Raises:
        KeyError: If name does not exist
    """

def has_parameter_index(self, idx: int) -> bool:
    """Check if parameter index exists."""

def has_parameter_name(self, name: str) -> bool:
    """Check if parameter name exists."""

def list_all_parameters(self) -> list[Parameter]:
    """Return all parameters sorted by index."""

def list_writable_parameters(self) -> list[Parameter]:
    """Return only writable (read=0) parameters sorted by index."""

def list_readonly_parameters(self) -> list[Parameter]:
    """Return only read-only (read=1) parameters sorted by index."""

def parameter_count(self) -> int:
    """Return total number of parameters."""
```

**Invariants**:
- _params_by_idx and _params_by_name always refer to same Parameter instances
- Both dicts have same number of entries
- Singleton pattern or module-level instance (TBD during implementation)

**Usage Pattern**:

```python
# Instantiate once (likely module-level singleton)
heat_pump = HeatPump()

# Access by index
param = heat_pump.get_parameter_by_index(1)
print(f"{param.text}: {param.min}-{param.max}")

# Access by name
param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
if param.is_writable():
    if param.validate_value(3):
        print(f"Value 3 is valid for {param.text}")

# List all parameters
for param in heat_pump.list_all_parameters():
    print(f"[{param.idx}] {param.text}")
```

## Relationships

```
┌─────────────┐
│  HeatPump   │
│             │
│             │  contains
│             ├──────────────┐
│             │              │
│             │          0..N│
└─────────────┘              │
                             │
                             ▼
                    ┌─────────────┐
                    │  Parameter  │
                    │             │
                    │ idx: int    │
                    │ extid: str  │
                    │ min: int    │
                    │ max: int    │
                    │ format: str │
                    │ read: int   │
                    │ text: str   │
                    └─────────────┘
```

- **HeatPump contains many Parameters**: 1:N relationship
- **Parameters are independent**: No relationships between Parameter instances
- **Lookup indices owned by HeatPump**: _params_by_idx and _params_by_name are internal implementation details

## Data Source

**Primary Source**: `fhem/26_KM273v018.pm` - `@KM273_elements_default` array starting at line 218

**Conversion Process**:
1. Parse Perl array structure (one-time manual process)
2. Convert to Python list of dicts
3. Store in `buderus_wps/parameter_data.py` as `PARAMETER_DATA` constant
4. HeatPump loads data at initialization

**Example Data Structure** (parameter_data.py):
```python
"""
Parameter data extracted from fhem/26_KM273v018.pm @KM273_elements_default array.

# PROTOCOL: This data MUST match the FHEM reference implementation exactly.
# Source: fhem/26_KM273v018.pm lines 218-XXX
# Extraction date: 2025-10-24
"""

PARAMETER_DATA = [
    {
        "idx": 0,
        "extid": "814A53C66A0802",
        "max": 0,
        "min": 0,
        "format": "int",
        "read": 0,
        "text": "ACCESSORIES_CONNECTED_BITMASK"
    },
    {
        "idx": 1,
        "extid": "61E1E1FC660023",
        "max": 5,
        "min": 0,
        "format": "int",
        "read": 0,
        "text": "ACCESS_LEVEL"
    },
    # ... 400+ more entries
]
```

## Validation Rules

### Parameter Validation

1. **Index uniqueness**: Each idx value appears exactly once
2. **Name uniqueness**: Each text value appears exactly once
3. **ExtID uniqueness**: Each extid value appears exactly once (assumed, verify in tests)
4. **Min/Max relationship**: max >= min for all parameters
5. **Read flag values**: read is either 0 or 1
6. **Format values**: format is non-empty string
7. **Text format**: text uses ALL_CAPS_WITH_UNDERSCORES convention

### Value Validation (by Parameter)

1. **Range check**: min <= value <= max
2. **Type check**: value is integer (format interpretation for future features)
3. **Read-only check**: If read=1, parameter should not be written (enforced by caller, not Parameter class)

## Edge Cases

### Non-Sequential Indices

**Example**: idx sequence has gaps (13 missing between 12 and 14)

**Handling**:
- Dict-based lookup handles naturally
- get_parameter_by_index(13) raises KeyError
- Documented in code comments
- Contract tests verify Python matches FHEM exactly

### Flag Parameters (min=max=0)

**Example**: ACCESSORIES_CONNECTED_BITMASK has min=0, max=0

**Handling**:
- validate_value(0) returns True
- validate_value(non-zero) returns False
- Likely indicates bitmask or boolean flag
- No special handling needed in validation logic

### Negative Minimum Values

**Example**: Temperature parameters can have min=-30

**Handling**:
- Python int supports negative values naturally
- Range validation works correctly: -30 <= value <= 40

### Large Maximum Values

**Example**: Some parameters have max=16777216 (2^24)

**Handling**:
- Python int has arbitrary precision
- No overflow concerns
- Validation logic unchanged

## Implementation Notes

1. **Immutability**: Parameter instances are frozen (immutable) to prevent accidental modification
2. **Type Safety**: Use type hints throughout for IDE support and mypy checking
3. **Performance**: Dict-based lookups provide O(1) access by both index and name
4. **Memory**: 400+ Parameter instances ~ few KB memory (negligible)
5. **Thread Safety**: Immutable data structures are inherently thread-safe for reads
6. **Protocol Fidelity**: Exact data preservation per Constitution Principle II

## Test Coverage Requirements

Per Constitution Principle IV, all described functionality must be tested:

### Unit Tests
- Parameter class creation and validation
- is_writable() for both read=0 and read=1
- validate_value() for valid, below min, above max, at boundaries
- HeatPump lookup methods (found, not found, KeyError)
- list_all_parameters() returns all in correct order

### Integration Tests
- Load all 400+ parameters successfully
- Verify indices match expected range
- Verify all lookups complete < 1 second

### Contract Tests
- **CRITICAL**: Parse FHEM Perl file and compare with Python data
- Verify parameter count matches
- Spot-check key parameters (idx=0, idx=1, last param)
- Verify no duplicate indices, names, or extids

## Future Extensions

This data model is foundational. Future features may add:

1. **Format-specific validation**: Interpret "temp" format for temperature ranges
2. **Unit conversion**: Add methods for Celsius/Fahrenheit conversion
3. **Grouping**: Categorize parameters by function (DHW, heating circuit, etc.)
4. **Change tracking**: Track which parameters have been modified
5. **Persistence**: Save/load parameter values from file

The current design supports these extensions without modification.

