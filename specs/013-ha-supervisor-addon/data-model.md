# Data Model: Home Assistant Supervisor Add-on

**Feature**: 013-ha-supervisor-addon
**Date**: 2025-12-13

## Core Data Structures

### EntityConfig

Represents an entity to be published via MQTT Discovery.

```python
@dataclass
class EntityConfig:
    """Configuration for an MQTT Discovery entity."""

    entity_id: str          # Unique identifier (e.g., "outdoor_temp")
    entity_type: str        # HA platform: sensor, binary_sensor, switch, select, number
    name: str               # Human-readable name
    device_class: str | None  # HA device class (temperature, running, etc.)
    unit: str | None        # Unit of measurement
    state_class: str | None # measurement, total, total_increasing

    # Topic configuration
    state_topic: str        # Topic for state updates
    command_topic: str | None  # Topic for commands (controllable entities)

    # Value handling
    value_template: str | None  # Jinja2 template for state extraction
    options: list[str] | None   # For select entities
    min_value: float | None     # For number entities
    max_value: float | None     # For number entities
    step: float | None          # For number entities

    # Source configuration
    parameter_name: str | None  # buderus_wps parameter name
    broadcast_idx: int | None   # Broadcast index for passive reads
    use_menu_api: bool = False  # Use MenuAPI instead of direct read
```

### SensorReading

Container for sensor data.

```python
@dataclass
class SensorReading:
    """A sensor reading with metadata."""

    entity_id: str
    value: float | int | bool | str | None
    timestamp: float
    source: str  # "broadcast", "parameter", "menu_api"
    raw_value: bytes | None = None
```

### AddonConfig

Runtime configuration loaded from Supervisor.

```python
@dataclass
class AddonConfig:
    """Add-on configuration from Supervisor."""

    serial_device: str      # USB serial device path
    mqtt_host: str          # MQTT broker host
    mqtt_port: int          # MQTT broker port (default: 1883)
    mqtt_username: str | None
    mqtt_password: str | None
    scan_interval: int      # Polling interval in seconds (default: 60)
    log_level: str          # debug, info, warning, error
```

### CommandMessage

Incoming command from MQTT.

```python
@dataclass
class CommandMessage:
    """A command received via MQTT."""

    entity_id: str
    value: str  # Raw string value from MQTT
    timestamp: float
    topic: str
```

### QueuedCommand

Command waiting in the rate-limited queue.

```python
@dataclass
class QueuedCommand:
    """A command in the execution queue."""

    entity_id: str
    parameter_name: str
    value: int | float | bool | str
    queued_at: float
    callback: Callable[[bool, str | None], None] | None = None
```

## Entity Definitions

### Temperature Sensors

```python
TEMPERATURE_SENSORS = [
    EntityConfig(
        entity_id="outdoor_temp",
        entity_type="sensor",
        name="Outdoor Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        state_topic="buderus_wps/sensor/outdoor_temp/state",
        command_topic=None,
        value_template=None,
        broadcast_idx=12,
    ),
    EntityConfig(
        entity_id="supply_temp",
        entity_type="sensor",
        name="Supply Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        state_topic="buderus_wps/sensor/supply_temp/state",
        command_topic=None,
        value_template=None,
        broadcast_idx=13,
    ),
    EntityConfig(
        entity_id="return_temp",
        entity_type="sensor",
        name="Return Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        state_topic="buderus_wps/sensor/return_temp/state",
        command_topic=None,
        value_template=None,
        broadcast_idx=14,
    ),
    EntityConfig(
        entity_id="dhw_temp",
        entity_type="sensor",
        name="Hot Water Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        state_topic="buderus_wps/sensor/dhw_temp/state",
        command_topic=None,
        value_template=None,
        broadcast_idx=15,
    ),
    EntityConfig(
        entity_id="buffer_top_temp",
        entity_type="sensor",
        name="Buffer Top Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        state_topic="buderus_wps/sensor/buffer_top_temp/state",
        command_topic=None,
        value_template=None,
        broadcast_idx=16,
    ),
    EntityConfig(
        entity_id="buffer_bottom_temp",
        entity_type="sensor",
        name="Buffer Bottom Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        state_topic="buderus_wps/sensor/buffer_bottom_temp/state",
        command_topic=None,
        value_template=None,
        broadcast_idx=17,
    ),
]
```

### Binary Sensors

```python
BINARY_SENSORS = [
    EntityConfig(
        entity_id="compressor",
        entity_type="binary_sensor",
        name="Compressor",
        device_class="running",
        unit=None,
        state_class=None,
        state_topic="buderus_wps/binary_sensor/compressor/state",
        command_topic=None,
        value_template=None,
        use_menu_api=True,
    ),
]
```

### Select Entities

```python
SELECT_ENTITIES = [
    EntityConfig(
        entity_id="heating_season_mode",
        entity_type="select",
        name="Heating Season Mode",
        device_class=None,
        unit=None,
        state_class=None,
        state_topic="buderus_wps/select/heating_season_mode/state",
        command_topic="buderus_wps/select/heating_season_mode/set",
        options=["Winter", "Automatic", "Summer"],
        parameter_name="HEATING_SEASON_MODE",
    ),
    EntityConfig(
        entity_id="dhw_program_mode",
        entity_type="select",
        name="DHW Program Mode",
        device_class=None,
        unit=None,
        state_class=None,
        state_topic="buderus_wps/select/dhw_program_mode/state",
        command_topic="buderus_wps/select/dhw_program_mode/set",
        options=["Automatic", "Always On", "Always Off"],
        parameter_name="DHW_PROGRAM_MODE",
    ),
]
```

### Switch Entities

```python
SWITCH_ENTITIES = [
    EntityConfig(
        entity_id="holiday_mode",
        entity_type="switch",
        name="Holiday Mode",
        device_class=None,
        unit=None,
        state_class=None,
        state_topic="buderus_wps/switch/holiday_mode/state",
        command_topic="buderus_wps/switch/holiday_mode/set",
        parameter_name="HOLIDAY_ACTIVE_GLOBAL",
    ),
]
```

### Number Entities

```python
NUMBER_ENTITIES = [
    EntityConfig(
        entity_id="extra_dhw_duration",
        entity_type="number",
        name="Extra Hot Water Duration",
        device_class=None,
        unit="h",
        state_class=None,
        state_topic="buderus_wps/number/extra_dhw_duration/state",
        command_topic="buderus_wps/number/extra_dhw_duration/set",
        min_value=0,
        max_value=48,
        step=1,
        use_menu_api=True,
    ),
    EntityConfig(
        entity_id="extra_dhw_target",
        entity_type="number",
        name="Extra Hot Water Target",
        device_class="temperature",
        unit="°C",
        state_class=None,
        state_topic="buderus_wps/number/extra_dhw_target/state",
        command_topic="buderus_wps/number/extra_dhw_target/set",
        min_value=50.0,
        max_value=65.0,
        step=0.5,
        use_menu_api=True,
    ),
]
```

## Value Mappings

### Heating Season Mode

| HA Option | Parameter Value | Description |
|-----------|-----------------|-------------|
| Winter | 0 | Forced heating - heating always enabled |
| Automatic | 1 | Normal operation - based on outdoor temp |
| Summer | 2 | No heating - hot water only |

### DHW Program Mode

| HA Option | Parameter Value | Description |
|-----------|-----------------|-------------|
| Automatic | 0 | Normal - follows time program |
| Always On | 1 | DHW always active |
| Always Off | 2 | No DHW heating |

### Holiday Mode

| HA State | Parameter Value |
|----------|-----------------|
| OFF | 0 |
| ON | 1 |

## MQTT Discovery Payloads

### Example: Temperature Sensor

```json
{
  "unique_id": "buderus_wps_outdoor_temp",
  "name": "Outdoor Temperature",
  "device_class": "temperature",
  "unit_of_measurement": "°C",
  "state_class": "measurement",
  "state_topic": "buderus_wps/sensor/outdoor_temp/state",
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": {
    "identifiers": ["buderus_wps"],
    "name": "Buderus WPS Heat Pump",
    "manufacturer": "Buderus",
    "model": "WPS"
  }
}
```

### Example: Select Entity

```json
{
  "unique_id": "buderus_wps_heating_season_mode",
  "name": "Heating Season Mode",
  "state_topic": "buderus_wps/select/heating_season_mode/state",
  "command_topic": "buderus_wps/select/heating_season_mode/set",
  "options": ["Winter", "Automatic", "Summer"],
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": {
    "identifiers": ["buderus_wps"],
    "name": "Buderus WPS Heat Pump",
    "manufacturer": "Buderus",
    "model": "WPS"
  }
}
```

### Example: Number Entity

```json
{
  "unique_id": "buderus_wps_extra_dhw_duration",
  "name": "Extra Hot Water Duration",
  "unit_of_measurement": "h",
  "state_topic": "buderus_wps/number/extra_dhw_duration/state",
  "command_topic": "buderus_wps/number/extra_dhw_duration/set",
  "min": 0,
  "max": 48,
  "step": 1,
  "mode": "slider",
  "availability_topic": "buderus_wps/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": {
    "identifiers": ["buderus_wps"],
    "name": "Buderus WPS Heat Pump",
    "manufacturer": "Buderus",
    "model": "WPS"
  }
}
```

## State Transitions

### Service Lifecycle

```
[STARTING] → [CONNECTING] → [RUNNING] → [DISCONNECTED] → [RECONNECTING]
                                ↑                              ↓
                                └──────────────────────────────┘
```

### Availability States

| State | MQTT Payload | Condition |
|-------|--------------|-----------|
| online | "online" | Connected to heat pump AND MQTT broker |
| offline | "offline" | Either disconnected or service stopped |

## Error States

### SensorError

```python
@dataclass
class SensorError:
    """Error reading a sensor."""

    entity_id: str
    error_type: str  # "timeout", "invalid_response", "disconnected"
    message: str
    timestamp: float
    recoverable: bool
```

### CommandError

```python
@dataclass
class CommandError:
    """Error executing a command."""

    entity_id: str
    error_type: str  # "validation", "timeout", "rejected", "disconnected"
    message: str
    timestamp: float
    original_value: str
```
