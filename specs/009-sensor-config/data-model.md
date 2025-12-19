# Data Model: Sensor Configuration

**Feature**: 009-sensor-config
**Date**: 2024-12-02

## Entities

### SensorMapping

Represents a CAN broadcast address mapped to a human-readable sensor name.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| base | int | Yes | CAN message base address (0x0000-0xFFFF) |
| idx | int | Yes | Parameter index within message (0-2047) |
| sensor | str | Yes | Sensor name: outdoor, supply, return_temp, dhw, brine_in |

**Validation**:
- `base` must be 0-65535 (0xFFFF)
- `idx` must be 0-2047
- `sensor` must be one of the known sensor types

### CircuitConfig

Represents a heating circuit configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| number | int | Yes | Circuit number (1-4) |
| type | str | Yes | Circuit type: ventilo, floor_heating, unknown |
| apartment | str | No | Apartment identifier (user-defined string) |
| label | str | No | Custom display label |

**Validation**:
- `number` must be 1-4
- `type` must be one of: ventilo, floor_heating, unknown

### DHWConfig

Represents domestic hot water distribution configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| apartments | list[str] | No | List of apartments with DHW access |

**Default**: If not specified, all apartments have DHW access.

### SensorLabels

Optional custom labels for sensor display.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sensor_name | str | Key | Standard sensor name |
| label | str | Value | Custom display label |

### InstallationConfig

Root configuration object containing all settings.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | str | No | Config file version (for future compatibility) |
| sensor_mappings | list[SensorMapping] | No | CAN address to sensor mappings |
| circuits | list[CircuitConfig] | No | Heating circuit definitions |
| dhw | DHWConfig | No | DHW distribution settings |
| labels | SensorLabels | No | Custom sensor labels |

## Relationships

```
InstallationConfig
├── sensor_mappings: List[SensorMapping]
├── circuits: List[CircuitConfig]
│   └── apartment: references Apartment (string)
├── dhw: DHWConfig
│   └── apartments: List[Apartment] (strings)
└── labels: Dict[sensor_name, label]
```

## State Transitions

Configuration is stateless - loaded once at application startup. No state transitions.

## Example YAML Structure

```yaml
# Buderus WPS Configuration
version: "1.0"

# CAN broadcast to sensor mappings
sensor_mappings:
  - base: 0x0402
    idx: 38
    sensor: outdoor
  - base: 0x0060
    idx: 58
    sensor: dhw
  - base: 0x0270
    idx: 1
    sensor: supply
  - base: 0x0270
    idx: 0
    sensor: return_temp

# Heating circuits
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

# DHW distribution
dhw:
  apartments:
    - "Apartment 0"

# Custom sensor labels
labels:
  outdoor: "Outside Air"
  dhw: "Hot Water Tank"
```
