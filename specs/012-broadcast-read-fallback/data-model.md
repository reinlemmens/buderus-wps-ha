# Data Model: CLI Broadcast Read Fallback

**Feature**: 012-broadcast-read-fallback
**Date**: 2025-12-06

## Entities

### ReadResult (Extended)

The read command result, extended to include data source information.

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| name | str | Parameter name (e.g., "GT2_TEMP") |
| idx | int | Parameter index in registry |
| extid | str | Extended ID from FHEM reference |
| format | str | Value format ("tem", "int", etc.) |
| min | int | Minimum valid value |
| max | int | Maximum valid value |
| read | int | Read flag (0=read-only via broadcast, 1=RTR readable) |
| raw | bytes | Raw bytes from device |
| decoded | Any | Decoded/formatted value |
| **source** | str | **NEW**: "rtr" or "broadcast" |

**JSON Representation**:
```json
{
  "name": "GT2_TEMP",
  "idx": 672,
  "extid": "0E7E9390E70063",
  "format": "tem",
  "min": 0,
  "max": 0,
  "read": 1,
  "raw": "0069",
  "decoded": 10.5,
  "source": "broadcast"
}
```

### BroadcastMapping

Maps standard parameter names to broadcast identification.

**Structure**:
```python
PARAM_TO_BROADCAST: Dict[str, Tuple[int, int]] = {
    # param_name: (base, idx)
    "GT2_TEMP": (0x0060, 12),      # Outdoor temperature
    "GT3_TEMP": (0x0060, 58),      # DHW temperature
    # ... additional mappings
}
```

**Lookup Logic**:
```python
def get_broadcast_for_param(param_name: str) -> Optional[Tuple[int, int]]:
    """Get broadcast (base, idx) for a parameter name."""
    return PARAM_TO_BROADCAST.get(param_name.upper())
```

### ReadSource (Enum-like)

Constants for data source indication.

| Value | Description |
|-------|-------------|
| "rtr" | Data obtained via RTR request/response |
| "broadcast" | Data obtained from CAN bus broadcast traffic |

## State Transitions

### Read Command Flow

```
[Start]
    │
    ▼
[Check --broadcast flag]
    │
    ├── Yes ──► [Broadcast Read] ──► [Return result with source="broadcast"]
    │
    └── No
        │
        ▼
    [RTR Read]
        │
        ▼
    [Check if valid response]
        │
        ├── Valid ──► [Return result with source="rtr"]
        │
        └── Invalid (1-byte temp)
            │
            ▼
        [Check --no-fallback flag]
            │
            ├── Yes ──► [Return invalid result with warning]
            │
            └── No
                │
                ▼
            [Broadcast Fallback]
                │
                ▼
            [Check if broadcast found]
                │
                ├── Found ──► [Return result with source="broadcast"]
                │
                └── Not found ──► [Return RTR result with warning]
```

## Validation Rules

### Temperature Parameter Detection

```python
def is_temperature_param(param: Parameter) -> bool:
    return param.format == "tem" or param.format.startswith("temp")
```

### Invalid RTR Response Detection

```python
def is_invalid_rtr_response(param: Parameter, raw: bytes) -> bool:
    """Check if RTR response indicates invalid/incomplete data."""
    if not is_temperature_param(param):
        return False
    # Temperature params should have 2+ bytes
    if len(raw) == 1:
        return True
    return False
```

### Broadcast Availability Check

```python
def has_broadcast_mapping(param_name: str) -> bool:
    """Check if parameter has known broadcast mapping."""
    return param_name.upper() in PARAM_TO_BROADCAST
```

## Relationships

```
Parameter (registry)
    │
    ├──► ReadResult (output)
    │       └── source: "rtr" | "broadcast"
    │
    └──► BroadcastMapping (lookup)
            └── (base, idx) → BroadcastReading
```

## Backward Compatibility

The `source` field is **additive** - existing consumers that don't use it will continue to work. The field is:
- Always present in JSON output
- Added to text output in parenthetical info
- Does not change the decoded value format
