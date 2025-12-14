# Implementation Plan: Home Assistant Supervisor Add-on

**Branch**: `013-ha-supervisor-addon` | **Date**: 2025-12-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-ha-supervisor-addon/spec.md`

## Summary

Create a Docker-based Home Assistant Supervisor add-on that bridges the buderus_wps library to Home Assistant via MQTT Discovery. The add-on will run as a standalone container, connect to the heat pump via USB serial (USBtin), and automatically expose sensors and controls as Home Assistant entities.

## Technical Context

**Language/Version**: Python 3.11 (matches HA base image)
**Primary Dependencies**: buderus_wps library, paho-mqtt, pyserial
**Storage**: N/A (stateless service, HA stores entity state)
**Testing**: pytest (mock MQTT broker + mock serial)
**Target Platform**: Home Assistant OS/Supervised on amd64/aarch64
**Project Type**: Single project (add-on service)
**Performance Goals**: Sensor updates within 60s, command execution within 30s
**Constraints**: 500ms minimum between CAN commands, 60s MQTT buffer on disconnect
**Scale/Scope**: Single heat pump instance per add-on

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Library-First | PASS | Reuses existing buderus_wps library |
| Hardware Abstraction | PASS | USBtinAdapter already abstracted |
| Safety & Reliability | PASS | Existing validation + reconnection logic |
| Comprehensive Tests | REQUIRED | Must test MQTT bridge logic |
| Protocol Documentation | PASS | CAN protocol already documented |
| HA Integration Standards | REQUIRED | Must follow MQTT Discovery conventions |

## Project Structure

### Documentation (this feature)

```
specs/013-ha-supervisor-addon/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
addon/
├── config.yaml              # Supervisor add-on metadata & schema
├── Dockerfile               # Multi-arch Docker build
├── build.yaml               # Build configuration
├── DOCS.md                  # Add-on documentation
├── CHANGELOG.md             # Version history
├── translations/
│   └── en.yaml              # Configuration translations
├── rootfs/
│   └── etc/
│       └── s6-overlay/
│           └── s6-rc.d/
│               ├── buderus-wps/
│               │   ├── type         # "longrun"
│               │   ├── run          # Service script
│               │   └── finish       # Cleanup script
│               └── user/
│                   └── contents.d/
│                       └── buderus-wps  # Service registration
└── buderus_wps_addon/
    ├── __init__.py
    ├── main.py              # Entry point
    ├── mqtt_bridge.py       # MQTT Discovery publisher
    ├── entity_config.py     # Entity definitions
    └── config.py            # Configuration loader

tests/
├── unit/
│   ├── test_mqtt_bridge.py      # MQTT message formatting tests
│   └── test_entity_config.py    # Entity configuration tests
├── integration/
│   └── test_addon_service.py    # Service lifecycle tests
└── contract/
    └── test_mqtt_discovery.py   # MQTT Discovery payload validation
```

**Structure Decision**: Single-project add-on structure. The addon/ directory contains all add-on specific code, separate from the existing buderus_wps library which it imports.

## Architecture

### Data Flow

```
[Heat Pump] <--CAN--> [USBtin] <--Serial--> [Add-on Container]
                                                    |
                                            [BuderusService]
                                                    |
                                    +---------------+---------------+
                                    |               |               |
                            [BroadcastMonitor] [HeatPumpClient] [CommandQueue]
                                    |               |               |
                                    +---------------+---------------+
                                                    |
                                            [MQTTBridge]
                                                    |
                                    +---------------+---------------+
                                    |               |               |
                            [Discovery]        [State]        [Command]
                              Topics           Topics          Topics
                                    |               |               |
                                    +---------------+---------------+
                                                    |
                                    [MQTT Broker (Mosquitto)]
                                                    |
                                            [Home Assistant]
```

### Key Components

1. **BuderusService**: Main service class wrapping HeatPumpClient
   - Manages USBtinAdapter lifecycle
   - Handles reconnection on disconnect
   - Exposes read_sensors() and execute_command() methods

2. **MQTTBridge**: MQTT Discovery publisher
   - Publishes retained config messages on startup
   - Publishes state updates at configured interval
   - Subscribes to command topics for control entities
   - Handles broker disconnection with 60s buffer

3. **CommandQueue**: Serialized command execution
   - Queues write commands with 500ms minimum spacing
   - Validates values before transmission
   - Publishes command status responses

## MQTT Topic Structure

```
# Discovery (retained)
homeassistant/sensor/buderus_wps/outdoor_temp/config
homeassistant/sensor/buderus_wps/supply_temp/config
homeassistant/binary_sensor/buderus_wps/compressor/config
homeassistant/select/buderus_wps/heating_season_mode/config
homeassistant/select/buderus_wps/dhw_program_mode/config
homeassistant/switch/buderus_wps/holiday_mode/config
homeassistant/number/buderus_wps/extra_dhw_duration/config
homeassistant/number/buderus_wps/extra_dhw_target/config

# State (NOT retained)
buderus_wps/sensor/outdoor_temp/state
buderus_wps/sensor/supply_temp/state
buderus_wps/binary_sensor/compressor/state
buderus_wps/select/heating_season_mode/state
buderus_wps/select/dhw_program_mode/state
buderus_wps/switch/holiday_mode/state
buderus_wps/number/extra_dhw_duration/state
buderus_wps/number/extra_dhw_target/state

# Commands
buderus_wps/select/heating_season_mode/set
buderus_wps/select/dhw_program_mode/set
buderus_wps/switch/holiday_mode/set
buderus_wps/number/extra_dhw_duration/set
buderus_wps/number/extra_dhw_target/set

# Availability
buderus_wps/status  # "online" / "offline"
```

## Implementation Phases

### Phase 1: Add-on Scaffolding
1. Create addon/ directory structure
2. Write config.yaml with USB device mapping and MQTT config
3. Write Dockerfile for multi-arch build
4. Set up S6 overlay service scripts
5. Create translations/en.yaml

### Phase 2: MQTT Bridge Core
1. Implement entity_config.py with sensor/control definitions
2. Implement mqtt_bridge.py with Discovery message publishing
3. Implement config.py for Supervisor API integration
4. Write unit tests for MQTT message formatting

### Phase 3: Service Integration
1. Implement main.py service loop
2. Integrate BroadcastMonitor for temperature readings
3. Integrate HeatPumpClient for control commands
4. Implement CommandQueue with rate limiting
5. Write integration tests for service lifecycle

### Phase 4: Error Handling & Reconnection
1. USB disconnect detection and reconnection
2. MQTT broker disconnect handling with 60s buffer
3. Health check endpoint for Supervisor
4. Comprehensive logging with configurable verbosity

### Phase 5: Documentation & Testing
1. Write DOCS.md with installation instructions
2. Write CHANGELOG.md
3. Create acceptance tests for all user stories
4. Validate against all success criteria

## Entity Definitions

### Sensors (Read-Only)

| Entity ID | Type | Parameter/Source | Unit |
|-----------|------|------------------|------|
| outdoor_temp | sensor | Broadcast idx=12 | °C |
| supply_temp | sensor | Broadcast idx=13 | °C |
| return_temp | sensor | Broadcast idx=14 | °C |
| dhw_temp | sensor | Broadcast idx=15 | °C |
| buffer_top_temp | sensor | Broadcast idx=16 | °C |
| buffer_bottom_temp | sensor | Broadcast idx=17 | °C |
| compressor | binary_sensor | MenuAPI.status.compressor_running | - |

### Controls (Read/Write)

| Entity ID | Type | Parameter | Options/Range |
|-----------|------|-----------|---------------|
| heating_season_mode | select | HEATING_SEASON_MODE (idx=884) | Winter, Automatic, Summer |
| dhw_program_mode | select | DHW_PROGRAM_MODE (idx=489) | Automatic, Always On, Always Off |
| holiday_mode | switch | HOLIDAY_ACTIVE_GLOBAL | On/Off |
| extra_dhw_duration | number | via MenuAPI | 0-48 hours |
| extra_dhw_target | number | via MenuAPI | 50.0-65.0 °C |

## Configuration Schema

```yaml
# config.yaml schema
schema:
  serial_device: str
  mqtt_host: str?
  mqtt_port: int(1883)?
  mqtt_username: str?
  mqtt_password: str?
  scan_interval: int(60)?
  log_level: list(debug|info|warning|error)?

options:
  serial_device: /dev/ttyACM0
  scan_interval: 60
  log_level: info
```

## Critical Files

Files requiring direct implementation work:

| File | Purpose |
|------|---------|
| `addon/config.yaml` | Add-on metadata, USB device mapping, MQTT config schema |
| `addon/Dockerfile` | Multi-arch build using ghcr.io/home-assistant/amd64-base-python |
| `addon/buderus_wps_addon/main.py` | Service entry point, polling loop |
| `addon/buderus_wps_addon/mqtt_bridge.py` | MQTT Discovery message publishing |
| `addon/buderus_wps_addon/entity_config.py` | Sensor/control entity definitions |
| `addon/rootfs/etc/s6-overlay/s6-rc.d/buderus-wps/run` | S6 service script |

## Dependencies on Existing Code

The add-on reuses these components from buderus_wps library:

| Component | Usage |
|-----------|-------|
| USBtinAdapter | Serial CAN communication |
| HeatPumpClient | Parameter read/write |
| ParameterRegistry | Parameter definitions |
| BroadcastMonitor | Passive temperature reading |
| MenuAPI | Compressor status, DHW control |
| get_default_sensor_map() | Temperature sensor mappings |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| USB device path changes | Support /dev/serial/by-id/ paths |
| MQTT broker unavailable | 60s message buffer, graceful degradation |
| CAN bus timeouts | Exponential backoff, availability marking |
| Concurrent command conflicts | CommandQueue with 500ms spacing |

## Complexity Tracking

*No constitution violations requiring justification*
