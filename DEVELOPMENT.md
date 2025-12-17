# Development Guide

This guide explains how to set up your development environment and run tests for the Buderus WPS Heat Pump integration.

## Quick Start

### Using VSCode DevContainer (Recommended)

1. Open the project in VSCode
2. Click "Reopen in Container" when prompted (or use Command Palette: `Dev Containers: Reopen in Container`)
3. Wait for the container to build and the bootstrap script to run
4. The virtual environment will be automatically activated in all new terminals

### Manual Setup (Without DevContainer)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
pip install homeassistant>=2024.3.0
```

## Project Architecture

This project follows a **library-first architecture**:

```
buderus_wps/              # Core library (CAN protocol, heat pump control)
buderus_wps_cli/          # CLI tool (wraps library)
custom_components/        # Home Assistant integration (uses library)
tests/
├── unit/                 # Unit tests (pure logic, fully mocked)
├── integration/          # Integration tests (mocked hardware)
├── contract/             # Protocol contract tests (FHEM compatibility)
├── acceptance/           # End-to-end acceptance tests (mocked hardware)
└── hil/                  # Hardware-in-loop tests (REQUIRES PHYSICAL DEVICE)
```

## Running Tests

### Without Physical Hardware (Recommended for Development)

All tests use comprehensive mocks by default. No USB adapter or heat pump required.

```bash
# Run all tests except hardware-in-loop (HIL)
pytest --ignore=tests/hil/

# Run specific test layers
pytest tests/unit/                # Unit tests only
pytest tests/integration/         # Integration tests
pytest tests/acceptance/          # Acceptance tests

# Run Home Assistant integration tests only
pytest tests/unit/test_ha_*.py tests/integration/test_ha_*.py tests/acceptance/test_ha_*.py

# Or use convenience scripts
./scripts/test-all.sh             # All non-HIL tests
./scripts/test-ha.sh              # HA integration tests only
```

### With Physical Hardware (Optional)

Hardware-in-loop (HIL) tests require:
- USBtin CAN adapter connected at `/dev/ttyACM0` (or set `USBTIN_PORT` env var)
- Buderus WPS heat pump broadcasting on CAN bus

```bash
# Run HIL tests
RUN_HIL_TESTS=1 pytest tests/hil/

# Or use convenience script
./scripts/test-hil.sh
```

**Note:** HIL tests are automatically skipped unless `RUN_HIL_TESTS=1` is set.

## Test Coverage

```bash
# Run tests with coverage report
pytest --cov=buderus_wps --cov-report=html

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Coverage targets:**
- Library code (`buderus_wps`, `buderus_wps_cli`): 100%
- HA integration (`custom_components`): Excluded from coverage (uses mocks)

## Code Quality Tools

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy buderus_wps buderus_wps_cli

# Run all quality checks
black . && ruff check . && mypy buderus_wps buderus_wps_cli
```

## Mocking Strategy

The project uses comprehensive mocks to allow testing without physical hardware:

### Home Assistant Mocks (`tests/conftest.py`)

- **HA Core**: `homeassistant`, `HomeAssistant`, `ConfigEntry`, `DataUpdateCoordinator`
- **Entities**: `SensorEntity`, `BinarySensorEntity`, `SwitchEntity`, `NumberEntity`
- **Helpers**: `DeviceInfo`, `device_registry`, `entity_platform`

### Hardware Mocks (`tests/conftest.py`)

- **`mock_usb_adapter`**: Mocks USBtin CAN adapter (serial communication)
- **`mock_heat_pump_client`**: Mocks parameter read/write operations
- **`mock_broadcast_monitor`**: Mocks CAN broadcast collection
- **`mock_menu_api`**: Mocks menu navigation and status API
- **`mock_coordinator`**: Mocks HA DataUpdateCoordinator with test data

### Example: Using Mocks in Tests

```python
import pytest

def test_read_temperature(mock_heat_pump_client):
    """Test reading temperature parameter."""
    # Mock returns predetermined value
    mock_heat_pump_client.read_parameter.return_value = {"decoded": 25.5}

    # Your test code here
    result = mock_heat_pump_client.read_parameter("OUTDOOR_TEMP")
    assert result["decoded"] == 25.5
```

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and write tests (TDD recommended)
pytest tests/unit/test_my_feature.py

# Run all tests
pytest --ignore=tests/hil/

# Format and lint
black . && ruff check .

# Commit
git commit -m "feat: add my feature"
```

### 2. Testing with Real Hardware (Optional)

```bash
# Connect USBtin adapter to /dev/ttyACM0

# Run HIL tests to verify protocol
RUN_HIL_TESTS=1 pytest tests/hil/

# Mark test as hardware-verified in docstring
"""
Hardware Verified: 2025-12-16 on Raspberry Pi with USBtin
"""
```

### 3. Home Assistant Integration Development

```bash
# Run HA integration tests
./scripts/test-ha.sh

# End-to-end validation in actual HA instance (REQUIRED before release)
# See "End-to-End Validation" section below
```

## End-to-End Validation (Required Before Release)

**CRITICAL**: Pytest tests alone are insufficient. All releases MUST be validated in a running Home Assistant instance.

### Why E2E Testing is Required

- **Pytest tests use mocks**: They don't catch runtime errors like missing attributes, import failures, or integration initialization issues
- **Real HA environment**: Only an actual HA instance can validate the complete startup sequence, entity registration, and coordinator instantiation
- **User experience**: E2E testing verifies what users will actually see and experience

### E2E Validation Checklist

This checklist is **MANDATORY** before creating any release (major, minor, or patch):

#### 1. Test the ACTUAL Release Artifact

**CRITICAL**: You MUST test the actual release zip file, not the development directory!

Development code ≠ Release artifact:
- ❌ **Development directory** may have different imports/structure than release
- ✅ **Release zip** is what users actually install via HACS

```bash
# Step 1: Build the release (creates buderus-wps-ha-vX.Y.Z.zip)
./scripts/build-release.sh vX.Y.Z

# Step 2: Extract to temporary location
unzip -q buderus-wps-ha-vX.Y.Z.zip -d /tmp/release-test

# Step 3: Verify bundled library exists
ls /tmp/release-test/custom_components/buderus_wps/buderus_wps/
# Should show: __init__.py, can_adapter.py, heat_pump.py, etc. (20 files)

# Step 4: Install release artifact in HA (OVERWRITES development version)
# In devcontainer:
rm -rf /config/custom_components/buderus_wps
cp -r /tmp/release-test/custom_components/buderus_wps /config/custom_components/

# In standalone HA:
rm -rf ~/.homeassistant/custom_components/buderus_wps
cp -r /tmp/release-test/custom_components/buderus_wps ~/.homeassistant/custom_components/

# Step 5: Restart Home Assistant to load release artifact
# Check logs during startup for import errors
```

**Why this is critical**:
- v1.3.1 bug: Development version had absolute imports, release had relative imports
- Testing dev version would miss this discrepancy
- Only testing actual zip catches packaging/bundling issues

#### 2. Monitor Startup Logs

```bash
# Watch logs for errors during HA startup
tail -f /config/home-assistant.log

# Or in HA UI: Settings > System > Logs
# Filter for "buderus_wps" to see integration-specific logs
```

**Check for:**
- ✅ No `AttributeError`, `ImportError`, or `ModuleNotFoundError`
- ✅ No exceptions during coordinator initialization
- ✅ Integration loads successfully with log: `"Successfully connected to heat pump"`

#### 3. Create Config Entry via UI

```bash
# In Home Assistant UI:
# 1. Settings > Devices & Services > Add Integration
# 2. Search for "Buderus WPS Heat Pump"
# 3. Configure serial port (or use mock device if testing)
# 4. Submit configuration
```

**Check for:**
- ✅ Config flow completes without errors
- ✅ Device appears in device registry
- ✅ No error notifications in UI

#### 4. Verify Entities Exist

```bash
# In Home Assistant UI:
# 1. Settings > Devices & Services > Buderus WPS Heat Pump
# 2. Click on the device
# 3. Verify all expected entities are present
```

**Expected entities (as of v1.3.x):**
- ✅ 5 temperature sensors (Outdoor, Supply, Return, DHW, Brine Inlet)
- ✅ 1 binary sensor (Compressor Running)
- ✅ 1 switch (Energy Blocking)
- ✅ 1 number (DHW Extra Duration)
- ✅ All entities show values (or "unavailable" if no device connected)
- ✅ No entities stuck in "Unknown" state after first data fetch

#### 5. Check Entity Attributes

```bash
# In Home Assistant UI, click on any temperature sensor
# Navigate to "Attributes" section
```

**Check for (as of v1.3.x with indefinite caching):**
- ✅ `last_update_age_seconds` attribute present
- ✅ `data_is_stale` attribute present (true/false)
- ✅ `last_successful_update` timestamp present (ISO 8601 format)
- ✅ No missing or undefined attributes

#### 6. Test State Changes

```bash
# If physical device is connected:
# 1. Toggle the Energy Blocking switch
# 2. Verify switch state updates
# 3. Check logs for write operation confirmation

# If no device (testing with mocks):
# 1. Verify entities show "unavailable" gracefully
# 2. No crash or error spam in logs
```

#### 7. Test Error Handling

```bash
# Simulate connection loss (if using physical device):
# 1. Unplug USB adapter
# 2. Wait for coordinator to detect failure (check logs)
# 3. Verify entities retain last known values with staleness indicators
# 4. Reconnect USB adapter
# 5. Verify entities update to fresh values
```

**Check for:**
- ✅ No crashes during connection loss
- ✅ Entities retain last values (not "Unknown")
- ✅ `data_is_stale` becomes `true` during disconnection
- ✅ `data_is_stale` becomes `false` after reconnection
- ✅ Exponential backoff reconnection works (check logs)

#### 8. Review HA Logs for Warnings

```bash
# Check for any unexpected warnings or errors
grep -i "buderus_wps" /config/home-assistant.log | grep -E "(ERROR|WARNING|CRITICAL)"
```

**Check for:**
- ✅ No unexpected errors or warnings
- ✅ Only expected warnings (e.g., "Not connected, returning stale data" during disconnection)
- ✅ No attribute access errors, import errors, or type errors

### E2E Validation Sign-Off

Before creating a release, document E2E validation in commit message or release notes:

```
Tested in Home Assistant 2024.12.0:
✅ Integration loads without errors
✅ All 8 entities created successfully
✅ Entity attributes show staleness metadata
✅ Coordinator handles connection failures gracefully
✅ No AttributeError or runtime exceptions
✅ Logs clean (no unexpected errors)

Environment: HA Supervisor devcontainer on [OS/Platform]
```

### When to Skip E2E Testing

**NEVER skip E2E testing for releases.** Even "trivial" changes can have unintended consequences.

### Automation (Future Enhancement)

Consider adding automated E2E tests using Home Assistant's test framework:
- `pytest-homeassistant-custom-component` for automated integration testing
- GitHub Actions workflow to spin up HA instance and run E2E tests
- Prevent releases if E2E tests fail

## Pytest Markers

Tests are marked with categories:

```bash
# Run by marker
pytest -m unit                # Unit tests only
pytest -m integration         # Integration tests only
pytest -m contract            # Protocol contract tests
pytest -m acceptance          # Acceptance tests
```

## Troubleshooting

### Virtual Environment Not Activated

```bash
# Manually activate venv
source venv/bin/activate

# Or run commands with full path
./venv/bin/pytest tests/
```

### Home Assistant Import Errors

```bash
# Ensure HA is installed in venv
./venv/bin/pip list | grep homeassistant

# Reinstall if needed
./venv/bin/pip install homeassistant>=2024.3.0
```

### Coverage "No Data Collected" Warning

This happens when running HA integration tests that only use mocks. It's expected and can be ignored. The coverage config excludes `custom_components/*` from measurement.

### HIL Tests Failing

HIL tests require physical hardware. If you don't have a USB adapter:
- HIL tests are automatically skipped (this is normal)
- All functionality is testable via mocks

### Permission Denied on Scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh
```

## Additional Resources

- [README.md](README.md) - Project overview
- [CLAUDE.md](CLAUDE.md) - Instructions for Claude Code
- [.specify/memory/constitution.md](.specify/memory/constitution.md) - Project governance
- [specs/](specs/) - Feature specifications

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) for project architecture and principles
2. Follow TDD: Write tests before implementation
3. Ensure 100% test coverage for described functionality
4. Run all quality checks before committing
5. Update documentation as needed

## Getting Help

- **Issues**: https://github.com/reinlemmens/buderus-wps-ha/issues
- **Discussions**: Check GitHub Discussions (if enabled)
- **FHEM Reference**: See `fhem/26_KM273v018.pm` for protocol details
