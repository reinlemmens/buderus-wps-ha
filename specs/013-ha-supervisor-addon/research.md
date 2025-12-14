# Research: Home Assistant Supervisor Add-on

**Feature**: 013-ha-supervisor-addon
**Date**: 2025-12-13

## Overview

This document captures research findings for implementing a Home Assistant Supervisor add-on for the Buderus WPS heat pump integration.

## Home Assistant Add-on Architecture

### Required Files

| File | Purpose | Required |
|------|---------|----------|
| `config.yaml` | Add-on metadata, permissions, configuration schema | Yes |
| `Dockerfile` | Container build configuration | Yes |
| `build.yaml` | Additional build options | Optional |
| `DOCS.md` | Documentation shown in Add-on Store | Recommended |
| `CHANGELOG.md` | Version history | Recommended |
| `translations/en.yaml` | Configuration parameter descriptions | Recommended |

### S6 Overlay Process Supervision

Home Assistant add-ons use S6 overlay for process supervision. Key features:

1. **Three Stages**:
   - Stage 1: Container initialization (automatic)
   - Stage 2: Service execution
   - Stage 3: Graceful shutdown

2. **Service Structure**:
```
/etc/s6-overlay/s6-rc.d/
├── my-service/
│   ├── type              # "longrun" or "oneshot"
│   ├── run               # Executable script
│   ├── finish            # Optional cleanup
│   └── dependencies      # Service dependencies
└── user/
    └── contents.d/
        └── my-service    # Empty file registering service
```

3. **Run Script Best Practices**:
   - Use `#!/usr/bin/with-contenv bashio` shebang
   - Inherit environment from s6-supervise
   - NOT run as daemons (s6 handles supervision)
   - Use `exec` for final process replacement
   - s6-supervise automatically restarts failed services

### USB Device Access

**Device Passthrough in config.yaml**:
```yaml
devices:
  - "/dev/ttyUSB0:/dev/ttyUSB0:rwm"
  - "/dev/ttyACM0:/dev/ttyACM0:rwm"
```

**Stable Device Paths**:
- Use `/dev/serial/by-id/usb-[VendorID]_[ProductID]_[SerialNumber]-if00-port0`
- More stable than `/dev/ttyUSB0` which can change on reboot

### MQTT Integration

**Auto-Discovery via Supervisor API**:
- Default broker hostname: `core-mosquitto` (internal Docker network)
- Default port: 1883
- Bashio helpers: `bashio::config`, `bashio::services mqtt`

**Birth Message Pattern**:
1. Subscribe to `homeassistant/status`
2. On "online" message → publish discovery configs
3. Ensures entities re-discovered after HA restart

## MQTT Discovery Protocol

### Message Types

1. **Config Messages** (retained):
   - Topic: `homeassistant/<type>/<device_id>/<entity_id>/config`
   - Payload: JSON with entity configuration
   - Must be retained for HA restart recovery

2. **State Messages** (NOT retained):
   - Topic: `<prefix>/<type>/<entity_id>/state`
   - Payload: Current value
   - Must NOT be retained (causes stale data issues)

3. **Command Messages**:
   - Topic: `<prefix>/<type>/<entity_id>/set`
   - Payload: New value to set

### Discovery Payload Structure

**Required Fields**:
- `unique_id`: Unique identifier for entity
- `name`: Human-readable name
- `state_topic`: Topic for state updates
- `device`: Device grouping information

**Optional Fields**:
- `device_class`: Semantic type (temperature, running, etc.)
- `unit_of_measurement`: Display unit
- `availability_topic`: Online/offline status
- `command_topic`: For controllable entities
- `value_template`: Jinja2 template for value extraction

### Entity Types

| Type | HA Platform | Use Case |
|------|-------------|----------|
| sensor | sensor | Temperature readings |
| binary_sensor | binary_sensor | Compressor on/off |
| switch | switch | On/off toggles |
| select | select | Multi-option selection |
| number | number | Numeric ranges |

## Existing Library Integration

### USBtinAdapter

```python
adapter = USBtinAdapter(
    port='/dev/ttyACM0',
    baudrate=115200,
    timeout=5.0,
    read_only=False
)
with adapter:
    # Operations...
```

**Features**:
- Thread-safe (`_op_lock`)
- Context manager support
- Auto-cleanup via atexit handler

### HeatPumpClient

```python
client = HeatPumpClient(adapter, registry)

# Read
result = client.read_parameter("OUTDOOR_TEMPERATURE")
# Returns: {"name": ..., "decoded": 12.4, "raw": ...}

# Write
client.write_value("HEATING_SEASON_MODE", 2)  # Summer mode
```

**Error Handling**:
- `ParameterNotFoundError`: Parameter doesn't exist
- `PermissionError`: Attempt to write read-only
- `TimeoutError`: CAN bus timeout (5s)
- `DeviceCommunicationError`: Wrong response ID

### BroadcastMonitor

```python
monitor = BroadcastMonitor(adapter)
cache = monitor.collect(duration=5.0)
temps = cache.get_temperatures()
```

**Best for**: Temperature readings (more reliable than RTR requests)

### MenuAPI

```python
menu = MenuAPI(client)
status = menu.status
compressor_running = status.compressor_running
```

**Provides**: High-level control interface

## Docker Base Images

**Recommended**: `ghcr.io/home-assistant/{arch}-base-python:3.11`

**Architectures**:
- `amd64` - Intel/AMD 64-bit
- `aarch64` - ARM 64-bit (Raspberry Pi 4)
- `armhf` - ARM 32-bit (older Pi)
- `armv7` - ARM v7 32-bit
- `i386` - Intel 32-bit (legacy)

**Multi-arch Build**:
```yaml
# build.yaml
build_from:
  amd64: ghcr.io/home-assistant/amd64-base-python:3.11
  aarch64: ghcr.io/home-assistant/aarch64-base-python:3.11
```

## Rate Limiting

**CAN Bus Constraints**:
- Minimum 500ms between commands
- Queue commands for sequential processing
- Timeout handling with exponential backoff

**MQTT Buffer**:
- Buffer messages for 60 seconds during broker disconnect
- Discard oldest messages if buffer fills
- Log warnings but don't crash

## References

- [Home Assistant Add-on Configuration](https://developers.home-assistant.io/docs/add-ons/configuration/)
- [S6 Overlay Documentation](https://github.com/just-containers/s6-overlay)
- [MQTT Discovery Protocol](https://www.home-assistant.io/integrations/mqtt/#discovery)
- [Home Assistant MQTT Sensor](https://www.home-assistant.io/integrations/sensor.mqtt/)
