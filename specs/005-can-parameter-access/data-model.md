# Data Model: CAN Bus Parameter Read/Write Access

**Feature**: 005-can-parameter-access
**Date**: 2025-10-24
**Status**: Phase 1 Design

This document defines the core data structures, entities, and their relationships for parameter read/write operations.

---

## Core Entities

### 1. Parameter

Represents a single heat pump parameter with metadata.

**Attributes**:
```python
@dataclass(frozen=True)
class Parameter:
    """
    Immutable parameter definition with metadata.

    Loaded once at startup from Feature 002 (elements.py).
    Thread-safe due to immutability.
    """
    idx: int                    # Sequential index (1-1789)
    extid: int                  # Extended CAN identifier (hex address)
    text: str                   # Human-readable name (UPPERCASE)
    min_value: int | float      # Minimum allowed value
    max_value: int | float      # Maximum allowed value
    format: str                 # Data format type (int, temp, etc.)
    writable: bool              # True if parameter can be written
    unit: str | None = None     # Physical unit (°C, bar, %, etc.)
    description: str | None = None  # Human-readable description

    def validate_value(self, value: Any) -> bool:
        """Check if value is within allowed range."""
        try:
            numeric_value = float(value)
            return self.min_value <= numeric_value <= self.max_value
        except (ValueError, TypeError):
            return False

    def is_read_only(self) -> bool:
        """Check if parameter is read-only."""
        return not self.writable or (self.min_value == 0 and self.max_value == 0)
```

**Identity**:
- **Primary key**: `text` (uppercase parameter name)
- **Secondary key**: `idx` (sequential index)
- **Unique constraint**: `extid` (CAN address)

**Lifecycle**:
- **Creation**: Loaded once at application startup from Feature 002
- **Immutable**: No modification after load (frozen dataclass)
- **Lookup**: By `text` (case-insensitive input, normalized to uppercase)

**Validation Rules**:
- `text` must be non-empty, alphanumeric + underscores only
- `extid` must be valid CAN identifier (0x00000000 to 0x1FFFFFFF)
- `min_value <= max_value`
- If `min_value == max_value == 0`, parameter is read-only flag/status

---

### 2. ParameterRegistry

Registry for fast parameter lookup by name.

**Attributes**:
```python
class ParameterRegistry:
    """
    Case-insensitive parameter lookup registry.

    Performance: ~1 microsecond per lookup
    Memory: ~600KB for 1,789 parameters
    Thread-safe: Yes (read-only after init)
    """
    _params: dict[str, Parameter]      # Private mutable dict
    params: MappingProxyType           # Public immutable view

    def __init__(self, parameters: list[Parameter]):
        """
        Initialize registry with parameter list.

        Args:
            parameters: List of Parameter objects from Feature 002

        Raises:
            ValueError: If duplicate parameter names exist
        """
        self._params = {}
        for param in parameters:
            key = param.text.upper()
            if key in self._params:
                raise ValueError(f"Duplicate parameter name: {key}")
            self._params[key] = param

        # Create immutable view
        self.params = MappingProxyType(self._params)

    def get(self, name: str, default: Parameter | None = None) -> Parameter | None:
        """Get parameter by name (case-insensitive)."""
        return self.params.get(name.upper(), default)

    def __getitem__(self, name: str) -> Parameter:
        """Dict-like access (raises KeyError if not found)."""
        key = name.upper()
        if key not in self.params:
            raise KeyError(f"Parameter '{name}' not found")
        return self.params[key]

    def __contains__(self, name: str) -> bool:
        """Check if parameter exists (case-insensitive)."""
        return name.upper() in self.params

    def __len__(self) -> int:
        """Return total number of parameters."""
        return len(self.params)

    def list_all(self, writable_only: bool = False) -> list[Parameter]:
        """
        Get list of all parameters.

        Args:
            writable_only: If True, return only writable parameters

        Returns:
            List of parameters, sorted by name
        """
        params = list(self.params.values())
        if writable_only:
            params = [p for p in params if p.writable and not p.is_read_only()]
        return sorted(params, key=lambda p: p.text)
```

**Relationships**:
- **Contains**: 1,789 Parameter objects
- **Indexed by**: Uppercase parameter name (text)
- **Used by**: ParameterAccessor, CLI commands

---

### 3. ParameterValue

Represents a parameter value with metadata at a specific point in time.

**Attributes**:
```python
@dataclass
class ParameterValue:
    """
    Parameter value read from or written to device.

    Captures both the raw CAN value and human-readable representation.
    """
    parameter: Parameter        # Parameter definition
    raw_value: bytes            # Raw CAN response data
    value: int | float | str    # Converted human-readable value
    timestamp: datetime         # When value was read/written
    operation: str              # 'read' or 'write'

    def format_human(self) -> str:
        """Format value for human-readable output."""
        unit_str = f" {self.parameter.unit}" if self.parameter.unit else ""
        return f"{self.parameter.text}: {self.value}{unit_str}"

    def format_json(self) -> dict:
        """Format value for JSON output."""
        return {
            "operation": self.operation,
            "parameter": self.parameter.text,
            "value": self.value,
            "unit": self.parameter.unit,
            "metadata": {
                "min": self.parameter.min_value,
                "max": self.parameter.max_value,
                "writable": self.parameter.writable,
                "type": self.parameter.format,
            },
            "timestamp": self.timestamp.isoformat() + "Z",
            "status": "success"
        }
```

**Lifecycle**:
- **Creation**: After successful CAN read or write operation
- **Ephemeral**: Not persisted (out of scope per spec)
- **Usage**: Formatted for CLI output, then discarded

---

### 4. ParameterAccessor

Service class for parameter read/write operations.

**Attributes**:
```python
class ParameterAccessor:
    """
    High-level interface for parameter read/write operations.

    Orchestrates:
    - Parameter lookup and validation
    - CAN communication (via Feature 001)
    - Value conversion
    - Error handling
    - Logging
    """
    registry: ParameterRegistry      # Parameter metadata registry
    can_interface: CANInterface      # CAN communication (Feature 001)
    logger: logging.Logger           # Logger instance
    timeout: float = 5.0             # Device response timeout (seconds)

    def read_parameter(self, name: str) -> ParameterValue:
        """
        Read parameter value from device.

        Args:
            name: Parameter name (case-insensitive)

        Returns:
            ParameterValue with current value

        Raises:
            ParameterNotFoundError: Parameter doesn't exist
            CANBusError: CAN communication failure
            TimeoutError: Device didn't respond within timeout
        """
        # 1. Lookup parameter (with case normalization)
        # 2. Send CAN read request via Feature 001
        # 3. Wait for response (5-second timeout)
        # 4. Convert raw bytes to human value
        # 5. Return ParameterValue
        pass

    def write_parameter(self, name: str, value: Any) -> ParameterValue:
        """
        Write parameter value to device.

        Args:
            name: Parameter name (case-insensitive)
            value: New value to write

        Returns:
            ParameterValue with new value

        Raises:
            ParameterNotFoundError: Parameter doesn't exist
            ParameterReadOnlyError: Parameter is read-only
            ValidationError: Value outside allowed range
            CANBusError: CAN communication failure
            TimeoutError: Device didn't respond within timeout
        """
        # 1. Lookup parameter
        # 2. Validate value against min/max
        # 3. Check parameter is writable
        # 4. Convert human value to raw bytes
        # 5. Send CAN write request via Feature 001
        # 6. Wait for confirmation (5-second timeout)
        # 7. Read back value to confirm
        # 8. Return ParameterValue
        pass
```

**Dependencies**:
- **ParameterRegistry**: For parameter lookup
- **CANInterface** (Feature 001): For CAN communication
- **logging**: For operation logging

---

### 5. CLI Command Context

Context object passed to CLI command handlers.

**Attributes**:
```python
@dataclass
class CLIContext:
    """
    Execution context for CLI commands.

    Created once at CLI entry point, passed to all commands.
    """
    accessor: ParameterAccessor      # Parameter operations service
    output_format: str               # 'human' or 'json'
    verbose: bool                    # Debug logging enabled
    timeout: float                   # Operation timeout (seconds)

    def format_output(self, value: ParameterValue) -> str:
        """Format value according to output_format."""
        if self.output_format == 'json':
            return json.dumps(value.format_json(), indent=2)
        else:
            return value.format_human()

    def format_error(self, error: Exception, parameter: str | None = None) -> str:
        """Format error message according to output_format."""
        if self.output_format == 'json':
            return json.dumps({
                "status": "error",
                "error_type": type(error).__name__,
                "message": str(error),
                "parameter": parameter,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, indent=2)
        else:
            return f"Error: {error}"
```

---

## Exception Hierarchy

Custom exceptions for domain-specific errors.

```python
class ParameterError(Exception):
    """Base exception for parameter operations."""
    exit_code: int = 1

class ParameterNotFoundError(ParameterError):
    """Parameter name doesn't exist in registry."""
    exit_code: int = 3

class ParameterReadOnlyError(ParameterError):
    """Attempted write to read-only parameter."""
    exit_code: int = 4

class ValidationError(ParameterError):
    """Value outside allowed range."""
    exit_code: int = 5

class CANBusError(ParameterError):
    """CAN bus communication failure."""
    exit_code: int = 6

class TimeoutError(ParameterError):
    """Device didn't respond within timeout."""
    exit_code: int = 7

class DeviceError(ParameterError):
    """Device returned error response."""
    exit_code: int = 8
```

---

## Data Flow Diagrams

### Read Operation Flow

```
User: buderus-wps get DHW_TEMP_SETPOINT
  │
  ├──> CLI Parser (argparse)
  │      └──> Validates command syntax
  │
  ├──> cmd_get(args, context)
  │      ├──> Normalizes parameter name: "DHW_TEMP_SETPOINT"
  │      └──> Calls accessor.read_parameter("DHW_TEMP_SETPOINT")
  │
  ├──> ParameterAccessor.read_parameter()
  │      ├──> Registry lookup: registry.get("DHW_TEMP_SETPOINT")
  │      │      └──> Returns Parameter(idx=123, extid=0x31D011E9, ...)
  │      │
  │      ├──> Log: DEBUG "Reading parameter: DHW_TEMP_SETPOINT"
  │      │
  │      ├──> CAN request: can_interface.send_request(0x31D011E9, [0x01], timeout=5.0)
  │      │      └──> Feature 001: Sends CAN message to device
  │      │
  │      ├──> Wait for response (5-second timeout)
  │      │      └──> Receives: bytes([0x00, 0x2D])
  │      │
  │      ├──> Convert raw to value: bytes_to_value([0x00, 0x2D], format='temp')
  │      │      └──> Returns: 45.0
  │      │
  │      └──> Create ParameterValue(parameter, raw, value=45.0, timestamp, operation='read')
  │
  ├──> context.format_output(param_value)
  │      └──> Returns: "DHW_TEMP_SETPOINT: 45.0°C" (human mode)
  │
  └──> Print to stdout, exit code 0
```

### Write Operation Flow

```
User: buderus-wps set DHW_TEMP_SETPOINT 55
  │
  ├──> CLI Parser (argparse)
  │
  ├──> cmd_set(args, context)
  │      └──> Calls accessor.write_parameter("DHW_TEMP_SETPOINT", "55")
  │
  ├──> ParameterAccessor.write_parameter()
  │      ├──> Registry lookup: registry.get("DHW_TEMP_SETPOINT")
  │      │      └──> Returns Parameter(min=40, max=70, writable=True, ...)
  │      │
  │      ├──> Validate value: 40 <= 55 <= 70 ✓
  │      ├──> Check writable: writable=True ✓
  │      │
  │      ├──> Convert value to bytes: value_to_bytes(55, format='temp')
  │      │      └──> Returns: bytes([0x00, 0x37])
  │      │
  │      ├──> CAN write request: can_interface.send_write(0x31D011E9, [0x00, 0x37], timeout=5.0)
  │      │      └──> Feature 001: Sends CAN write message
  │      │
  │      ├──> Wait for write confirmation (5-second timeout)
  │      │
  │      ├──> Read back value: accessor.read_parameter("DHW_TEMP_SETPOINT")
  │      │      └──> Confirms: 55.0
  │      │
  │      └──> Create ParameterValue(..., value=55.0, operation='write')
  │
  ├──> context.format_output(param_value)
  │      └──> Returns: "✓ Successfully set DHW_TEMP_SETPOINT to 55.0°C"
  │
  └──> Print to stdout, exit code 0
```

---

## Relationships Between Entities

```
ParameterRegistry
    │
    ├──> Contains: 1..* Parameter (immutable)
    │              Key: text (uppercase)
    │
    └──> Used by: ParameterAccessor

ParameterAccessor
    │
    ├──> Uses: ParameterRegistry (lookup)
    ├──> Uses: CANInterface (Feature 001, communication)
    ├──> Creates: ParameterValue (ephemeral)
    │
    └──> Used by: CLI commands

Parameter
    │
    ├──> Loaded from: Feature 002 (elements.py)
    ├──> Immutable after load
    │
    └──> Referenced by: ParameterValue

ParameterValue
    │
    ├──> References: Parameter (metadata)
    ├──> Contains: raw_value (bytes), value (human), timestamp
    ├──> Ephemeral: Not persisted
    │
    └──> Used by: CLI formatters

CLIContext
    │
    ├──> Contains: ParameterAccessor (operations)
    ├──> Contains: Configuration (format, verbose, timeout)
    │
    └──> Passed to: All CLI commands
```

---

## State Transitions

### Parameter Lifecycle

```
┌─────────────────┐
│  Load from      │
│  Feature 002    │
│  (startup)      │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  In Registry    │  ◄───── Immutable, never changes
│  (ready for     │
│   lookup)       │
└─────────────────┘
         │
         │ (no state changes - immutable)
         │
         v
    (app exit, memory freed)
```

### Parameter Value Lifecycle (Read Operation)

```
┌──────────────────┐
│  User Request    │
│  (CLI command)   │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Lookup in       │
│  Registry        │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  CAN Request     │
│  (Feature 001)   │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Wait Response   │
│  (5s timeout)    │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  ParameterValue  │
│  Created         │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Formatted &     │
│  Displayed       │
└────────┬─────────┘
         │
         v
    (object discarded)
```

### Parameter Value Lifecycle (Write Operation)

```
┌──────────────────┐
│  User Request    │
│  (set command)   │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Lookup & Validate│
│  (registry)      │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Check Writable  │──> NO ──> ParameterReadOnlyError (exit 4)
└────────┬─────────┘
         │ YES
         v
┌──────────────────┐
│  Validate Range  │──> FAIL ──> ValidationError (exit 5)
└────────┬─────────┘
         │ PASS
         v
┌──────────────────┐
│  CAN Write Req   │
│  (Feature 001)   │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Wait Confirm    │──> TIMEOUT ──> TimeoutError (exit 7)
│  (5s timeout)    │
└────────┬─────────┘
         │ SUCCESS
         v
┌──────────────────┐
│  Read Back       │
│  (confirmation)  │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  ParameterValue  │
│  Created         │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Formatted &     │
│  Displayed       │
└────────┬─────────┘
         │
         v
    (object discarded)
```

---

## Data Persistence

**In-Scope** (Memory Only):
- ParameterRegistry: Loaded once at startup, kept in memory
- Parameter definitions: Immutable in memory
- ParameterValue: Ephemeral, created and discarded per operation

**Out-of-Scope** (Explicitly Excluded in spec.md):
- Historical parameter values
- Parameter change logs
- Value caching
- Parameter subscriptions/monitoring

---

## Validation Rules Summary

| Entity | Validation | When | Error |
|--------|-----------|------|-------|
| Parameter.text | Non-empty, alphanumeric + underscore | Load time | ValueError |
| Parameter.extid | Valid CAN ID (0x0 - 0x1FFFFFFF) | Load time | ValueError |
| Parameter.min/max | min <= max | Load time | ValueError |
| ParameterValue | Value within min/max range | Write time | ValidationError (exit 5) |
| ParameterValue | Parameter is writable | Write time | ParameterReadOnlyError (exit 4) |
| Parameter name | Exists in registry | Lookup time | ParameterNotFoundError (exit 3) |

---

## Memory Footprint Estimates

| Component | Count | Size Each | Total |
|-----------|-------|-----------|-------|
| Parameter objects | 1,789 | ~200 bytes | ~360KB |
| Registry dict overhead | 1 | ~200KB | ~200KB |
| String interning (names) | 1,789 | ~20 bytes | ~36KB |
| **Total (registry)** | | | **~600KB** |
| ParameterAccessor | 1 | ~1KB | ~1KB |
| ParameterValue (temp) | 1 | ~500 bytes | ~500B |

**Total runtime memory**: <1MB for all parameter access functionality.

---

## Thread Safety Analysis

| Component | Thread-Safe? | Mechanism |
|-----------|-------------|-----------|
| Parameter | ✅ Yes | Immutable (frozen dataclass) |
| ParameterRegistry | ✅ Yes | MappingProxyType (read-only view) |
| ParameterAccessor | ❌ No | Uses CAN interface (not thread-safe) |
| ParameterValue | ⚠️ Mutable | Not designed for sharing |

**Conclusion**: Per spec requirements (single-threaded sequential usage), thread safety is not guaranteed. Concurrent calls result in undefined behavior.

---

## Data Model Validation

This data model satisfies all functional requirements:

- ✅ **FR-001**: Parameter lookup by human-readable name (ParameterRegistry)
- ✅ **FR-002**: Write support with metadata (ParameterAccessor.write_parameter)
- ✅ **FR-003**: Validation against min/max (Parameter.validate_value)
- ✅ **FR-004**: Read-only enforcement (Parameter.is_read_only)
- ✅ **FR-005**: Name-to-extid mapping (Parameter.extid)
- ✅ **FR-006**: Data format conversion (ParameterAccessor)
- ✅ **FR-007**: Clear error messages (Exception hierarchy with context)
- ✅ **NFR-005**: Lookup performance <100ms (dict lookup ~1µs)

**Phase 1 Data Model Status**: ✅ COMPLETE
