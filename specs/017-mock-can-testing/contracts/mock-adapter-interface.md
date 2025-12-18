# Mock Adapter Interface Contract

**Feature**: 017-mock-can-testing
**Date**: 2025-12-18
**Version**: 1.0.0

## Overview

This document defines the interface contract for `MockUSBtinAdapter`, ensuring compatibility with the existing `USBtinAdapter` interface without modifications to the original adapter code.

## Interface Specification

### Class: MockUSBtinAdapter

**Location**: `tests/mocks/mock_can_adapter.py`

**Purpose**: Drop-in replacement for `USBtinAdapter` that provides mocked CAN traffic from recordings or synthetic generation.

**Compatibility**: Must implement identical interface to `buderus_wps.can_adapter.USBtinAdapter` (duck typing).

---

## Constructor

```python
def __init__(
    self,
    replay_file: str | None = None,
    synthetic: bool = False
) -> None:
    """Initialize mock adapter.

    Args:
        replay_file: Path to recording JSON file (enables replay mode)
        synthetic: Enable synthetic data generation mode

    Raises:
        ValueError: If both replay_file and synthetic are provided
        FileNotFoundError: If replay_file doesn't exist
        JSONDecodeError: If replay_file is invalid JSON
    """
```

**Modes**:
- **Replay**: `replay_file` provided, `synthetic=False`
- **Synthetic**: `replay_file=None`, `synthetic=True`
- **Invalid**: Both or neither provided (raises ValueError)

---

## Public Methods

### connect()

```python
def connect(self) -> None:
    """Establish mock connection.

    For replay mode: Loads recording file and initializes replay engine.
    For synthetic mode: Initializes data generator.

    Raises:
        DeviceConnectionError: If already connected
        FileNotFoundError: If replay file doesn't exist (replay mode)
        JSONDecodeError: If replay file invalid (replay mode)
    """
```

**Behavior**:
- Sets internal `_connected` flag to True
- Replay mode: Loads JSON, validates schema, starts replay engine
- Synthetic mode: Initializes generator with default sensor values
- Idempotent: Safe to call multiple times (no-op if already connected)

**Post-conditions**:
- `_connected == True`
- `send_frame()` and `receive_frame()` become operational

---

### disconnect()

```python
def disconnect(self) -> None:
    """Close mock connection and release resources.

    Raises:
        DeviceConnectionError: If not connected
    """
```

**Behavior**:
- Sets internal `_connected` flag to False
- Replay mode: Stops replay engine, releases recording data
- Synthetic mode: Stops generator
- Safe to call multiple times (no-op if already disconnected)

**Post-conditions**:
- `_connected == False`
- `send_frame()` and `receive_frame()` raise errors if called

---

### send_frame()

```python
def send_frame(
    self,
    message: CANMessage,
    timeout: float = 1.0
) -> CANMessage:
    """Send CAN frame and wait for response.

    Typically used for RTR (Remote Transmission Request) to read parameters.

    Args:
        message: CAN message to send (usually RTR frame)
        timeout: Maximum time to wait for response (seconds)

    Returns:
        CANMessage: Response frame from mock (replay or synthetic)

    Raises:
        DeviceNotConnectedError: If not connected
        DeviceCommunicationError: If timeout expires without response
        ValueError: If message format invalid
    """
```

**Behavior**:
- Replay mode: Searches recording for matching response CAN ID
- Synthetic mode: Generates response based on parameter index
- RTR requests: Extract parameter index from CAN ID, return corresponding response
- Data frames: Return acknowledgment (implementation-specific)

**Timing**:
- Returns immediately (no actual serial communication)
- Timeout parameter ignored (mock always responds instantly)

---

### receive_frame()

```python
def receive_frame(
    self,
    timeout: float = 0.5
) -> CANMessage | None:
    """Receive next broadcast CAN frame.

    Used for passive monitoring of heat pump broadcasts.

    Args:
        timeout: Maximum time to wait for frame (seconds)

    Returns:
        CANMessage: Next broadcast frame, or None if timeout
        None: If timeout expires before frame available

    Raises:
        DeviceNotConnectedError: If not connected
    """
```

**Behavior**:
- Replay mode: Returns next frame from recording based on timing
- Synthetic mode: Generates broadcast at configured interval
- Timing: Waits for appropriate delay to maintain realistic intervals
- Returns None if timeout expires before frame ready

**Timing Accuracy**:
- Replay: ±10% of original broadcast timing (per SC-003)
- Synthetic: Configurable interval (default 125ms between frames)

---

## Properties

### port (read-only)

```python
@property
def port(self) -> str:
    """Get mock port identifier.

    Returns:
        str: Mock port name (e.g., "/dev/mock" or replay file name)
    """
```

**Behavior**:
- Replay mode: Returns replay file path
- Synthetic mode: Returns "/dev/mock/synthetic"

---

### is_connected (read-only)

```python
@property
def is_connected(self) -> bool:
    """Check if mock adapter is connected.

    Returns:
        bool: True if connected, False otherwise
    """
```

---

## Error Handling

### Exception Types

MockUSBtinAdapter raises the same exceptions as USBtinAdapter:

| Exception | When Raised | Recovery |
|-----------|-------------|----------|
| `DeviceNotFoundError` | Replay file not found | Provide valid file path |
| `DeviceConnectionError` | Connection failed (invalid JSON) | Fix JSON format |
| `DeviceNotConnectedError` | Operation attempted while disconnected | Call `connect()` first |
| `DeviceCommunicationError` | Timeout (rarely in mock) | Increase timeout |
| `ValueError` | Invalid configuration (both modes enabled) | Choose one mode |

### Error Messages

Error messages must be descriptive and include context:

```python
# Good
raise DeviceNotFoundError(
    f"Recording file not found: {replay_file}. "
    "Ensure file exists in tests/fixtures/can_recordings/"
)

# Bad
raise DeviceNotFoundError("File not found")
```

---

## Thread Safety

**Contract**: MockUSBtinAdapter is **NOT thread-safe**.

**Behavior**:
- Must be used from single thread only
- Matches USBtinAdapter behavior (also not thread-safe)
- For async contexts: Use `hass.async_add_executor_job()` wrapper

---

## Compatibility Requirements

### 1. Type Signatures

Must match USBtinAdapter exactly:
- Same method names
- Same parameter names and types
- Same return types
- Same default values

### 2. Exception Types

Must raise same exception types as USBtinAdapter:
- DeviceNotFoundError
- DeviceConnectionError
- DeviceNotConnectedError
- DeviceCommunicationError

### 3. Behavioral Parity

Must behave identically from caller perspective:
- Connection state machine (disconnected → connected → disconnected)
- Frame send/receive semantics
- Error conditions

### 4. No Additional Public Interface

Must not expose additional public methods beyond USBtinAdapter interface. Implementation-specific methods must be private (prefixed with `_`).

---

## Usage Contract

### Initialization

```python
# Replay mode
adapter = MockUSBtinAdapter(replay_file="tests/fixtures/can_recordings/normal_operation.json")

# Synthetic mode
adapter = MockUSBtinAdapter(synthetic=True)

# Invalid (raises ValueError)
adapter = MockUSBtinAdapter(replay_file="file.json", synthetic=True)
adapter = MockUSBtinAdapter()  # Neither mode specified
```

### Connection Lifecycle

```python
adapter.connect()
try:
    # Use adapter
    response = adapter.send_frame(request_message)
    broadcast = adapter.receive_frame(timeout=1.0)
finally:
    adapter.disconnect()
```

### Pytest Fixture Pattern

```python
@pytest.fixture
def mock_adapter():
    adapter = MockUSBtinAdapter(synthetic=True)
    adapter.connect()
    yield adapter
    adapter.disconnect()
```

---

## Testing Requirements

### Contract Tests

MockUSBtinAdapter must pass same contract tests as USBtinAdapter:

```python
def test_connect_disconnect_lifecycle(adapter):
    """Test connection state machine."""
    assert not adapter.is_connected
    adapter.connect()
    assert adapter.is_connected
    adapter.disconnect()
    assert not adapter.is_connected

def test_send_frame_requires_connection(adapter):
    """Test send_frame fails when disconnected."""
    with pytest.raises(DeviceNotConnectedError):
        adapter.send_frame(CANMessage(...))

def test_receive_frame_timeout(adapter):
    """Test receive_frame returns None on timeout."""
    adapter.connect()
    frame = adapter.receive_frame(timeout=0.001)
    assert frame is None or isinstance(frame, CANMessage)
```

### Interface Validation

```python
def test_interface_compatibility():
    """Verify MockUSBtinAdapter implements USBtinAdapter interface."""
    from buderus_wps.can_adapter import USBtinAdapter

    # Check method signatures
    for method_name in ['connect', 'disconnect', 'send_frame', 'receive_frame']:
        assert hasattr(MockUSBtinAdapter, method_name)
        assert callable(getattr(MockUSBtinAdapter, method_name))

        # Check signature matches (name, parameters, types)
        mock_sig = inspect.signature(getattr(MockUSBtinAdapter, method_name))
        real_sig = inspect.signature(getattr(USBtinAdapter, method_name))
        assert mock_sig == real_sig, f"Signature mismatch for {method_name}"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-18 | Initial interface specification |

---

## References

- **Original Interface**: `buderus_wps/can_adapter.py` - USBtinAdapter class
- **CAN Protocol**: `buderus_wps/can_message.py` - CANMessage dataclass
- **Usage Examples**: `tests/integration/test_can_adapter_mock.py` - Existing mocking patterns

---

**Interface Contract Status**: ✅ APPROVED - Ready for implementation
