# Data Model: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-12-18 (Updated)
**Status**: Complete

## Overview

This document defines the data model for representing Buderus WPS heat pump parameters in Python with dynamic discovery support. The model includes:
- Parameter entity with CAN ID calculation
- HeatPump container with discovery/cache/fallback support
- ParameterDiscovery for CAN bus protocol
- ParameterCache for persistence

## Entities

### 1. Parameter (Extended)

**Description**: Represents a single configurable or readable value on the Buderus WPS heat pump, with CAN ID calculation.

**Source**: Discovered from device via CAN bus OR fallback to `@KM273_elements_default` array

**Attributes**:

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| idx | int | Parameter index (CAN ID construction) | >= 0, may have gaps |
| extid | str | External ID | 14-character hex string |
| min | int | Minimum allowed value | Can be negative |
| max | int | Maximum allowed value | >= min |
| format | str | Data format type | Known: "int", "temp" |
| read | int | Read-only flag | 0 = writable, 1+ = read-only |
| text | str | Human-readable name | ALL_CAPS_WITH_UNDERSCORES |

**Methods** (Extended):

```python
def get_read_can_id(self) -> int:
    """
    Calculate CAN ID for read request.

    # PROTOCOL: Formula from fhem/26_KM273v018.pm:2229
    Returns: rtr = 0x04003FE0 | (idx << 14)
    """

def get_write_can_id(self) -> int:
    """
    Calculate CAN ID for write/response.

    # PROTOCOL: Formula from fhem/26_KM273v018.pm:2230
    Returns: txd = 0x0C003FE0 | (idx << 14)
    """

def is_writable(self) -> bool:
    """Check if parameter is writable (not read-only)."""

def validate_value(self, value: int) -> bool:
    """Check if value is within allowed min/max range."""
```

**CAN ID Calculation Examples**:

| idx | Read CAN ID | Write CAN ID | Calculation |
|-----|-------------|--------------|-------------|
| 0 | 0x04003FE0 | 0x0C003FE0 | Base IDs (no shift) |
| 1 | 0x04007FE0 | 0x0C007FE0 | 0x04003FE0 \| (1 << 14) |
| 100 | 0x041903E0 | 0x0C1903E0 | 0x04003FE0 \| (100 << 14) |

**Example Instances**:

```python
param = Parameter(
    idx=1,
    extid="61E1E1FC660023",
    min=0,
    max=5,
    format="int",
    read=0,
    text="ACCESS_LEVEL"
)

# CAN IDs calculated dynamically
assert param.get_read_can_id() == 0x04007FE0
assert param.get_write_can_id() == 0x0C007FE0
```

### 2. HeatPump (Extended)

**Description**: Container class providing access to all heat pump parameters with discovery, cache, and fallback support.

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| _params_by_idx | dict[int, Parameter] | O(1) lookup by idx |
| _params_by_name | dict[str, Parameter] | O(1) lookup by name |
| _source | str | Data source: 'cache', 'discovery', 'fallback' |

**Methods** (Extended):

```python
def __init__(self,
             adapter: CANAdapter | None = None,
             cache_path: Path | None = None,
             force_discovery: bool = False):
    """
    Initialize HeatPump with parameter loading strategy.

    Priority: cache → discovery → static fallback
    """

@property
def using_fallback(self) -> bool:
    """True if operating with static fallback data."""

@property
def data_source(self) -> str:
    """Return data source: 'cache', 'discovery', or 'fallback'."""

def get_parameter_by_index(self, idx: int) -> Parameter:
    """Get parameter by index. Raises KeyError if not found."""

def get_parameter_by_name(self, name: str) -> Parameter:
    """Get parameter by name. Raises KeyError if not found."""

def has_parameter_index(self, idx: int) -> bool:
    """Check if parameter index exists."""

def has_parameter_name(self, name: str) -> bool:
    """Check if parameter name exists."""

def list_all_parameters(self) -> list[Parameter]:
    """Return all parameters sorted by index."""

def list_writable_parameters(self) -> list[Parameter]:
    """Return only writable parameters sorted by index."""

def list_readonly_parameters(self) -> list[Parameter]:
    """Return only read-only parameters sorted by index."""

def parameter_count(self) -> int:
    """Return total number of parameters."""
```

**Usage Pattern**:

```python
# With discovery and caching
heat_pump = HeatPump(adapter=can_adapter, cache_path=Path("~/.cache/buderus/params.json"))

# Check data source
if heat_pump.using_fallback:
    logger.warning("Using fallback data - some parameters may not match device")

# Access parameter and calculate CAN ID
param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
can_id = param.get_read_can_id()
```

### 3. ParameterDiscovery (NEW)

**Description**: Implements the CAN bus discovery protocol to retrieve parameter definitions from the device.

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| _adapter | CANAdapter | CAN bus communication adapter |
| ELEMENT_COUNT_SEND | int | 0x01FD7FE0 |
| ELEMENT_COUNT_RECV | int | 0x09FD7FE0 |
| ELEMENT_DATA_SEND | int | 0x01FD3FE0 |
| ELEMENT_DATA_RECV | int | 0x09FDBFE0 |
| CHUNK_SIZE | int | 4096 |

**Methods**:

```python
def __init__(self, adapter: CANAdapter):
    """Initialize with CAN adapter."""

async def discover(self) -> list[dict]:
    """
    Execute full discovery protocol.

    Returns:
        List of parameter dicts with keys: idx, extid, min, max, format, read, text

    Raises:
        DiscoveryError: On timeout or protocol error
    """

async def _request_element_count(self) -> int:
    """Request element count from device."""

async def _request_element_chunk(self, offset: int, length: int) -> bytes:
    """Request chunk of element data."""

@staticmethod
def parse_element(data: bytes, offset: int) -> tuple[dict | None, int]:
    """
    Parse single element from binary data.

    # PROTOCOL: Binary structure from fhem/26_KM273v018.pm:2135-2143

    Returns:
        (element_dict, next_offset) or (None, -1) on error
    """
```

**Binary Element Structure**:

```
Offset  Size  Field    Type        Notes
0       2     idx      uint16 LE   Parameter index
2       7     extid    hex string  External ID (7 bytes → 14 hex chars)
9       4     max      int32 LE    Maximum value
13      4     min      int32 LE    Minimum value
17      1     len      uint8       Name length
18      N     name     ASCII       Parameter name (len-1 bytes, null-terminated)
```

### 4. ParameterCache (NEW)

**Description**: Manages persistent cache of discovered parameters.

**Cache File Structure**:

```json
{
  "version": "1.0.0",
  "created": "2025-12-18T10:30:00Z",
  "device_id": "BUDERUS_WPS_SN12345",
  "firmware": "v1.23",
  "checksum": "sha256:abc123...",
  "element_count": 1789,
  "parameters": [
    {"idx": 0, "extid": "814A53C66A0802", "min": 0, "max": 0, ...},
    ...
  ]
}
```

**Methods**:

```python
def __init__(self, cache_path: Path):
    """Initialize with cache file path."""

def is_valid(self) -> bool:
    """Check if cache exists and is valid (checksum, version)."""

def load(self) -> list[dict] | None:
    """
    Load parameters from cache.

    Returns:
        List of parameter dicts or None if cache invalid
    """

def save(self, parameters: list[dict], device_id: str | None = None,
         firmware: str | None = None) -> bool:
    """
    Save parameters to cache.

    Returns:
        True if save successful
    """

def invalidate(self) -> None:
    """Remove cache file."""

@staticmethod
def _compute_checksum(parameters: list[dict]) -> str:
    """Compute SHA256 checksum of parameters."""
```

## Relationships

```
┌─────────────────────┐
│      HeatPump       │
│                     │
│ _source: str        │
│ _params_by_idx: {}  │
│ _params_by_name: {} │
│                     │
│ using_fallback      │
│ data_source         │
└────────┬────────────┘
         │
         │ loads from one of:
         │
    ┌────┴────┬────────────┐
    ▼         ▼            ▼
┌───────┐ ┌────────┐ ┌──────────────┐
│ Cache │ │ Disc.  │ │ Static Data  │
│       │ │        │ │              │
│ JSON  │ │ CAN    │ │ parameter_   │
│ file  │ │ bus    │ │ data.py      │
└───────┘ └────────┘ └──────────────┘
    │         │            │
    │         │            │
    └────┬────┴────────────┘
         │
         │ creates
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
    │             │
    │ get_read_can_id()  │
    │ get_write_can_id() │
    └─────────────┘
```

**Relationships**:
- **HeatPump contains many Parameters**: 1:N relationship
- **HeatPump uses ParameterCache**: 1:1 optional dependency
- **HeatPump uses ParameterDiscovery**: 1:1 optional dependency
- **Parameters are independent**: No inter-parameter relationships
- **Cache stores serialized Parameters**: Persistence layer

## Data Sources

### Primary: Device Discovery

**Protocol**: CAN bus messages using fixed discovery CAN IDs

| Purpose | Send CAN ID | Receive CAN ID |
|---------|-------------|----------------|
| Element count | 0x01FD7FE0 | 0x09FD7FE0 |
| Element data | 0x01FD3FE0 | 0x09FDBFE0 |
| Buffer read | 0x01FDBFE0 | - |

### Secondary: Cache

**Location**: User-configurable, default `~/.cache/buderus/params.json`

**Validation**:
1. File exists and is valid JSON
2. Version matches library version
3. SHA256 checksum validates integrity
4. Device ID matches (if available)

### Tertiary: Static Fallback

**Source**: `buderus_wps/parameter_data.py` - `PARAMETER_DATA` constant

**Content**: 1789 parameters from `fhem/26_KM273v018.pm:218-2009`

## Validation Rules

### Parameter Validation

1. **Index uniqueness**: Each idx value appears exactly once
2. **Name uniqueness**: Each text value appears exactly once
3. **ExtID uniqueness**: Each extid value appears exactly once
4. **Range relationship**: For most parameters max >= min (some FHEM data has bugs)
5. **Read flag values**: read is 0 (writable) or 1+ (read-only)
6. **Text format**: text uses ALL_CAPS_WITH_UNDERSCORES convention

### CAN ID Validation

1. **Formula correctness**: CAN IDs match FHEM formulas exactly
2. **Range bounds**: Read CAN IDs in 0x04003FE0-0x04FFFFFF
3. **Range bounds**: Write CAN IDs in 0x0C003FE0-0x0CFFFFFF

### Cache Validation

1. **JSON structure**: Valid JSON with required fields
2. **Version compatibility**: version field matches library
3. **Data integrity**: checksum validates parameters array
4. **Freshness**: Optional device_id/firmware match

## Edge Cases

### Non-Sequential Indices
- idx sequence has gaps (e.g., 13 missing between 12 and 14)
- Dict-based lookup handles naturally
- get_parameter_by_index(13) raises KeyError

### Discovery Timeout
- Element count timeout → fallback
- Data chunk timeout → partial data discarded → fallback
- Network interruption → DiscoveryError → fallback

### Cache Corruption
- Invalid JSON → cache invalidated → discovery
- Checksum mismatch → cache invalidated → discovery
- Version mismatch → cache invalidated → discovery

### Binary Parsing Errors
- Truncated element → skip, continue parsing
- Invalid name length → skip element
- Zero-length name → use placeholder

## Implementation Notes

1. **Immutability**: Parameter instances are frozen (dataclass)
2. **Async Discovery**: Non-blocking for Home Assistant compatibility
3. **Type Safety**: Full type hints for mypy checking
4. **Performance**: O(1) lookups, <30s discovery, <3s cache load
5. **Thread Safety**: Immutable Parameters + single-threaded discovery
6. **Protocol Fidelity**: Exact FHEM formula replication

## Test Coverage Requirements

### Unit Tests
- Parameter CAN ID calculation (idx=0, 1, 100, max)
- Binary element parsing (valid, malformed, truncated)
- Cache JSON serialization/deserialization
- Checksum computation and validation

### Contract Tests
- **CRITICAL**: CAN ID formulas match FHEM reference
- Binary structure matches FHEM parsing
- Static fallback data matches FHEM array

### Integration Tests
- Discovery flow with mock adapter
- Cache save/load cycle
- Fallback triggering on errors

### Acceptance Tests
- User Story 0: Discovery scenarios
- User Story 4: Caching scenarios
