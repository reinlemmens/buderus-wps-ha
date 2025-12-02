# Quickstart: Sensor Configuration

**Feature**: 009-sensor-config
**Date**: 2024-12-02

## Overview

This feature provides centralized configuration for CAN broadcast sensor mappings and installation-specific settings.

## Basic Usage

### Using Default Configuration

The system works out of the box with built-in defaults:

```python
from buderus_wps import load_config, get_default_sensor_map

# Load configuration (uses defaults if no config file found)
config = load_config()

# Get sensor mappings for broadcast monitoring
sensor_map = config.get_sensor_map()
# Returns: {(0x0402, 38): "outdoor", (0x0060, 58): "dhw", ...}

# Get display label for a sensor
label = config.get_label("outdoor")
# Returns: "Outdoor Temperature"
```

### Creating a Configuration File

Create `~/.config/buderus-wps/config.yaml`:

```yaml
# Buderus WPS Configuration
version: "1.0"

# Heating circuits for your installation
circuits:
  - number: 1
    type: ventilo
    apartment: "Apartment 0"
    label: "Living Room Fan Coil"
  - number: 2
    type: floor_heating
    apartment: "Apartment 1"
  - number: 3
    type: floor_heating
    apartment: "Apartment 0"
  - number: 4
    type: floor_heating
    apartment: "Apartment 2"

# DHW distribution (which apartments get hot water)
dhw:
  apartments:
    - "Apartment 0"

# Optional: custom sensor labels
labels:
  outdoor: "Outside Air"
  dhw: "Hot Water Tank"
```

### Loading Custom Configuration

```python
from buderus_wps import load_config

# Explicit path
config = load_config("/path/to/my-config.yaml")

# Or use environment variable
# export BUDERUS_WPS_CONFIG=/path/to/config.yaml
config = load_config()
```

## TUI Integration

The TUI automatically loads configuration at startup:

```bash
# Uses default config search path
./start-tui.sh

# Or specify config file
./start-tui.sh --config /path/to/config.yaml
```

## Common Tasks

### Check Circuit Configuration

```python
config = load_config()

# Get specific circuit
circuit = config.get_circuit(1)
print(f"Circuit 1: {circuit.circuit_type}, serves {circuit.apartment}")

# Get circuits by apartment
circuits = config.get_circuits_by_apartment("Apartment 0")
for c in circuits:
    print(f"  Circuit {c.number}: {c.circuit_type}")
```

### Check DHW Availability

```python
config = load_config()

# Check if apartment has hot water access
if config.dhw.has_access("Apartment 0"):
    print("Apartment 0 has DHW")
if not config.dhw.has_access("Apartment 1"):
    print("Apartment 1 does not have DHW")
```

### Custom Sensor Mappings

If your installation has different CAN broadcast addresses:

```yaml
sensor_mappings:
  # Override default outdoor sensor address
  - base: 0x0403
    idx: 42
    sensor: outdoor
```

## Error Handling

The system gracefully handles configuration errors:

- **Missing file**: Uses built-in defaults, logs warning
- **Invalid syntax**: Uses defaults, logs error with line number
- **Invalid values**: Skips invalid entries, logs warning, uses remaining valid entries

```python
import logging
logging.basicConfig(level=logging.WARNING)

config = load_config()
# Warnings logged for any issues
```

## File Search Order

Configuration files are searched in this order:

1. Explicit `--config` path or `load_config(path=...)`
2. `BUDERUS_WPS_CONFIG` environment variable
3. `./buderus-wps.yaml` (current directory)
4. `~/.config/buderus-wps/config.yaml` (XDG standard)
5. Built-in defaults (no file required)
