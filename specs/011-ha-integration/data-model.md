# Data Model: Home Assistant Integration

**Feature**: 011-ha-integration
**Date**: 2025-12-13

## Overview

This document defines the data structures and entities for the Home Assistant integration. The integration follows Home Assistant's entity model with a central coordinator managing heat pump communication.

## Core Data Structure

### BuderusData (Coordinator State)

Central data class returned by the coordinator on each poll.

```python
@dataclass
class BuderusData:
    """Heat pump data from coordinator poll."""

    temperatures: dict[str, float | None]
    # Keys: "outdoor", "supply", "return_temp", "dhw", "brine_in"
    # Values: temperature in Celsius, None if unavailable

    compressor_running: bool
    # True if compressor frequency > 0

    energy_blocked: bool
    # True if ADDITIONAL_BLOCKED parameter is set

    dhw_extra_duration: int
    # Hours remaining for DHW extra production (0-24)
    # 0 means not active

    heating_season_mode: int | None
    # 0=Winter (forced), 1=Auto, 2=Off (summer)
    # None if read failed

    dhw_program_mode: int | None
    # 0=Auto, 1=Always On, 2=Always Off
    # None if read failed
```

### Coordinator State

```python
class BuderusCoordinator:
    """Coordinator state fields."""

    port: str                    # Serial port path (e.g., "/dev/ttyACM0")
    _connected: bool             # Connection status
    _backoff_delay: int          # Current backoff delay in seconds
    _reconnect_task: Task | None # Active reconnect task
    _lock: asyncio.Lock          # Serialization lock for operations
```

## Home Assistant Entities

### Temperature Sensors (5 entities)

| Entity ID | Name | Device Class | Unit | State Class |
|-----------|------|--------------|------|-------------|
| `sensor.heat_pump_outdoor_temperature` | Outdoor Temperature | temperature | °C | measurement |
| `sensor.heat_pump_supply_temperature` | Supply Temperature | temperature | °C | measurement |
| `sensor.heat_pump_return_temperature` | Return Temperature | temperature | °C | measurement |
| `sensor.heat_pump_hot_water_temperature` | Hot Water Temperature | temperature | °C | measurement |
| `sensor.heat_pump_brine_inlet_temperature` | Brine Inlet Temperature | temperature | °C | measurement |

**State**: Float value in Celsius, or `unavailable` if connection lost.

### Compressor Binary Sensor (1 entity)

| Entity ID | Name | Device Class |
|-----------|------|--------------|
| `binary_sensor.heat_pump_compressor` | Compressor | running |

**State**: `on` (running) or `off` (stopped), or `unavailable` if connection lost.

### Energy Block Switch (1 entity)

| Entity ID | Name | Icon |
|-----------|------|------|
| `switch.heat_pump_energy_block` | Energy Block | mdi:power-plug-off |

**State**: `on` (blocking enabled) or `off` (normal operation)
**Actions**: `turn_on`, `turn_off`

### DHW Extra Duration Number (1 entity)

| Entity ID | Name | Icon | Range | Unit | Step |
|-----------|------|------|-------|------|------|
| `number.heat_pump_dhw_extra_duration` | DHW Extra Duration | mdi:water-boiler | 0-24 | h | 1 |

**State**: Integer hours (0 = not active, 1-24 = active with duration)
**Mode**: Slider for dashboard interaction
**Actions**: `set_value` (0-24)

### Heating Season Mode Select (bonus entity)

| Entity ID | Name | Icon | Options |
|-----------|------|------|---------|
| `select.heat_pump_heating_season_mode` | Heating Season Mode | mdi:home-thermometer | Winter (Forced), Automatic, Off (Summer) |

**State**: Current mode name
**Actions**: `select_option`

### DHW Program Mode Select (bonus entity)

| Entity ID | Name | Icon | Options |
|-----------|------|------|---------|
| `select.heat_pump_dhw_program_mode` | DHW Program Mode | mdi:water-boiler | Automatic, Always On, Always Off |

**State**: Current mode name
**Actions**: `select_option`

## Device Registration

All entities belong to a single device:

```python
DeviceInfo(
    identifiers={(DOMAIN, port)},  # e.g., ("buderus_wps", "/dev/ttyACM0")
    name="Heat Pump",              # Simple name per clarification
    manufacturer="Buderus",
    model="WPS Heat Pump",
    sw_version="0.1.0",
)
```

## Entity State Transitions

### Connection States

```
CONNECTED ──[USB disconnect]──► UNAVAILABLE
    │                               │
    │                               ▼
    │                      [backoff reconnect]
    │                               │
    └──────────────────────────────►┘
                                [success]
```

### Entity Availability

| Condition | Entity State |
|-----------|--------------|
| Coordinator connected, data valid | Shows value |
| Coordinator connected, data None | Shows `unknown` |
| Coordinator disconnected | Shows `unavailable` |

## Configuration Schema

```yaml
buderus_wps:
  port: "/dev/ttyACM0"       # Required: USB serial port
  scan_interval: 60          # Optional: Poll interval (10-300 seconds)
```

### Validation Rules

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| port | string | "/dev/ttyACM0" | Non-empty string |
| scan_interval | integer | 60 | Range 10-300 |

## Heat Pump Parameter Mapping

| Entity | Parameter | Index | Range | Notes |
|--------|-----------|-------|-------|-------|
| Temperatures | Various | - | - | From broadcast monitoring |
| Compressor | COMPRESSOR_FREQUENCY | - | 0-100 | From MenuAPI status |
| Energy Block | ADDITIONAL_BLOCKED | - | 0/1 | Read/write |
| DHW Extra | DHW_EXTRA_DURATION | - | 0-24 | Hours (read/write) |
| Heating Mode | HEATING_SEASON_MODE | 884 | 0-2 | Hardware verified |
| DHW Mode | DHW_PROGRAM_MODE | 489 | 0-2 | Hardware verified |

## Error Handling

### Connection Errors

- Log error with details
- Set all entities to `unavailable`
- Start exponential backoff reconnection (5s → 120s max)

### Read Errors

- Log warning
- Keep previous value or set to `None`
- Entity shows `unknown` state

### Write Errors

- Log error with details
- Raise `HomeAssistantError` for UI feedback
- Don't change entity state until refresh confirms change
