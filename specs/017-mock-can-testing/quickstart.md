# Quickstart Guide: Mock CAN Testing Infrastructure

**Feature**: 017-mock-can-testing
**Audience**: Developers working on Buderus WPS Home Assistant integration
**Prerequisites**: Dev container setup, Python 3.9+, pytest

---

## Table of Contents

1. [Recording CAN Traffic from Real Hardware](#1-recording-can-traffic-from-real-hardware)
2. [Using Replay Mode in Dev Container](#2-using-replay-mode-in-dev-container)
3. [Using Synthetic Mode in Pytest](#3-using-synthetic-mode-in-pytest)
4. [Adding New Recording Scenarios](#4-adding-new-recording-scenarios)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Recording CAN Traffic from Real Hardware

### Prerequisites
- Physical heat pump with USBtin adapter connected
- SSH access to production HA instance (`hassio@homeassistant.local`)
- Serial port accessible (typically `/dev/ttyACM0`)

### Step 1: SSH to Hardware

```bash
ssh hassio@homeassistant.local
cd ~/buderus-wps-ha
source venv/bin/activate
```

### Step 2: Record CAN Traffic

```bash
python tools/record_can_traffic.py \
  --port /dev/ttyACM0 \
  --duration 60 \
  --output tests/fixtures/can_recordings/my_scenario.json \
  --description "Outdoor temp 5°C, compressor running, DHW heating active"
```

**Parameters**:
- `--port`: Serial port (use `ls /dev/tty*` to find)
- `--duration`: Recording length in seconds (60 recommended)
- `--output`: Output JSON file path
- `--description`: Human-readable scenario description

### Step 3: Verify Recording

```bash
# Check file was created
ls -lh tests/fixtures/can_recordings/my_scenario.json

# Inspect contents
head -50 tests/fixtures/can_recordings/my_scenario.json

# Validate JSON format
python -m json.tool tests/fixtures/can_recordings/my_scenario.json > /dev/null
echo "JSON valid: $?"
```

### Step 4: Copy to Development Machine

```bash
# On your dev machine
scp hassio@homeassistant.local:~/buderus-wps-ha/tests/fixtures/can_recordings/my_scenario.json \
    tests/fixtures/can_recordings/
```

### Expected Output

```json
{
  "metadata": {
    "recorded_at": "2025-12-18T14:30:00Z",
    "duration_seconds": 60.2,
    "frame_count": 481,
    "port": "/dev/ttyACM0",
    "description": "Outdoor temp 5°C, compressor running, DHW heating active"
  },
  "frames": [
    {
      "timestamp": 0.0,
      "can_id": "0x0C003060",
      "dlc": 2,
      "data": "0032",
      "description": "OUTDOOR_TEMP_C0: 5.0°C"
    },
    ...
  ]
}
```

**Success Criteria** (SC-001): Should complete in <90 seconds total (60s recording + 30s overhead).

---

## 2. Using Replay Mode in Dev Container

### Step 1: Configure Mock Mode

Edit `.devcontainer/devcontainer_bootstrap.sh` or set environment variable:

**Option A: Bootstrap Script** (persistent)
```bash
# Uncomment/edit in .devcontainer/devcontainer_bootstrap.sh
export MOCK_CAN_MODE=replay:normal_operation.json
```

**Option B: Environment Variable** (session-specific)
```bash
# In dev container terminal
export MOCK_CAN_MODE=replay:my_scenario.json
```

### Step 2: Restart Home Assistant

```bash
# In dev container
cd /config
ha core restart
```

Or rebuild dev container:
- VSCode: Command Palette → "Dev Containers: Rebuild Container"

### Step 3: Verify Mock Adapter Active

Check Home Assistant logs:

```bash
ha logs | grep -i "mock\|buderus"
```

Expected output:
```
INFO Using mock CAN adapter with replay: normal_operation.json
INFO Heat Pump integration loaded with mock adapter
```

### Step 4: Test Sensors

Open Home Assistant UI at `http://localhost:7123`

1. Navigate to **Developer Tools** → **States**
2. Search for `sensor.heat_pump`
3. Verify sensors show values from recording:
   - `sensor.heat_pump_outdoor_temperature`
   - `sensor.heat_pump_supply_temperature`
   - `sensor.heat_pump_dhw_temperature`
4. Check entity attributes for staleness indicators:
   - `data_is_stale: false` (if replay active)
   - `last_update_age_seconds: <10` (recent)

**Success Criteria** (SC-002): Sensors update within 30 seconds of HA start.

### Replay Loop Behavior

- Recording plays from start to end
- When `duration_seconds` reached, replay restarts from beginning
- Seamless loop for continuous testing

---

## 3. Using Synthetic Mode in Pytest

### Step 1: Create Test with Synthetic Fixture

```python
# tests/integration/test_my_feature.py
import pytest
from tests.mocks.mock_can_adapter import MockUSBtinAdapter

@pytest.fixture
def synthetic_adapter():
    """Fixture providing synthetic CAN adapter."""
    adapter = MockUSBtinAdapter(synthetic=True)
    adapter.connect()
    yield adapter
    adapter.disconnect()

async def test_coordinator_handles_missing_sensor(synthetic_adapter, mock_hass):
    """Test partial broadcast loss scenario (FR-011)."""
    from custom_components.buderus_wps.coordinator import BuderusCoordinator

    # Configure generator to skip DHW sensor
    synthetic_adapter._data_generator.sensor_map.pop((0x0402, 78))

    coordinator = BuderusCoordinator(mock_hass, "/dev/mock", 30)
    coordinator._adapter = synthetic_adapter
    coordinator._connected = True

    # First refresh - get initial values
    await coordinator.async_refresh()
    initial_dhw = coordinator.data.temperatures.get("dhw")
    assert initial_dhw is not None, "Should have DHW temp from first broadcast"

    # Second refresh - DHW missing from broadcast
    await coordinator.async_refresh()

    # BUG FIX TEST: DHW should retain cached value, not become None
    assert coordinator.data.temperatures.get("dhw") == initial_dhw
    assert coordinator.is_data_stale() is False  # Generator still working
```

### Step 2: Run Tests

```bash
# Run specific test
pytest tests/integration/test_my_feature.py::test_coordinator_handles_missing_sensor -v

# Run all tests using synthetic mode
pytest -m mock_synthetic -v

# Run with coverage
pytest tests/integration/ --cov=custom_components.buderus_wps --cov-report=html
```

### Step 3: Configure Synthetic Sensor Values

```python
@pytest.fixture
def custom_synthetic_adapter():
    """Synthetic adapter with custom temperatures."""
    adapter = MockUSBtinAdapter(synthetic=True)

    # Customize sensor values
    adapter._data_generator.sensor_map = {
        (0x0060, 12): ("OUTDOOR_TEMP_C0", -5.0),  # Cold outdoor temp
        (0x0060, 0):  ("SUPPLY_TEMP", 45.0),      # High supply temp
        (0x0060, 1):  ("RETURN_TEMP", 35.0),      # Return temp
        (0x0402, 78): ("DHW_TEMP_ACTUAL", 55.0),  # DHW temp
    }

    # Faster broadcasts for testing
    adapter._data_generator.broadcast_interval = 0.05  # 50ms instead of 125ms

    adapter.connect()
    yield adapter
    adapter.disconnect()
```

**Success Criteria** (SC-004): Bug reproduction setup in <5 minutes.

---

## 4. Adding New Recording Scenarios

### Pre-recorded Scenarios

The following scenarios should be captured:

| Scenario | Filename | Description | Duration |
|----------|----------|-------------|----------|
| Normal operation | `normal_operation.json` | Steady-state heating, typical temps | 60s |
| Startup sequence | `startup_sequence.json` | Heat pump boot, initial broadcasts | 120s |
| Compressor cycling | `compressor_cycling.json` | Compressor on/off transitions | 180s |
| Varying temperatures | `varying_temperatures.json` | Outdoor temp changes 5°C → 10°C | 300s |
| Partial broadcast loss | `partial_broadcast_loss.json` | Some sensors missing (bug repro) | 60s |

### Capturing New Scenario

1. **Plan scenario**: Define what to capture (e.g., "DHW heating cycle")
2. **Set up hardware**: Configure heat pump to desired state
3. **Record**: Use `record_can_traffic.py` with descriptive name
4. **Verify**: Check frame count, duration, parameter coverage
5. **Document**: Add to `tests/fixtures/can_recordings/README.md`
6. **Test**: Create integration test using new recording

### Example: Recording DHW Heating Cycle

```bash
# SSH to hardware
ssh hassio@homeassistant.local

# Trigger DHW heating (via HA UI or heat pump controls)
# Wait for DHW heating to start (compressor running, DHW temp rising)

# Start recording
cd ~/buderus-wps-ha
source venv/bin/activate
python tools/record_can_traffic.py \
  --port /dev/ttyACM0 \
  --duration 180 \
  --output tests/fixtures/can_recordings/dhw_heating_cycle.json \
  --description "DHW heating cycle from 40°C to 50°C, compressor active"

# Copy to dev machine and commit
```

### Recording Catalog

Maintain `tests/fixtures/can_recordings/README.md`:

```markdown
# CAN Traffic Recordings

| File | Date | Duration | Frames | Description |
|------|------|----------|--------|-------------|
| normal_operation.json | 2025-12-18 | 60s | 481 | Steady-state, outdoor 5°C |
| dhw_heating_cycle.json | 2025-12-18 | 180s | 1443 | DHW 40°C→50°C |
```

---

## 5. Troubleshooting

### Issue: Recording Tool Fails with "Permission Denied"

**Symptom**:
```
ERROR: Cannot open /dev/ttyACM0: Permission denied
```

**Solution**:
```bash
# Check user is in audio group (needed for serial port access)
groups hassio | grep audio

# If not in group, add and re-login
sudo usermod -a -G audio hassio
# Logout and login again
```

---

### Issue: Dev Container HA Doesn't Start with Mock

**Symptom**:
```
ERROR: Mock CAN adapter not found
ERROR: ModuleNotFoundError: No module named 'tests.mocks'
```

**Solution**:
```bash
# Install mock package in dev container
cd /workspace
pip install -e tests/mocks/

# Verify installation
python -c "from tests.mocks.mock_can_adapter import MockUSBtinAdapter; print('OK')"
```

---

### Issue: Replay Timing Too Fast/Slow

**Symptom**:
Sensors update much faster or slower than expected.

**Diagnosis**:
```python
# Check replay timing in logs
import logging
logging.getLogger('tests.mocks.can_replay_engine').setLevel(logging.DEBUG)
```

**Solution**:
- Fast: Normal behavior if processing is faster than real-time
- Slow: Check CPU usage, may need to reduce broadcast interval
- Verify recording timestamps are correct:
  ```bash
  grep "timestamp" my_recording.json | head -20
  ```

---

### Issue: Synthetic Mode Shows Wrong Temperatures

**Symptom**:
Sensors show unexpected values (e.g., 0°C when expecting 20°C).

**Solution**:
```python
# Print sensor map configuration
@pytest.fixture
def debug_synthetic_adapter():
    adapter = MockUSBtinAdapter(synthetic=True)
    adapter.connect()

    print("Sensor map:")
    for (base, idx), (name, value) in adapter._data_generator.sensor_map.items():
        print(f"  {name}: {value}°C (base=0x{base:04X}, idx={idx})")

    yield adapter
    adapter.disconnect()
```

---

### Issue: Tests Pass with Mock but Fail with Real Hardware

**Symptom**:
Integration tests pass using MockUSBtinAdapter but fail with real device.

**Common Causes**:
1. **Timing assumptions**: Mock responds instantly, real device has delays
2. **Missing parameters**: Mock generates only configured sensors
3. **Error handling**: Real device has communication errors not simulated

**Solution**:
1. Always test with real hardware before release (per E2E requirements)
2. Add HIL tests for critical paths
3. Record real traffic and use for regression testing

---

### Issue: Recording File Too Large

**Symptom**:
Recording JSON file is 10+ MB, causing slow load times.

**Diagnosis**:
```bash
wc -l my_recording.json    # Check frame count
du -h my_recording.json     # Check file size
```

**Solution**:
- **Reduce duration**: 60s usually sufficient (vs 300s)
- **Filter frames**: Remove duplicate/unnecessary broadcasts (manual edit)
- **Split scenarios**: Create multiple smaller recordings instead of one large

**Typical sizes**:
- 60s recording: ~500 frames, ~150 KB
- 180s recording: ~1500 frames, ~450 KB

---

## Quick Reference

### Environment Variables

| Variable | Values | Purpose |
|----------|--------|---------|
| `MOCK_CAN_MODE` | `replay:<file>` | Use replay mode with file |
| `MOCK_CAN_MODE` | `synthetic` | Use synthetic mode |
| `MOCK_CAN_MODE` | `disabled` | Use real hardware (default) |

### File Locations

| Path | Contents |
|------|----------|
| `tools/record_can_traffic.py` | Recording CLI tool |
| `tests/mocks/` | Mock adapter package |
| `tests/fixtures/can_recordings/` | Recorded JSON files |
| `tests/integration/test_mock_can_scenarios.py` | Example tests |

### Common Commands

```bash
# Record CAN traffic
python tools/record_can_traffic.py --port /dev/ttyACM0 --duration 60 --output file.json --description "..."

# Run tests with mocks
pytest tests/integration/ -v

# Start dev container with replay
export MOCK_CAN_MODE=replay:normal_operation.json
ha core restart

# Validate recording JSON
python -m json.tool file.json > /dev/null && echo "Valid"
```

---

## Next Steps

- Read [data-model.md](./data-model.md) for entity details
- Review [contracts/](./contracts/) for JSON schema and interface spec
- See [plan.md](./plan.md) for full implementation plan
- Run `/speckit.tasks` to generate implementation task breakdown

---

**Quickstart Guide Status**: ✅ COMPLETE - Ready for use
