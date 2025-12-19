# Home Assistant Service Contracts

**Feature**: 011-ha-integration
**Date**: 2025-12-13

## Overview

This document defines the Home Assistant services and entity interfaces for the Buderus WPS integration. These are the "contracts" that HA automations and the UI rely on.

## Entity Interfaces

### Sensor Entity Contract

```yaml
# Temperature Sensor Interface
entity_id: sensor.heat_pump_{type}_temperature
domain: sensor
device_class: temperature
state_class: measurement
unit_of_measurement: "°C"

states:
  - numeric: float  # Temperature value
  - unavailable     # Connection lost
  - unknown         # Read error

attributes:
  device_class: "temperature"
  state_class: "measurement"
  unit_of_measurement: "°C"
  friendly_name: "Heat Pump {Type} Temperature"
```

### Binary Sensor Contract

```yaml
# Compressor Status Interface
entity_id: binary_sensor.heat_pump_compressor
domain: binary_sensor
device_class: running

states:
  - "on"          # Compressor running
  - "off"         # Compressor stopped
  - unavailable   # Connection lost

attributes:
  device_class: "running"
  friendly_name: "Heat Pump Compressor"
```

### Switch Entity Contract

```yaml
# Energy Block Switch Interface
entity_id: switch.heat_pump_energy_block
domain: switch

states:
  - "on"          # Energy blocking enabled
  - "off"         # Normal operation
  - unavailable   # Connection lost

services:
  switch.turn_on:
    description: "Enable energy blocking (stops compressor and aux heater)"
    fields: {}

  switch.turn_off:
    description: "Disable energy blocking (resume normal operation)"
    fields: {}

attributes:
  icon: "mdi:power-plug-off"
  friendly_name: "Heat Pump Energy Block"
```

### Number Entity Contract

```yaml
# DHW Extra Duration Interface
entity_id: number.heat_pump_dhw_extra_duration
domain: number

states:
  - numeric: int (0-24)  # Hours remaining
  - unavailable          # Connection lost

services:
  number.set_value:
    description: "Set DHW extra production duration"
    fields:
      value:
        description: "Duration in hours (0 to stop, 1-24 to start)"
        example: 2
        required: true
        selector:
          number:
            min: 0
            max: 24
            step: 1
            unit_of_measurement: "h"

attributes:
  min: 0
  max: 24
  step: 1
  mode: "slider"
  unit_of_measurement: "h"
  icon: "mdi:water-boiler"
  friendly_name: "Heat Pump DHW Extra Duration"
```

### Select Entity Contract

```yaml
# Heating Season Mode Interface
entity_id: select.heat_pump_heating_season_mode
domain: select

states:
  - "Winter (Forced)"   # Force heating
  - "Automatic"         # Normal operation
  - "Off (Summer)"      # Disable heating
  - unavailable         # Connection lost

services:
  select.select_option:
    description: "Set heating season mode"
    fields:
      option:
        description: "The mode to select"
        required: true
        selector:
          select:
            options:
              - "Winter (Forced)"
              - "Automatic"
              - "Off (Summer)"

attributes:
  options: ["Winter (Forced)", "Automatic", "Off (Summer)"]
  icon: "mdi:home-thermometer"
  friendly_name: "Heat Pump Heating Season Mode"
```

```yaml
# DHW Program Mode Interface
entity_id: select.heat_pump_dhw_program_mode
domain: select

states:
  - "Automatic"      # Follow time program
  - "Always On"      # Force DHW heating
  - "Always Off"     # Disable DHW heating
  - unavailable      # Connection lost

services:
  select.select_option:
    description: "Set DHW program mode"
    fields:
      option:
        description: "The mode to select"
        required: true
        selector:
          select:
            options:
              - "Automatic"
              - "Always On"
              - "Always Off"

attributes:
  options: ["Automatic", "Always On", "Always Off"]
  icon: "mdi:water-boiler"
  friendly_name: "Heat Pump DHW Program Mode"
```

## Configuration Contract

```yaml
# YAML Configuration Schema
buderus_wps:
  # Serial port for USBtin adapter
  port:
    type: string
    required: false
    default: "/dev/ttyACM0"
    description: "USB serial port path"

  # Polling interval
  scan_interval:
    type: integer
    required: false
    default: 60
    minimum: 10
    maximum: 300
    description: "Sensor update interval in seconds"
```

## Event Contracts

### State Change Events

When entities change state, Home Assistant fires state_changed events:

```yaml
event_type: state_changed
data:
  entity_id: sensor.heat_pump_outdoor_temperature
  old_state:
    state: "18.5"
    attributes: {...}
  new_state:
    state: "19.0"
    attributes: {...}
```

### Unavailable State Event

When connection is lost:

```yaml
event_type: state_changed
data:
  entity_id: sensor.heat_pump_outdoor_temperature
  old_state:
    state: "18.5"
  new_state:
    state: "unavailable"
    attributes:
      device_class: "temperature"
      # Other attributes preserved
```

## Automation Examples

### Energy Blocking During Peak Hours

```yaml
automation:
  - alias: "Block Energy During Peak"
    trigger:
      - platform: time
        at: "17:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.heat_pump_energy_block

  - alias: "Resume Energy After Peak"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.heat_pump_energy_block
```

### Morning DHW Boost

```yaml
automation:
  - alias: "Morning Hot Water Boost"
    trigger:
      - platform: time
        at: "05:30:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.heat_pump_dhw_extra_duration
        data:
          value: 1  # 1 hour of extra heating
```

### Compressor Running Notification

```yaml
automation:
  - alias: "Notify When Compressor Starts"
    trigger:
      - platform: state
        entity_id: binary_sensor.heat_pump_compressor
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Heat pump compressor started"
```

## Error States

| Scenario | Entity State | Coordinator State |
|----------|--------------|-------------------|
| Normal operation | Valid values | `connected=True` |
| USB disconnected | `unavailable` | `connected=False`, backoff active |
| Read timeout | `unknown` or last value | `connected=True` |
| Write failure | No change | `connected=True`, error logged |
| Reconnected | Valid values | `connected=True`, backoff reset |
