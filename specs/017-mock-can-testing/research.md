# Research: Mock CAN Testing Infrastructure

**Feature**: 017-mock-can-testing
**Date**: 2025-12-18
**Status**: Complete

## Overview

This document captures research findings and technical decisions for implementing the mock CAN adapter infrastructure. Each decision is based on analysis of existing patterns in the codebase, industry best practices, and the specific requirements from spec.md.

---

## Decision 1: JSON Recording Format

### Question
What JSON schema structure best balances human-readability with replay efficiency?

### Research Conducted

**Existing CAN Logging Formats Analyzed**:
1. **Vector CANalyzer ASC**: Text-based, one frame per line, timestamp + ID + data
   - Example: `0.123456 1 18FE6CEE Rx d 8 11 22 33 44 55 66 77 88`
   - Pros: Human-readable, industry standard
   - Cons: Not structured data, requires parsing

2. **SocketCAN candump**: Similar to ASC, Linux-native format
   - Example: `(1639567890.123456) can0 18FE6CEE#1122334455667788`
   - Pros: Simple, widely supported
   - Cons: Minimal metadata, not JSON

3. **Peak PCAN Viewer TRC**: Binary format with text header
   - Pros: Compact, precise timestamps
   - Cons: Not human-readable, requires specialized tools

**JSON Structure Options Evaluated**:
- **Option A**: Flat array with metadata header
- **Option B**: Nested by timestamp ranges
- **Option C**: Grouped by CAN ID

### Decision: Flat Array with Metadata Header (Option A)

**Rationale**:
1. **Human-Readability** (SC-007): Can be opened in any text editor, frames sequential
2. **Simplicity**: Straightforward to write during recording, easy to iterate during replay
3. **Metadata Separation**: Session info in header, frames in array maintains clean structure
4. **Inspection**: Users can grep, search, manually edit recordings without tools

**Format**:
```json
{
  "metadata": {
    "recorded_at": "2025-12-18T12:00:00Z",
    "duration_seconds": 60.5,
    "frame_count": 484,
    "port": "/dev/ttyACM0",
    "description": "Normal operation, outdoor temp 5°C"
  },
  "frames": [
    {
      "timestamp": 0.0,
      "can_id": "0x0C003060",
      "dlc": 2,
      "data": "00A3",
      "description": "OUTDOOR_TEMP_C0: 16.3°C"
    },
    {
      "timestamp": 0.125,
      "can_id": "0x0C0024E2",
      "dlc": 2,
      "data": "0131",
      "description": "DHW_TEMP_ACTUAL: 30.5°C"
    }
  ]
}
```

**Encoding Decisions**:
- **Timestamp**: Float, relative to recording start (seconds with decimal precision)
  - Rationale: Simple arithmetic for timing, matches Python time.time() precision
- **CAN ID**: Hex string with "0x" prefix, uppercase, 8 digits (e.g., "0x0C003060")
  - Rationale: Human-readable, matches existing logging in codebase, unambiguous
- **Data**: Hex string, uppercase, no delimiters (e.g., "00A3")
  - Rationale: Compact, matches CAN protocol convention, easy to parse with bytes.fromhex()
- **Description**: Optional human-readable string
  - Rationale: Helps users understand recordings, maps to parameter names from broadcast_monitor.py

**Alternatives Considered**:
- Base64 encoding: Rejected - not human-readable
- Numeric arrays for data: Rejected - verbose, harder to read
- Absolute timestamps: Rejected - replay would need offset calculation, less clear
- Grouped by CAN ID: Rejected - harder to replay in chronological order

---

## Decision 2: Timing Precision Strategy

### Question
How to maintain ±10% timing accuracy during replay without complex scheduling?

### Research Conducted

**Timing Mechanisms Evaluated**:

1. **`time.sleep()` (Synchronous)**
   - Python's standard library sleep function
   - Typical accuracy: ±1-10ms on Linux (depends on OS scheduler)
   - For 125ms broadcast interval: ±1-10ms = 0.8-8% variance
   - Pros: Simple, no async complexity, adequate for ±10% requirement
   - Cons: Blocks thread, not suitable for async contexts

2. **`asyncio.sleep()` (Asynchronous)**
   - Async version for coroutine contexts
   - Similar accuracy to time.sleep()
   - Required when used in Home Assistant async coordinator
   - Pros: Non-blocking, integrates with HA async pattern
   - Cons: More complex, requires async/await everywhere

3. **Timestamp-Based Scheduling**
   - Calculate next frame time, sleep until then
   - Accounts for processing time between frames
   - Can skip frames if replay falls behind
   - Pros: Most accurate, handles variable frame processing time
   - Cons: More complex logic, may drop frames

**Observations from Codebase**:
- Home Assistant coordinator uses async/await (`async def _async_update_data()`)
- Broadcast monitor (buderus_wps/broadcast_monitor.py) uses `time.sleep()` for collection
- Hardware-in-loop tests use synchronous timing

### Decision: Hybrid Approach - `time.sleep()` for Sync, `asyncio.sleep()` for Async

**Rationale**:
1. **Context-Appropriate**: Use time.sleep() in replay engine (sync), asyncio.sleep() in coordinator (async)
2. **Adequate Precision**: Both achieve <10% variance for typical broadcast intervals (125ms)
3. **Simplicity**: Straightforward implementation, matches existing codebase patterns
4. **Timestamp Tracking**: Track elapsed time to maintain overall accuracy, but don't skip frames

**Implementation Strategy**:
```python
# Replay engine (synchronous)
def get_next_broadcast(self, timeout: float) -> CANMessage | None:
    elapsed = time.time() - self.start_time
    next_frame_time = self.frames[self.current_index]["timestamp"]

    if next_frame_time > elapsed:
        sleep_duration = min(timeout, next_frame_time - elapsed)
        time.sleep(sleep_duration)

    return self._parse_frame(self.frames[self.current_index])

# Async wrapper for HA coordinator
async def async_receive_frame(self, timeout: float) -> CANMessage | None:
    # Run sync replay in executor to avoid blocking event loop
    return await hass.async_add_executor_job(
        self.replay_engine.get_next_broadcast, timeout
    )
```

**Clock Drift Handling**:
- For 60+ second recordings, cumulative error could reach ±3-5%
- Acceptable within ±10% requirement
- If needed, can add periodic time correction every N frames

**Alternatives Considered**:
- Precision timers (sched module): Rejected - overkill for ±10% requirement
- Frame skipping: Rejected - want all frames for complete testing
- Real-time multiplier: Deferred - can add later if needed (e.g., 2x speed replay)

---

## Decision 3: Mock Injection Pattern

### Question
Best approach to inject mock adapter without modifying USBtinAdapter interface?

### Research Conducted

**Existing Patterns in tests/conftest.py**:

```python
# Current fixture pattern (lines 236-244)
@pytest.fixture
def mock_usb_adapter() -> MagicMock:
    adapter = MagicMock(spec=USBtinAdapter)
    adapter.connect.return_value = None
    adapter.disconnect.return_value = None
    adapter.send_frame.return_value = create_mock_can_message()
    adapter.receive_frame.return_value = create_mock_can_message()
    return adapter

# Coordinator fixture (lines 263-280)
@pytest.fixture
def mock_coordinator(mock_buderus_data) -> MagicMock:
    coordinator = MagicMock(spec=BuderusCoordinator)
    coordinator.data = mock_buderus_data
    # ... properties mocked
    return coordinator
```

**Integration Test Patterns** (tests/integration/test_can_adapter_mock.py):
```python
# Monkey patching with @patch decorator (line 89)
@patch('serial.Serial')
def test_connect_success(self, mock_serial_class):
    mock_serial = MagicMock()
    mock_serial_class.return_value = mock_serial
    # Test USBtinAdapter with mocked serial
```

**Injection Points Identified**:
1. **BuderusCoordinator.__init__()** (custom_components/buderus_wps/coordinator.py:44-77)
   - Creates USBtinAdapter, HeatPumpClient, BroadcastMonitor
   - Current: Direct instantiation with `port` parameter
   - Opportunity: Pass adapter instance or use factory

2. **HeatPumpClient constructor** (buderus_wps/heat_pump.py)
   - Accepts `adapter` parameter already
   - Already supports dependency injection

3. **Pytest fixtures** (tests/conftest.py)
   - Can create MockUSBtinAdapter and inject via constructor

### Decision: Direct Fixture Injection (Duck Typing)

**Rationale**:
1. **No Interface Changes**: MockUSBtinAdapter implements same interface as USBtinAdapter
2. **Duck Typing**: Python doesn't require explicit inheritance, just matching interface
3. **Existing Pattern**: Matches current test approach (MagicMock with spec)
4. **Simplicity**: No factory pattern needed, fixtures instantiate mock directly

**Implementation Pattern**:

```python
# tests/mocks/mock_can_adapter.py
class MockUSBtinAdapter:
    """Drop-in replacement for USBtinAdapter."""

    def __init__(self, replay_file: str | None = None, synthetic: bool = False):
        self.replay_file = replay_file
        self.synthetic = synthetic
        self._connected = False
        # ... initialization

    # Implement same interface as USBtinAdapter
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def send_frame(self, message: CANMessage, timeout: float = 1.0) -> CANMessage: ...
    def receive_frame(self, timeout: float = 0.5) -> CANMessage | None: ...

# tests/conftest.py (NEW FIXTURES)
@pytest.fixture
def mock_can_adapter_replay(request) -> MockUSBtinAdapter:
    """Mock adapter with replay mode."""
    recording_file = getattr(request, 'param', 'normal_operation.json')
    recording_path = Path(__file__).parent / "fixtures" / "can_recordings" / recording_file

    adapter = MockUSBtinAdapter(replay_file=str(recording_path))
    adapter.connect()
    yield adapter
    adapter.disconnect()

@pytest.fixture
def mock_can_adapter_synthetic() -> MockUSBtinAdapter:
    """Mock adapter with synthetic mode."""
    adapter = MockUSBtinAdapter(synthetic=True)
    adapter.connect()
    yield adapter
    adapter.disconnect()

# Test usage
@pytest.mark.parametrize("mock_can_adapter_replay", ["startup_sequence.json"], indirect=True)
async def test_with_specific_recording(mock_can_adapter_replay):
    coordinator = BuderusCoordinator(hass, "/dev/mock", 30)
    coordinator._adapter = mock_can_adapter_replay  # Direct injection
    # ... test logic
```

**Dev Container Injection** (custom_components/buderus_wps/__init__.py):

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port = entry.data[CONF_PORT]

    # Check for mock mode environment variable
    adapter = None
    if os.getenv("MOCK_CAN_MODE"):
        from tests.mocks.mock_can_adapter import MockUSBtinAdapter

        mock_mode = os.getenv("MOCK_CAN_MODE")
        if mock_mode.startswith("replay:"):
            recording_file = mock_mode.split(":", 1)[1]
            adapter = MockUSBtinAdapter(replay_file=recording_file)
        elif mock_mode == "synthetic":
            adapter = MockUSBtinAdapter(synthetic=True)

    coordinator = BuderusCoordinator(hass, port, scan_interval)

    # Inject mock if configured
    if adapter:
        coordinator._adapter = adapter

    await coordinator.async_setup()
    # ... rest of setup
```

**Alternatives Considered**:
- **Factory Pattern**: Rejected - over-engineered for simple injection
- **Monkey Patching**: Rejected - more fragile, harder to debug
- **Formal Interface/ABC**: Rejected - Python duck typing sufficient, no need for abstract base class

---

## Decision 4: Configuration Strategy

### Question
How to configure mock mode (replay/synthetic) for dev container vs pytest?

### Research Conducted

**Dev Container Configuration** (.devcontainer/devcontainer.json):
- `containerEnv`: Environment variables available in container
- `initializeCommand`: Runs on host before container starts
- `postStartCommand`: Runs in container after start
- Bootstrap script: `.devcontainer/devcontainer_bootstrap.sh`

**Existing Patterns**:
- HA configuration: `.devcontainer/config/configuration.yaml`
- Environment variables: Used for WORKSPACE_DIRECTORY
- Post-start hook: Already exists for setup

**Pytest Configuration** (pyproject.toml):
- Markers for test categorization
- Fixtures for dependency injection
- Parametrization for test variations

### Decision: Environment Variables for Dev Container, Fixture Parameters for Pytest

**Rationale**:
1. **Separation of Concerns**: Dev container config separate from test config
2. **Flexibility**: Pytest fixtures can override env vars for specific tests
3. **Existing Pattern**: Matches current devcontainer approach
4. **Explicit Control**: Tests opt-in to mocking via fixtures

**Configuration Precedence**:
1. Fixture parameter (highest priority - test-specific)
2. Environment variable (dev container or CI)
3. Default (no mock - use real adapter)

**Dev Container Configuration**:

```bash
# .devcontainer/devcontainer_bootstrap.sh (additions)

# Configure mock CAN adapter
cat > /config/.mock_can_config <<EOF
# Mock CAN Adapter Configuration
# Uncomment to enable mock mode in dev container

# Replay mode (use recorded traffic)
MOCK_CAN_MODE=replay:normal_operation.json

# Synthetic mode (generate test data)
# MOCK_CAN_MODE=synthetic

# Disable mock (use real hardware - default)
# MOCK_CAN_MODE=disabled
EOF

# Install mock package if not already installed
if [ ! -d "/workspace/tests/mocks" ]; then
    pip install -e /workspace/tests/mocks/
fi
```

**Pytest Configuration**:

```python
# pyproject.toml (additions)
[tool.pytest.ini_options]
markers = [
    # ... existing markers
    "mock_replay: Tests using recorded CAN traffic",
    "mock_synthetic: Tests using synthetic CAN data",
]

# tests/conftest.py (additions)
def pytest_configure(config):
    """Register mock mode environment variables."""
    # Allow pytest to override MOCK_CAN_MODE
    if config.option.markexpr:
        if "mock_replay" in config.option.markexpr:
            os.environ["MOCK_CAN_MODE"] = "replay:test_default.json"
        elif "mock_synthetic" in config.option.markexpr:
            os.environ["MOCK_CAN_MODE"] = "synthetic"

# Test usage
@pytest.mark.mock_replay
async def test_with_replay():
    # MOCK_CAN_MODE automatically set via marker
    pass

@pytest.mark.parametrize("mock_can_adapter_replay", ["specific_scenario.json"], indirect=True)
async def test_with_specific_recording(mock_can_adapter_replay):
    # Fixture parameter overrides marker/env var
    pass
```

**Configuration File Support** (optional enhancement):

```python
# Load from config file if env var not set
import configparser

def load_mock_config():
    config = configparser.ConfigParser()
    config_path = Path("/config/.mock_can_config")

    if config_path.exists():
        config.read(config_path)
        return config.get("mock", "MOCK_CAN_MODE", fallback=None)

    return os.getenv("MOCK_CAN_MODE")
```

**Alternatives Considered**:
- **CLI arguments**: Rejected - not persistent across HA restarts
- **YAML configuration**: Rejected - overkill for simple on/off setting
- **pytest.ini only**: Rejected - doesn't work for dev container HA instance

---

## Summary of Decisions

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **JSON Format** | Flat array with metadata header | Human-readable, simple, meets SC-007 |
| **Timestamp Encoding** | Relative seconds (float) | Matches Python time.time(), simple replay arithmetic |
| **Data Encoding** | Uppercase hex strings | Human-readable, matches CAN conventions |
| **Timing Mechanism** | time.sleep() (sync) + asyncio.sleep() (async) | Adequate ±10% accuracy, context-appropriate |
| **Clock Drift** | Accept cumulative error | Within ±10% requirement for 60s recordings |
| **Mock Injection** | Direct fixture injection (duck typing) | No interface changes, matches existing patterns |
| **Injection Points** | Coordinator._adapter, fixture parameters | Explicit, flexible, testable |
| **Dev Container Config** | Environment variables | Matches existing devcontainer pattern |
| **Pytest Config** | Fixture parameters + markers | Explicit test control, parametrization support |
| **Config Precedence** | Fixture > Env Var > Default | Test-specific overrides global settings |

---

## Implementation Notes

### Phase 1 Artifacts Ready
All research questions resolved. Phase 1 can proceed with:
1. **data-model.md**: Document entities (RecordingSession, FrameRecord, MockUSBtinAdapter, CANReplayEngine, CANDataGenerator)
2. **contracts/recording-schema.json**: Use JSON schema from Decision 1
3. **contracts/mock-adapter-interface.md**: Document interface contract
4. **quickstart.md**: Usage guide with examples

### No Blockers
- All NEEDS CLARIFICATION items resolved
- No additional research required
- Constitution compliance maintained (all gates passed)

---

**Research Status**: ✅ COMPLETE - Ready for Phase 1 Design
