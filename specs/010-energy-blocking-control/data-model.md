# Data Model: Energy Blocking Control

**Feature**: 010-energy-blocking-control
**Date**: 2025-12-06

## Entities

### 1. BlockingState

Represents the current blocking status for a single component.

| Field | Type | Description |
|-------|------|-------------|
| component | str | Component identifier: "compressor" or "aux_heater" |
| blocked | bool | True if component is currently blocked |
| source | str | Source of block: "user", "external", "system", or "none" |
| timestamp | float | Unix timestamp when status was read |

**Validation Rules**:
- `component` must be one of: "compressor", "aux_heater"
- `source` must be one of: "user", "external", "system", "none"
- `timestamp` must be positive

### 2. BlockingCommand

Represents a command to change blocking state.

| Field | Type | Description |
|-------|------|-------------|
| component | str | Component to block/unblock: "compressor" or "aux_heater" |
| action | str | Action to perform: "block" or "unblock" |

**Validation Rules**:
- `component` must be one of: "compressor", "aux_heater"
- `action` must be one of: "block", "unblock"

### 3. BlockingResult

Result of a blocking operation.

| Field | Type | Description |
|-------|------|-------------|
| success | bool | True if operation completed successfully |
| component | str | Component that was targeted |
| action | str | Action that was attempted |
| message | str | Human-readable result message |
| error | Optional[str] | Error details if success is False |

**Validation Rules**:
- `message` should be user-friendly
- `error` is only set when `success` is False

### 4. BlockingStatus

Aggregate status of all blocking controls.

| Field | Type | Description |
|-------|------|-------------|
| compressor | BlockingState | Compressor blocking status |
| aux_heater | BlockingState | Auxiliary heater blocking status |
| timestamp | float | Unix timestamp of status read |

## State Transitions

### Compressor Blocking

```
         ┌──────────────────┐
         │                  │
         ▼                  │
    ┌─────────┐       ┌─────────┐
    │  Normal │──────▶│ Blocked │
    │ (false) │ block │ (true)  │
    └─────────┘       └─────────┘
         ▲                  │
         │    unblock       │
         └──────────────────┘
```

### Auxiliary Heater Blocking

Same state machine as compressor.

## CAN Parameter Mapping

### Control Parameters (Write)

| Entity Field | CAN Parameter | idx |
|--------------|---------------|-----|
| aux_heater.blocked | ADDITIONAL_USER_BLOCKED | 155 |
| compressor.blocked | COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 | 263 |

### Status Parameters (Read)

| Entity Field | CAN Parameter | idx |
|--------------|---------------|-----|
| aux_heater.blocked (status) | ADDITIONAL_BLOCKED | 9 |
| compressor.blocked (status) | COMPRESSOR_BLOCKED | 247 |

## Value Encoding

| Logical Value | CAN Value | Notes |
|---------------|-----------|-------|
| False (unblocked) | 0x00 | 1 byte |
| True (blocked) | 0x01 | 1 byte |

## Error States

| Condition | Handling |
|-----------|----------|
| Communication timeout | Return BlockingResult with success=False, error describing timeout |
| Invalid parameter response | Return BlockingResult with success=False, error with raw data |
| Read-after-write mismatch | Return BlockingResult with success=False, warning about verification failure |
