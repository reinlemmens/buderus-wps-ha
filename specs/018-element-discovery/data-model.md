# Data Model: Element Discovery Protocol

**Date**: 2026-01-10
**Feature**: 018-element-discovery

## Entities

### DiscoveredElement

Represents a parameter element retrieved from the heat pump via discovery protocol.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| idx | int | Parameter index for CAN ID calculation | 0-4095 |
| extid | str | External ID (14 hex chars) | Matches `[0-9A-F]{14}` |
| text | str | Parameter name | ASCII, uppercase with underscores |
| min_value | int | Minimum allowed value | Signed 32-bit |
| max_value | int | Maximum allowed value | Signed 32-bit |

**Derived Properties**:
- `can_id`: Calculated as `0x04003FE0 | (idx << 14)`

---

### Parameter (existing, modified)

Represents a parameter in the registry with metadata from static defaults and optional discovery updates.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| idx | int | Discovery/Cache | Parameter index - MUST come from discovery |
| extid | str | Discovery/Cache | External ID |
| text | str | Static | Parameter name |
| min | int | Discovery/Cache | Minimum value |
| max | int | Discovery/Cache | Maximum value |
| format | str | Static | Data format (tem, int, sw1, etc.) |
| read | int | Static | Read-only flag (0=writable, 1=read-only) |

**Note**: `idx`, `extid`, `min`, `max` should come from discovery/cache. `format` and `read` come from static defaults because discovery doesn't provide them.

---

### HeatPump (existing, modified)

Parameter registry container with discovery tracking.

| Field | Type | Description |
|-------|------|-------------|
| _params_by_name | Dict[str, Parameter] | Lookup by parameter name |
| _params_by_idx | Dict[int, Parameter] | Lookup by parameter index |
| _discovered_names | Set[str] | **NEW**: Names of parameters with discovered/cached idx |
| _data_source | str | Source: "discovery", "cache", or "fallback" |

**Methods**:
- `is_discovered(name: str) -> bool`: Check if parameter has discovered idx
- `get_parameter(name: str) -> Parameter`: Returns parameter or raises if not discovered

---

### DiscoveryCache (JSON format)

Persistent storage for discovered elements.

```json
{
  "version": 2,
  "timestamp": "2026-01-10T12:00:00Z",
  "timestamp_unix": 1736510400.0,
  "reported_bytes": 85000,
  "actual_bytes": 84500,
  "complete": true,
  "elements": [
    {
      "idx": 682,
      "extid": "0EB5CF43420068",
      "text": "GT3_TEMP",
      "min_value": 0,
      "max_value": 0
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| version | int | Cache format version (currently 2) |
| timestamp | str | ISO 8601 timestamp |
| timestamp_unix | float | Unix timestamp for age comparison |
| reported_bytes | int | Bytes reported by heat pump |
| actual_bytes | int | Bytes actually received |
| complete | bool | Whether discovery was complete (>=95%) |
| elements | list | Array of discovered elements |

---

## State Transitions

### Discovery State Machine

```
                    ┌─────────────┐
                    │   STARTUP   │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌─────────────────┐      ┌─────────────────┐
    │  Cache Exists?  │──No──│  Fresh Install  │
    └────────┬────────┘      └────────┬────────┘
             │ Yes                     │
             ▼                         ▼
    ┌─────────────────┐      ┌─────────────────┐
    │   Check Age     │      │  Run Discovery  │
    └────────┬────────┘      └────────┬────────┘
             │                         │
    ┌────────┴────────┐      ┌────────┴────────┐
    │                 │      │                 │
    ▼                 ▼      ▼                 ▼
  Fresh           Expired  Success          Failure
    │                 │      │                 │
    ▼                 ▼      ▼                 ▼
┌────────┐    ┌────────┐  ┌────────┐   ┌─────────────┐
│Load    │    │Run     │  │Update  │   │ERROR:       │
│Cache   │    │Discovery│ │Cache   │   │DiscoveryReq │
└────────┘    └────────┘  └────────┘   └─────────────┘
```

### Parameter Availability States

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| Discovered | idx from current discovery | Read, Write |
| Cached | idx from previous successful discovery | Read, Write |
| Static Only | idx only in static defaults | **NONE** (unavailable) |

---

## Validation Rules

1. **Cache Completeness**: Cache is valid only if `complete == true`
2. **Cache Age**: Cache expires after 24 hours (configurable)
3. **Discovery Threshold**: Require ≥95% of reported bytes for success
4. **Parameter Access**: Only allow operations on discovered/cached parameters
5. **Name Matching**: Case-insensitive parameter name lookup
