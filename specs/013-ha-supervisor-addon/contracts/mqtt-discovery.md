# MQTT Discovery Contract

**Feature**: 013-ha-supervisor-addon
**Date**: 2025-12-13

## Overview

This contract defines the MQTT Discovery message format for automatic entity creation in Home Assistant.

## Discovery Topic Structure

```
homeassistant/<component>/<object_id>/config
```

Where:
- `<component>`: Entity platform (sensor, binary_sensor, switch, select, number)
- `<object_id>`: Unique object identifier (e.g., `buderus_wps/outdoor_temp`)

## Device Information

All entities share a common device block:

```json
{
  "device": {
    "identifiers": ["buderus_wps"],
    "name": "Buderus WPS Heat Pump",
    "manufacturer": "Buderus",
    "model": "WPS",
    "sw_version": "1.0.0"
  }
}
```

## Availability Configuration

All entities include availability configuration:

```json
{
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline"
}
```

## Entity Contracts

### Temperature Sensor

**Discovery Topic**: `homeassistant/sensor/buderus_wps/<entity_id>/config`

**Payload Schema**:
```json
{
  "unique_id": "buderus_wps_<entity_id>",
  "name": "<display_name>",
  "device_class": "temperature",
  "unit_of_measurement": "°C",
  "state_class": "measurement",
  "state_topic": "buderus_wps/sensor/<entity_id>/state",
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": { ... }
}
```

**State Topic**: `buderus_wps/sensor/<entity_id>/state`
**State Payload**: Float value as string (e.g., "12.4")

**Entities**:
| entity_id | name |
|-----------|------|
| outdoor_temp | Outdoor Temperature |
| supply_temp | Supply Temperature |
| return_temp | Return Temperature |
| dhw_temp | Hot Water Temperature |
| buffer_top_temp | Buffer Top Temperature |
| buffer_bottom_temp | Buffer Bottom Temperature |

### Binary Sensor

**Discovery Topic**: `homeassistant/binary_sensor/buderus_wps/<entity_id>/config`

**Payload Schema**:
```json
{
  "unique_id": "buderus_wps_<entity_id>",
  "name": "<display_name>",
  "device_class": "running",
  "state_topic": "buderus_wps/binary_sensor/<entity_id>/state",
  "payload_on": "ON",
  "payload_off": "OFF",
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": { ... }
}
```

**State Topic**: `buderus_wps/binary_sensor/<entity_id>/state`
**State Payload**: "ON" or "OFF"

**Entities**:
| entity_id | name |
|-----------|------|
| compressor | Compressor |

### Select Entity

**Discovery Topic**: `homeassistant/select/buderus_wps/<entity_id>/config`

**Payload Schema**:
```json
{
  "unique_id": "buderus_wps_<entity_id>",
  "name": "<display_name>",
  "state_topic": "buderus_wps/select/<entity_id>/state",
  "command_topic": "buderus_wps/select/<entity_id>/set",
  "options": ["Option1", "Option2", "Option3"],
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": { ... }
}
```

**State Topic**: `buderus_wps/select/<entity_id>/state`
**State Payload**: One of the options (e.g., "Automatic")

**Command Topic**: `buderus_wps/select/<entity_id>/set`
**Command Payload**: One of the options (e.g., "Summer")

**Entities**:
| entity_id | name | options |
|-----------|------|---------|
| heating_season_mode | Heating Season Mode | Winter, Automatic, Summer |
| dhw_program_mode | DHW Program Mode | Automatic, Always On, Always Off |

### Switch Entity

**Discovery Topic**: `homeassistant/switch/buderus_wps/<entity_id>/config`

**Payload Schema**:
```json
{
  "unique_id": "buderus_wps_<entity_id>",
  "name": "<display_name>",
  "state_topic": "buderus_wps/switch/<entity_id>/state",
  "command_topic": "buderus_wps/switch/<entity_id>/set",
  "payload_on": "ON",
  "payload_off": "OFF",
  "state_on": "ON",
  "state_off": "OFF",
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": { ... }
}
```

**State Topic**: `buderus_wps/switch/<entity_id>/state`
**State Payload**: "ON" or "OFF"

**Command Topic**: `buderus_wps/switch/<entity_id>/set`
**Command Payload**: "ON" or "OFF"

**Entities**:
| entity_id | name |
|-----------|------|
| holiday_mode | Holiday Mode |

### Number Entity

**Discovery Topic**: `homeassistant/number/buderus_wps/<entity_id>/config`

**Payload Schema**:
```json
{
  "unique_id": "buderus_wps_<entity_id>",
  "name": "<display_name>",
  "device_class": "<device_class_or_null>",
  "unit_of_measurement": "<unit>",
  "state_topic": "buderus_wps/number/<entity_id>/state",
  "command_topic": "buderus_wps/number/<entity_id>/set",
  "min": <min_value>,
  "max": <max_value>,
  "step": <step>,
  "mode": "slider",
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": { ... }
}
```

**State Topic**: `buderus_wps/number/<entity_id>/state`
**State Payload**: Numeric value as string (e.g., "12" or "55.5")

**Command Topic**: `buderus_wps/number/<entity_id>/set`
**Command Payload**: Numeric value as string

**Entities**:
| entity_id | name | unit | min | max | step |
|-----------|------|------|-----|-----|------|
| extra_dhw_duration | Extra Hot Water Duration | h | 0 | 48 | 1 |
| extra_dhw_target | Extra Hot Water Target | °C | 50.0 | 65.0 | 0.5 |

## Message Retention

| Message Type | Retained |
|--------------|----------|
| Discovery config | Yes |
| State updates | No |
| Commands | No |
| Availability | Yes |

## QoS Levels

| Message Type | QoS |
|--------------|-----|
| Discovery config | 1 (at least once) |
| State updates | 0 (at most once) |
| Commands | 1 (at least once) |
| Availability | 1 (at least once) |

## Birth/Last Will

**Birth Message**:
- Topic: `buderus_wps/status`
- Payload: `online`
- Retained: Yes
- Published: On successful connection

**Last Will**:
- Topic: `buderus_wps/status`
- Payload: `offline`
- Retained: Yes
- QoS: 1
- Set: On MQTT connect

## Validation Rules

1. **unique_id**: Must be globally unique, format `buderus_wps_<entity_id>`
2. **options**: Must match exactly (case-sensitive) for select entities
3. **state values**: Must be valid for entity type (float for sensors, options for select)
4. **commands**: Must be validated before sending to heat pump
5. **availability**: Must reflect actual connection state to heat pump
