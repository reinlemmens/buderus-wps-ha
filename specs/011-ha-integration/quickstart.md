# Quickstart: Home Assistant Integration

**Feature**: 011-ha-integration
**Date**: 2025-12-13

## Prerequisites

1. **Hardware**
   - Buderus WPS heat pump with CAN bus interface
   - USBtin CAN-to-USB adapter connected to Raspberry Pi
   - USB cable connecting adapter to HA host

2. **Software**
   - Home Assistant Core 2023.x or later
   - Python 3.9+ on HA host
   - User in `dialout` group for serial port access

3. **Serial Port Access**
   ```bash
   # Add HA user to dialout group
   sudo usermod -a -G dialout homeassistant

   # Verify USB device is detected
   ls -la /dev/ttyACM*
   # Should show: /dev/ttyACM0
   ```

## Installation

### Step 1: Copy Integration Files

Copy the `custom_components/buderus_wps` directory to your Home Assistant config:

```bash
# From repository root
cp -r custom_components/buderus_wps /path/to/homeassistant/config/custom_components/
```

Directory structure after install:
```
config/
├── configuration.yaml
├── custom_components/
│   └── buderus_wps/
│       ├── __init__.py
│       ├── const.py
│       ├── coordinator.py
│       ├── entity.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── switch.py
│       ├── number.py
│       ├── select.py
│       └── manifest.json
```

### Step 2: Configure YAML

Add to `configuration.yaml`:

```yaml
# Minimal configuration (uses defaults)
buderus_wps:

# Or with custom settings
buderus_wps:
  port: "/dev/ttyACM0"     # USB serial port (default)
  scan_interval: 60        # Poll interval in seconds (10-300, default: 60)
```

### Step 3: Restart Home Assistant

```bash
# Restart HA to load the integration
ha core restart
```

### Step 4: Verify Installation

After restart, check for new entities in the HA UI:

1. Go to **Settings → Devices & Services → Entities**
2. Filter by "Heat Pump"
3. You should see:
   - 5 temperature sensors
   - 1 compressor binary sensor
   - 1 energy block switch
   - 1 DHW extra duration number
   - 2 mode selects (bonus)

## Entity Overview

| Entity | Type | Description |
|--------|------|-------------|
| Heat Pump Outdoor Temperature | sensor | Outdoor air temperature |
| Heat Pump Supply Temperature | sensor | Water supply temperature |
| Heat Pump Return Temperature | sensor | Water return temperature |
| Heat Pump Hot Water Temperature | sensor | DHW tank temperature |
| Heat Pump Brine Inlet Temperature | sensor | Geothermal brine input |
| Heat Pump Compressor | binary_sensor | Running/stopped status |
| Heat Pump Energy Block | switch | Block all heating operations |
| Heat Pump DHW Extra Duration | number | Set extra DHW heating (0-24h) |
| Heat Pump Heating Season Mode | select | Winter/Auto/Off modes |
| Heat Pump DHW Program Mode | select | Auto/Always On/Always Off |

## Basic Usage

### View Temperatures

Add sensors to a dashboard card:

```yaml
type: entities
title: Heat Pump Temperatures
entities:
  - sensor.heat_pump_outdoor_temperature
  - sensor.heat_pump_supply_temperature
  - sensor.heat_pump_return_temperature
  - sensor.heat_pump_hot_water_temperature
  - sensor.heat_pump_brine_inlet_temperature
```

### Monitor Compressor

```yaml
type: entity
entity: binary_sensor.heat_pump_compressor
name: Compressor Status
```

### Control Energy Blocking

Toggle from dashboard or use in automations:

```yaml
type: entity
entity: switch.heat_pump_energy_block
```

### Request Hot Water

Use the number slider to request extra DHW production:

```yaml
type: entity
entity: number.heat_pump_dhw_extra_duration
name: DHW Boost
```

Set to 1-24 hours to start extra heating, 0 to stop.

## Automation Examples

### Peak Hour Energy Blocking

Block heating during expensive electricity hours:

```yaml
automation:
  - alias: "Peak Hours Start - Block Heat Pump"
    trigger:
      - platform: time
        at: "17:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.heat_pump_energy_block

  - alias: "Peak Hours End - Unblock Heat Pump"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.heat_pump_energy_block
```

### Morning Hot Water Boost

Ensure hot water is ready in the morning:

```yaml
automation:
  - alias: "Morning DHW Boost"
    trigger:
      - platform: time
        at: "05:30:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.heat_pump_hot_water_temperature
        below: 45
    action:
      - service: number.set_value
        target:
          entity_id: number.heat_pump_dhw_extra_duration
        data:
          value: 1
```

### Guest Arrival Hot Water

Boost hot water when guests arrive:

```yaml
automation:
  - alias: "Guest Arrival - DHW Boost"
    trigger:
      - platform: state
        entity_id: input_boolean.guests_arriving
        to: "on"
    action:
      - service: number.set_value
        target:
          entity_id: number.heat_pump_dhw_extra_duration
        data:
          value: 2
```

### Low Temperature Alert

Get notified if outdoor temperature drops significantly:

```yaml
automation:
  - alias: "Cold Weather Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.heat_pump_outdoor_temperature
        below: -10
    action:
      - service: notify.mobile_app
        data:
          title: "Heat Pump Alert"
          message: "Outdoor temperature is {{ states('sensor.heat_pump_outdoor_temperature') }}°C"
```

## Troubleshooting

### Entities Show "Unavailable"

1. **Check USB connection**:
   ```bash
   ls -la /dev/ttyACM*
   ```
   If no device, check USB cable and adapter.

2. **Check serial port permissions**:
   ```bash
   groups homeassistant
   ```
   Should include `dialout`.

3. **Check logs**:
   ```bash
   grep buderus_wps /path/to/home-assistant.log
   ```

### Values Not Updating

1. Check `scan_interval` setting (default 60 seconds)
2. Verify heat pump is communicating (check CAN activity LEDs)
3. Look for timeout errors in logs

### Connection Drops

The integration implements automatic reconnection with exponential backoff:
- Initial retry: 5 seconds
- Doubles each failure: 5s → 10s → 20s → 40s → 80s → 120s
- Maximum wait: 120 seconds (2 minutes)

Check logs for reconnection attempts:
```
INFO Attempting reconnection in X seconds
WARNING Reconnection failed: <error>
INFO Successfully reconnected to heat pump
```

### Energy Block Not Working

The `ADDITIONAL_BLOCKED` parameter may not stop the compressor immediately:
- Wait up to 30 seconds for the command to take effect
- The heat pump may complete its current cycle first
- Check compressor status to verify blocking is active

## Configuration Reference

| Option | Type | Default | Range | Description |
|--------|------|---------|-------|-------------|
| `port` | string | "/dev/ttyACM0" | - | USB serial port path |
| `scan_interval` | integer | 60 | 10-300 | Poll interval in seconds |

## Logs

Enable debug logging for troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.buderus_wps: debug
```

## Next Steps

- Set up [energy management automations](https://www.home-assistant.io/docs/automation/)
- Create a [dashboard](https://www.home-assistant.io/dashboards/) for heat pump monitoring
- Integrate with [energy dashboard](https://www.home-assistant.io/docs/energy/) for usage tracking
