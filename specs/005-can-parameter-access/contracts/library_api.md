# Library API Contract

**Feature**: 005-can-parameter-access
**Component**: `buderus_wps` Python library
**Version**: 1.0.0
**Date**: 2025-10-24

This document defines the public API contract for the parameter access library.

---

## Module: `buderus_wps.parameter_access`

### Class: `ParameterAccessor`

Primary interface for parameter read/write operations.

#### Constructor

```python
def __init__(
    self,
    registry: ParameterRegistry,
    can_interface: CANInterface,
    timeout: float = 5.0,
    logger: logging.Logger | None = None
) -> None:
    """
    Initialize parameter accessor.

    Args:
        registry: Parameter registry for metadata lookup
        can_interface: CAN communication interface (Feature 001)
        timeout: Default timeout for device operations in seconds (default: 5.0)
        logger: Logger instance (creates new if None)

    Raises:
        ValueError: If timeout <= 0
    """
```

#### Method: `read_parameter`

```python
def read_parameter(
    self,
    name: str,
    timeout: float | None = None
) -> ParameterValue:
    """
    Read parameter value from device.

    Args:
        name: Parameter name (case-insensitive, normalized to uppercase)
        timeout: Override default timeout in seconds (optional)

    Returns:
        ParameterValue with current value, metadata, and timestamp

    Raises:
        ParameterNotFoundError: Parameter name doesn't exist (exit code 3)
        CANBusError: CAN bus not connected or communication failure (exit code 6)
        TimeoutError: Device didn't respond within timeout (exit code 7)
        DeviceError: Device returned error response (exit code 8)

    Performance:
        - Parameter lookup: <1ms
        - Total operation: <2 seconds under normal conditions
        - Timeout enforced: 5 seconds (default)

    Example:
        >>> accessor = ParameterAccessor(registry, can_interface)
        >>> value = accessor.read_parameter("DHW_TEMP_SETPOINT")
        >>> print(value.value)  # 55.0
        >>> print(value.parameter.unit)  # "°C"
    """
```

#### Method: `write_parameter`

```python
def write_parameter(
    self,
    name: str,
    value: int | float | str,
    timeout: float | None = None
) -> ParameterValue:
    """
    Write parameter value to device.

    Args:
        name: Parameter name (case-insensitive, normalized to uppercase)
        value: New value to write (converted to appropriate type)
        timeout: Override default timeout in seconds (optional)

    Returns:
        ParameterValue with new value (confirmed by read-back)

    Raises:
        ParameterNotFoundError: Parameter name doesn't exist (exit code 3)
        ParameterReadOnlyError: Parameter is read-only (exit code 4)
        ValidationError: Value outside allowed min/max range (exit code 5)
        CANBusError: CAN bus not connected or communication failure (exit code 6)
        TimeoutError: Device didn't respond within timeout (exit code 7)
        DeviceError: Device returned error response (exit code 8)

    Behavior:
        - Validates value against parameter min/max before sending
        - Checks parameter is writable (not read-only)
        - Sends CAN write command via Feature 001
        - Waits for write confirmation
        - Reads back value to confirm write succeeded
        - Returns ParameterValue with confirmed new value

    Performance:
        - Parameter lookup: <1ms
        - Total operation: <3 seconds under normal conditions
        - Timeout enforced: 5 seconds (default)

    Example:
        >>> accessor = ParameterAccessor(registry, can_interface)
        >>> value = accessor.write_parameter("DHW_TEMP_SETPOINT", 55)
        >>> print(value.value)  # 55.0
        >>> print(value.operation)  # "write"
    """
```

---

## Module: `buderus_wps.registry`

### Class: `ParameterRegistry`

Fast case-insensitive parameter lookup.

#### Constructor

```python
def __init__(self, parameters: list[Parameter]) -> None:
    """
    Initialize parameter registry.

    Args:
        parameters: List of Parameter objects (from Feature 002)

    Raises:
        ValueError: If duplicate parameter names found

    Performance:
        - Initialization: O(n) where n = parameter count (~1,789)
        - Memory: ~600KB for 1,789 parameters
    """
```

#### Method: `get`

```python
def get(self, name: str, default: Parameter | None = None) -> Parameter | None:
    """
    Get parameter by name (case-insensitive).

    Args:
        name: Parameter name (case-insensitive)
        default: Default value if not found

    Returns:
        Parameter object or default if not found

    Performance:
        - Lookup time: ~1 microsecond
        - Case normalization: ~50 nanoseconds

    Example:
        >>> param = registry.get("dhw_temp_setpoint")  # lowercase input
        >>> print(param.text)  # "DHW_TEMP_SETPOINT" (uppercase output)
    """
```

#### Method: `__getitem__`

```python
def __getitem__(self, name: str) -> Parameter:
    """
    Dict-like parameter access.

    Args:
        name: Parameter name (case-insensitive)

    Returns:
        Parameter object

    Raises:
        KeyError: If parameter not found

    Example:
        >>> param = registry["DHW_TEMP_SETPOINT"]
        >>> print(param.extid)  # 0x31D011E9
    """
```

#### Method: `__contains__`

```python
def __contains__(self, name: str) -> bool:
    """
    Check if parameter exists (case-insensitive).

    Args:
        name: Parameter name (case-insensitive)

    Returns:
        True if parameter exists, False otherwise

    Example:
        >>> if "DHW_TEMP_SETPOINT" in registry:
        ...     print("Found")
    """
```

#### Method: `list_all`

```python
def list_all(self, writable_only: bool = False) -> list[Parameter]:
    """
    Get list of all parameters.

    Args:
        writable_only: If True, return only writable parameters

    Returns:
        List of parameters sorted by name (uppercase)

    Example:
        >>> all_params = registry.list_all()
        >>> len(all_params)  # 1789
        >>> writable = registry.list_all(writable_only=True)
        >>> len(writable)  # ~800 (estimate)
    """
```

---

## Module: `buderus_wps.models`

### Dataclass: `Parameter`

Immutable parameter definition.

```python
@dataclass(frozen=True)
class Parameter:
    """Parameter metadata (immutable)."""
    idx: int                    # Sequential index (1-1789)
    extid: int                  # CAN extended identifier (hex)
    text: str                   # Parameter name (UPPERCASE)
    min_value: int | float      # Minimum allowed value
    max_value: int | float      # Maximum allowed value
    format: str                 # Data format type
    writable: bool              # True if can be written
    unit: str | None = None     # Physical unit (e.g., "°C")
    description: str | None = None  # Human description

    def validate_value(self, value: Any) -> bool:
        """Check if value within allowed range."""
        pass

    def is_read_only(self) -> bool:
        """Check if parameter is read-only."""
        pass
```

### Dataclass: `ParameterValue`

Parameter value at a point in time.

```python
@dataclass
class ParameterValue:
    """Parameter value with metadata."""
    parameter: Parameter        # Parameter definition
    raw_value: bytes            # Raw CAN data
    value: int | float | str    # Human-readable value
    timestamp: datetime         # When read/written
    operation: str              # 'read' or 'write'

    def format_human(self) -> str:
        """Format for human display."""
        pass

    def format_json(self) -> dict:
        """Format as JSON object."""
        pass
```

---

## Module: `buderus_wps.exceptions`

### Exception Hierarchy

```python
class ParameterError(Exception):
    """Base exception for parameter operations."""
    exit_code: int = 1

class ParameterNotFoundError(ParameterError):
    """Parameter name doesn't exist."""
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

## Module: `buderus_wps.logging_config`

### Function: `setup_library_logging`

```python
def setup_library_logging() -> None:
    """
    Setup NullHandler for library package.

    Call once in buderus_wps/__init__.py to prevent "No handlers" warnings.
    Applications should configure their own logging.
    """
```

### Function: `setup_cli_logging`

```python
def setup_cli_logging(
    verbose: bool = False,
    log_dir: str = "./logs",
    console: bool = True,
    log_file: bool = True
) -> logging.Logger:
    """
    Configure logging for CLI usage.

    Args:
        verbose: If True, DEBUG level; if False, ERROR only
        log_dir: Directory for log files (created if doesn't exist)
        console: If True, add console handler to stderr
        log_file: If True, add rotating file handler (10MB, 5 backups)

    Returns:
        Configured logger for 'buderus_wps' namespace

    Example:
        >>> logger = setup_cli_logging(verbose=True, log_dir="./logs")
        >>> # All library loggers now use this configuration
    """
```

---

## Backward Compatibility

**Version Policy**: Semantic versioning (MAJOR.MINOR.PATCH)

- **MAJOR**: Breaking API changes (parameter renames, signature changes)
- **MINOR**: New features, backward-compatible additions
- **PATCH**: Bug fixes, performance improvements

**Current Version**: 1.0.0 (initial release)

**Stability Guarantees**:
- Public API (documented here) will not break within major version
- Exception hierarchy stable within major version
- JSON output schema stable within major version
- CLI command syntax stable within major version

---

## Type Hints

All public APIs include complete type hints compatible with:
- Python 3.9+
- mypy strict mode
- pyright standard mode

Example:
```python
from buderus_wps import ParameterAccessor, ParameterValue

accessor: ParameterAccessor = ...
value: ParameterValue = accessor.read_parameter("DHW_TEMP_SETPOINT")
```

---

## Thread Safety

**Not Thread-Safe**: Per spec requirements, library assumes single-threaded sequential usage.

Concurrent calls to `ParameterAccessor` methods result in undefined behavior:
- CAN interface (Feature 001) is not thread-safe
- Serial port communication cannot handle concurrent access
- No internal locking provided

**Recommendation**: Use process-level locking if concurrent access needed.

---

## Contract Testing

All contracts verified by:
- Unit tests: Verify signatures, types, error conditions
- Integration tests: Verify behavior with mock CAN interface
- Contract tests: Verify compatibility with Feature 001 and Feature 002
- Acceptance tests: Verify user story scenarios end-to-end

See: `/tests/contract/test_parameter_access_api.py`

---

## Contract Status

✅ **STABLE** - Ready for implementation in Phase 2
