# Buderus WPS Heat Pump CAN Bus Communication Library

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Python library for communicating with Buderus WPS heat pumps via CAN bus using USBtin adapters.

## Features

- ✅ CAN bus communication via USBtin adapter (SLCAN protocol)
- ✅ Type-safe message handling with validation
- ✅ Temperature and integer value encoding/decoding
- ✅ Comprehensive error handling with diagnostic messages
- ✅ Context manager support for resource cleanup
- ✅ 100% test coverage

## Requirements

- Python 3.9 or higher
- USBtin CAN adapter (or compatible SLCAN adapter)
- Buderus WPS heat pump with CAN bus connection

## Installation

```bash
pip install buderus-wps
```

### Development Installation

```bash
git clone https://github.com/reinlemmens/buderus-wps-ha.git
cd buderus-wps-ha
pip install -e ".[dev]"
```

## Quick Start

```python
from buderus_wps import USBtinAdapter, CANMessage, ValueEncoder

# Connect to heat pump
with USBtinAdapter('/dev/ttyACM0') as adapter:
    # Create temperature read request
    request = CANMessage(
        arbitration_id=0x31D011E9,
        data=b'\x00',
        is_extended_id=True
    )

    # Send request and receive response
    response = adapter.send_frame(request)

    # Decode temperature value
    temp_celsius = ValueEncoder.decode_temperature(response.data, 'temp')
    print(f"Outdoor Temperature: {temp_celsius}°C")
```

## CLI (local USBtin)

After `pip install -e .`, a `wps-cli` command is available:

```bash
wps-cli read ACCESS_LEVEL                 # read by name (uses /dev/ttyACM0, 115200)
wps-cli write ACCESS_LEVEL 2              # write (validates range/format)
wps-cli list --filter ACCESS              # list parameters with optional filter
wps-cli dump --json > params.json         # dump all parameters with decoded/raw values
wps-cli --read-only write ACCESS_LEVEL 2  # blocks writes in read-only/dry-run
```

## Home Assistant Integration

A custom integration is available for monitoring and controlling your heat pump directly from Home Assistant.

### Features

- ✅ 5 temperature sensors (Outdoor, Supply, Return, DHW, Brine Inlet)
- ✅ Compressor status binary sensor
- ✅ Energy blocking switch (disable heating during peak rates)
- ✅ DHW extra production control (boost hot water on demand)
- ✅ Automatic reconnection with exponential backoff
- ✅ Fully tested (117 tests, all passing)

### Installation via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots menu in the top right corner
3. Select "Custom repositories"
4. Add repository URL: `https://github.com/reinlemmens/buderus-wps-ha`
5. Select category: "Integration"
6. Click "Add"
7. Search for "Buderus WPS" and click "Download"
8. Restart Home Assistant
9. Go to Settings → Devices & Services → Add Integration → Buderus WPS

### Manual Installation (Alternative)

1. Copy the `custom_components/buderus_wps` directory to your Home Assistant `config/custom_components/` folder
2. Add configuration to `configuration.yaml`:

```yaml
buderus_wps:
  port: /dev/ttyACM0        # USB serial port (required)
  scan_interval: 60         # Update interval in seconds (optional, default: 60, range: 10-300)
```

3. Restart Home Assistant
4. Verify 8 entities appear (5 sensors + 1 binary_sensor + 1 switch + 1 number)

### Entity Names

All entities are prefixed with "Heat Pump" for easy identification:

- `sensor.heat_pump_outdoor_temperature`
- `sensor.heat_pump_supply_temperature`
- `sensor.heat_pump_return_temperature`
- `sensor.heat_pump_hot_water_temperature`
- `sensor.heat_pump_brine_inlet_temperature`
- `binary_sensor.heat_pump_compressor`
- `switch.heat_pump_energy_block`
- `number.heat_pump_dhw_extra_duration`

### Example Automations

**Block heating during peak electricity rates:**
```yaml
automation:
  - alias: "Block heat pump during peak rates"
    trigger:
      - platform: time
        at: "17:00:00"  # Peak starts
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.heat_pump_energy_block

  - alias: "Resume heating after peak rates"
    trigger:
      - platform: time
        at: "21:00:00"  # Peak ends
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.heat_pump_energy_block
```

**Boost hot water before morning shower:**
```yaml
automation:
  - alias: "Morning hot water boost"
    trigger:
      - platform: time
        at: "05:30:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.heat_pump_dhw_extra_duration
        data:
          value: 2  # Run for 2 hours
```

### Documentation

- [Feature Specification](specs/011-ha-integration/spec.md)
- [Implementation Plan](specs/011-ha-integration/plan.md)
- [Data Model](specs/011-ha-integration/data-model.md)

## Finding Your Serial Port

**Linux/macOS:**
```bash
ls /dev/tty*
# Look for /dev/ttyACM0 or /dev/tty.usbmodem*
```

**Windows:**
```python
import serial.tools.list_ports
for port in serial.tools.list_ports.comports():
    print(f"{port.device}: {port.description}")
```

## Common Usage Patterns

### Error Handling

```python
from buderus_wps import USBtinAdapter, CANMessage
from buderus_wps.exceptions import ConnectionError, TimeoutError

try:
    with USBtinAdapter('/dev/ttyACM0') as adapter:
        response = adapter.send_frame(request)
except FileNotFoundError:
    print("Serial port not found. Check USB connection.")
except TimeoutError:
    print("No response from heat pump. Check CAN bus connection.")
except ConnectionError as e:
    print(f"Connection error: {e}")
```

### Temperature Encoding

```python
from buderus_wps import ValueEncoder

# Encode temperature (3 formats available)
temp_bytes = ValueEncoder.encode_temperature(22.5, 'temp')       # 2 bytes, 0.1°C resolution
temp_bytes = ValueEncoder.encode_temperature(22.5, 'temp_byte')  # 1 byte, 0.5°C resolution
temp_bytes = ValueEncoder.encode_temperature(60.0, 'temp_uint')  # 1 byte, 1°C resolution

# Decode temperature
temp_celsius = ValueEncoder.decode_temperature(b'\x01\x23', 'temp')  # 29.1°C
```

## Permissions (Linux/macOS)

Add your user to the dialout group for serial port access:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

## Troubleshooting

### Port Access Denied
```bash
sudo usermod -a -G dialout $USER
```

### Port Not Found
- Verify USB adapter is connected: `ls /dev/tty*`
- Check driver installation
- Try different USB port

### No Response / Timeout
- Check CAN bus connection to heat pump
- Verify heat pump is powered on
- Check CAN bus termination (120Ω resistors)
- Verify correct CAN bitrate (125 kbps for Buderus)

## Architecture

### Library-First Design

- **buderus_wps**: Core library (independently usable)
- **buderus_wps_cli**: Command-line tool
- **Home Assistant integration**: Smart home plugin (custom_components/buderus_wps)

### Constitution Principles

This project follows strict development principles:

1. **Library-First**: Pure Python library, minimal dependencies
2. **Protocol Fidelity**: SLCAN protocol compliance, CAN 2.0A/2.0B specs
3. **Safety**: Input validation, comprehensive error handling
4. **Test-First**: 100% coverage for all functionality
5. **Documentation**: Protocol and API documentation

## Development

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m contract

# Generate HTML coverage report
pytest --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
black buderus_wps tests

# Lint code
ruff check buderus_wps

# Type checking
mypy buderus_wps
```

## Project Structure

```
buderus_wps/
├── __init__.py          # Package exports
├── can_message.py       # CAN message dataclass
├── can_adapter.py       # USBtin adapter
├── value_encoder.py     # Value encoding utilities
└── exceptions.py        # Exception hierarchy

tests/
├── unit/                # Unit tests
├── integration/         # Integration tests (mocked)
└── contract/            # Protocol compliance tests
```

## Documentation

- [Quickstart Guide](specs/001-can-usb-serial/quickstart.md)
- [API Reference](specs/001-can-usb-serial/contracts/library_api.md)
- [Data Model](specs/001-can-usb-serial/data-model.md)
- [Research & Decisions](specs/001-can-usb-serial/research.md)

## Contributing

This project follows test-first development:

1. Write tests first (they should fail)
2. Implement minimum code to pass tests
3. Refactor while keeping tests green
4. Verify 100% coverage

See [Implementation Tasks](specs/001-can-usb-serial/tasks.md) for current work.

## License

MIT License - see LICENSE file for details

## References

- **SLCAN Protocol**: Lawicel AB ASCII protocol documentation
- **CAN 2.0 Specification**: ISO 11898-1:2015
- **USBtin Hardware**: fischl.de/usbtin
- **FHEM Reference**: 26_KM273v018.pm

## Support

- **Issues**: [GitHub Issues](https://github.com/reinlemmens/buderus-wps-ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/reinlemmens/buderus-wps-ha/discussions)

---

**Status**: Alpha - Active Development

This library implements Feature 001 (CAN over USB Serial Connection) from the project roadmap.
