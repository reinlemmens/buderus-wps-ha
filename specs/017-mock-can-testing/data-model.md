# Data Model: Mock CAN Testing Infrastructure

**Feature**: 017-mock-can-testing
**Date**: 2025-12-18
**Status**: Design Complete

## Overview

This document defines the data structures and entities for the mock CAN adapter infrastructure. All entities are derived from functional requirements (FR-001 through FR-013) and designed to support the four user stories in spec.md.

---

## Entity 1: RecordingSession

**Purpose**: Represents a complete session of CAN traffic captured from physical hardware.

**Description**: Contains metadata about the recording session and an ordered sequence of CAN frames with timestamps. Used for replay mode to provide authentic device behavior in tests.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `metadata` | RecordingMetadata | Yes | Session information | See RecordingMetadata below |
| `frames` | list[FrameRecord] | Yes | Ordered CAN frames | Length must match metadata.frame_count |

### RecordingMetadata

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `recorded_at` | str (ISO 8601) | Yes | Recording timestamp | Valid ISO 8601 datetime |
| `duration_seconds` | float | Yes | Recording duration | Must be > 0 |
| `frame_count` | int | Yes | Total frames captured | Must be >= 0 |
| `port` | str | Yes | Serial port used | Non-empty string (e.g., "/dev/ttyACM0") |
| `description` | str | No | User-provided description | Max 500 characters |

### Example

```json
{
  "metadata": {
    "recorded_at": "2025-12-18T14:30:00Z",
    "duration_seconds": 60.5,
    "frame_count": 484,
    "port": "/dev/ttyACM0",
    "description": "Normal operation, outdoor temp 5°C, compressor running"
  },
  "frames": [...]
}
```

### State Transitions

1. **Recording**: Session created with empty frames list, metadata partially filled
2. **In Progress**: Frames appended as received, metadata.frame_count incremented
3. **Complete**: Recording ended, metadata finalized, written to JSON file
4. **Loaded**: Deserialized from JSON for replay

### Related Requirements

- FR-001: Recording CAN traffic to JSON with timestamps and metadata
- FR-002: Session metadata (duration, frame count, timestamp, port, description)
- SC-001: Record 60 seconds in under 90 seconds total time

---

## Entity 2: FrameRecord

**Purpose**: Individual CAN frame captured during a recording session.

**Description**: Represents a single CAN frame with timestamp (relative to session start), CAN ID, data bytes, and optional human-readable description.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `timestamp` | float | Yes | Time offset from recording start | Must be >= 0, monotonically increasing within session |
| `can_id` | str | Yes | CAN identifier (hex) | Pattern: `^0x[0-9A-F]{8}$` (e.g., "0x0C003060") |
| `dlc` | int | Yes | Data Length Code | Integer 0-8 |
| `data` | str | Yes | Data bytes (hex) | Pattern: `^[0-9A-F]{0,16}$`, length = dlc * 2 |
| `description` | str | No | Human-readable annotation | Max 200 characters |

### Example

```json
{
  "timestamp": 0.125,
  "can_id": "0x0C003060",
  "dlc": 2,
  "data": "00A3",
  "description": "OUTDOOR_TEMP_C0: 16.3°C"
}
```

### Encoding Details

**CAN ID Format**:
- Hex string with "0x" prefix
- Uppercase letters (A-F)
- Zero-padded to 8 hex digits (4 bytes)
- Represents extended 29-bit CAN ID
- Example: `0x0C003060` = prefix 0x0C, idx 12, base 0x0060

**Data Format**:
- Hex string without delimiters or prefix
- Uppercase letters (A-F)
- Length = DLC * 2 characters
- Example: "00A3" = 2 bytes (0x00, 0xA3) = 163 tenths = 16.3°C

**Timestamp**:
- Floating point seconds relative to recording start
- First frame typically timestamp 0.0
- Precision to milliseconds (0.001 second resolution)
- Used for timing during replay

### Validation Rules

1. `timestamp` must be non-negative
2. Within a session, timestamps must be monotonically increasing
3. `can_id` must match pattern (8 hex digits with 0x prefix)
4. `dlc` must be 0-8 (CAN maximum)
5. `data` length must equal `dlc * 2`
6. `data` must contain only hex characters (0-9, A-F)

### Related Requirements

- FR-001: Frame timestamps, CAN IDs, data bytes
- FR-003: Replay with timing based on timestamps
- SC-007: Human-readable, inspectable in text editor

---

## Entity 3: MockUSBtinAdapter

**Purpose**: Drop-in replacement for USBtinAdapter that provides mocked CAN traffic instead of hardware communication.

**Description**: Adapter class that implements the same interface as USBtinAdapter but sources CAN frames from recordings or synthetic generation. Used in tests and dev container to enable hardware-free operation.

### Interface

Matches `USBtinAdapter` from `buderus_wps/can_adapter.py`:

```python
class MockUSBtinAdapter:
    """Mock CAN adapter - interface compatible with USBtinAdapter."""

    def connect(self) -> None:
        """Establish mock connection (no-op or prepare replay/generator)."""

    def disconnect(self) -> None:
        """Close mock connection (cleanup resources)."""

    def send_frame(self, message: CANMessage, timeout: float = 1.0) -> CANMessage:
        """Send RTR request, return mocked response from replay or generator."""

    def receive_frame(self, timeout: float = 0.5) -> CANMessage | None:
        """Receive next broadcast frame from replay engine or generator."""
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `replay_file` | str \| None | No | Path to recording JSON file (enables replay mode) |
| `synthetic` | bool | No | Enable synthetic data generation mode |

### Modes

**Replay Mode** (`replay_file` provided):
- Loads RecordingSession from JSON file
- Plays back frames with original timing
- Returns same responses for RTR requests as real device

**Synthetic Mode** (`synthetic=True`):
- Generates CAN frames programmatically
- Configurable sensor values and broadcast intervals
- Can simulate edge cases (missing sensors, errors)

**Disabled** (neither option set):
- Raises error if used - must configure one mode

### Internal Components

| Component | Type | Purpose |
|-----------|------|---------|
| `_replay_engine` | CANReplayEngine \| None | Manages frame playback from recording |
| `_data_generator` | CANDataGenerator \| None | Generates synthetic CAN frames |
| `_connected` | bool | Connection state flag |

### State Machine

```
[Created] --connect()--> [Connected]
[Connected] --disconnect()--> [Disconnected]
[Disconnected] --connect()--> [Connected]

Operations:
- send_frame(): Only when Connected
- receive_frame(): Only when Connected
```

### Related Requirements

- FR-007: Mock adapter replaces USBtinAdapter at adapter layer
- FR-003: Replay recorded traffic
- FR-005: Generate synthetic broadcasts
- FR-011: Reproduce partial broadcast loss scenario

---

## Entity 4: CANReplayEngine

**Purpose**: Manages playback of recorded CAN traffic with realistic timing.

**Description**: Component within MockUSBtinAdapter that loads a RecordingSession and replays frames in chronological order, maintaining original timing patterns.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `recording` | RecordingSession | Loaded recording data |
| `start_time` | float \| None | Timestamp when playback started (from time.time()) |
| `current_index` | int | Index of next frame to play |
| `loop` | bool | Whether to restart from beginning when recording ends |

### Methods

```python
def start(self) -> None:
    """Start playback - record start time, reset index."""

def stop(self) -> None:
    """Stop playback - clear start time."""

def get_next_broadcast(self, timeout: float) -> CANMessage | None:
    """Get next broadcast frame with timing.

    Waits until frame's timestamp has elapsed, then returns frame.
    Returns None if timeout expires before frame ready.
    """

def get_response(self, param_idx: int) -> CANMessage | None:
    """Get RTR response for parameter from recording.

    Searches recording for matching response CAN ID.
    Returns None if parameter not found in recording.
    """
```

### Timing Algorithm

```
For frame at current_index:
    elapsed = current_time - start_time
    frame_time = frame.timestamp

    if frame_time > elapsed:
        sleep_duration = min(timeout, frame_time - elapsed)
        time.sleep(sleep_duration)
        elapsed = current_time - start_time

    if frame_time <= elapsed:
        return frame
    else:
        return None  # Timeout
```

### Looping Behavior

When `loop=True` and `current_index` reaches end of recording:
1. Reset `current_index` to 0
2. Reset `start_time` to current time
3. Continue playback from first frame

### Related Requirements

- FR-003: Replay with timing based on timestamps
- FR-004: Looping support
- SC-003: Timing accuracy within ±10%

---

## Entity 5: CANDataGenerator

**Purpose**: Generates synthetic CAN broadcast frames for testing edge cases.

**Description**: Component within MockUSBtinAdapter that programmatically creates CAN frames with configurable sensor values, broadcast intervals, and failure scenarios.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `sensor_map` | dict[(base, idx), (name, temp)] | Mapping of CAN parameters to sensor values |
| `broadcast_interval` | float | Time between broadcasts (seconds, default 0.125) |
| `start_time` | float \| None | Timestamp when generation started |
| `last_broadcast_time` | float | Elapsed time of last broadcast |

### Methods

```python
def start(self) -> None:
    """Start generation - record start time."""

def stop(self) -> None:
    """Stop generation - clear start time."""

def generate_broadcast(self, timeout: float) -> CANMessage | None:
    """Generate next broadcast frame.

    Waits for broadcast_interval since last frame.
    Returns synthetic frame with sensor data.
    Adds small random variation (±0.2°C) for realism.
    """

def generate_response(self, param_idx: int) -> CANMessage:
    """Generate RTR response for parameter.

    Looks up parameter in sensor_map.
    Returns synthetic response with current value.
    """
```

### Sensor Map Format

```python
sensor_map = {
    (0x0060, 12): ("OUTDOOR_TEMP_C0", 5.0),    # Base 0x0060, idx 12, value 5.0°C
    (0x0060, 0):  ("SUPPLY_TEMP", 35.0),       # Supply temperature
    (0x0060, 1):  ("RETURN_TEMP", 30.0),       # Return temperature
    (0x0402, 78): ("DHW_TEMP_ACTUAL", 48.0),   # DHW tank temperature
}
```

### CAN Frame Generation

```python
# Encode temperature (tenths of degree)
temp_raw = int(temp_value * 10)
data = bytes([(temp_raw >> 8) & 0xFF, temp_raw & 0xFF])

# Build CAN ID: prefix 0x0C | (idx << 14) | base
can_id = 0x0C000000 | (idx << 14) | base

# Create frame
frame = CANMessage(
    arbitration_id=can_id,
    data=data,
    is_extended_id=True,
    is_remote_frame=False
)
```

### Edge Case Simulation

**Partial Broadcast Loss** (FR-011):
```python
# Remove sensor from map to simulate missing broadcast
sensor_map.pop((0x0402, 78))  # DHW sensor now missing

# Coordinator should use cached value, not show "Unknown"
```

**Temperature Variations**:
```python
# Add random variation for realism
temp_varied = base_temp + random.uniform(-0.2, 0.2)
```

**Rapid Changes** (testing coordinator response):
```python
# Increase outdoor temp from 5°C to 10°C over 30 seconds
for i in range(50):
    sensor_map[(0x0060, 12)] = ("OUTDOOR_TEMP_C0", 5.0 + (i * 0.1))
    await asyncio.sleep(0.6)
```

### Related Requirements

- FR-005: Generate synthetic broadcasts with configurable values
- FR-006: Use same CAN ID encoding as real hardware
- FR-011: Reproduce partial broadcast loss
- SC-004: Bug reproduction in <5 minutes

---

## Relationships Between Entities

```
RecordingSession
    ├─ has many FrameRecords (ordered by timestamp)
    └─ loaded by CANReplayEngine

MockUSBtinAdapter
    ├─ contains one CANReplayEngine (if replay_file provided)
    ├─ contains one CANDataGenerator (if synthetic=True)
    └─ implements same interface as USBtinAdapter

CANReplayEngine
    ├─ loads one RecordingSession from JSON
    └─ returns CANMessages from FrameRecords

CANDataGenerator
    └─ creates CANMessages from sensor_map configuration
```

---

## Validation & Constraints

### Recording Session Validation

1. Metadata frame_count must match actual frames array length
2. Frame timestamps must be monotonically increasing
3. All frames must have valid CAN IDs and data encoding
4. Duration must be >= last frame timestamp

### Mock Adapter Constraints

1. Cannot enable both replay and synthetic modes simultaneously
2. Must call `connect()` before `send_frame()` or `receive_frame()`
3. Recording file must exist and be valid JSON
4. Sensor map must use valid CAN ID encoding (base, idx)

### Type Safety

All entities use Python type hints for static analysis:
```python
RecordingSession = dict[str, Any]  # JSON object
FrameRecord = dict[str, Any]       # JSON object
MockUSBtinAdapter: class           # Concrete class
CANReplayEngine: class             # Concrete class
CANDataGenerator: class            # Concrete class
```

---

## Implementation Notes

### JSON Schema Reference

See [contracts/recording-schema.json](./contracts/recording-schema.json) for formal JSON Schema validation.

### Interface Compatibility

MockUSBtinAdapter interface matches USBtinAdapter (buderus_wps/can_adapter.py) without modification. Uses duck typing - no formal inheritance required.

### Hardware Protocol Reference

CAN ID encoding and data formats reference:
- buderus_wps/can_message.py (lines 12-16): CAN ID structure
- buderus_wps/broadcast_monitor.py (lines 106-155): Broadcast mapping

### Test Integration

All entities designed for pytest fixture use:
- RecordingSession: Loaded from tests/fixtures/can_recordings/*.json
- MockUSBtinAdapter: Instantiated in conftest.py fixtures
- CANReplayEngine: Internal to adapter, transparent to tests
- CANDataGenerator: Internal to adapter, configured via adapter constructor

---

**Data Model Status**: ✅ COMPLETE - Ready for implementation (Phase 2)
