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

# Test in actual HA instance (optional)
# 1. Copy custom_components/buderus_wps to HA config/custom_components/
# 2. Restart Home Assistant
# 3. Add integration via UI
```

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
