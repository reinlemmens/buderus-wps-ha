# Buderus WPS Heat Pump Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Monitor and control your Buderus WPS heat pump directly from Home Assistant via CAN bus.

## Features

- **13 temperature sensors**:
  - 5 core sensors (Outdoor, Supply, Return, DHW, Brine Inlet)
  - 4 room temperature sensors (C1-C4, from RC10 thermostats)
  - 4 room setpoint sensors (C1-C4, target temperatures)
- Compressor status monitoring
- Energy blocking switch (disable heating during peak electricity rates)
- DHW extra production control (boost hot water on demand)
- Advanced parameter access (allowlist sensors + read/list services)
- Automatic reconnection with exponential backoff

## Requirements

- Home Assistant with [HACS](https://hacs.xyz/) installed
- USBtin CAN adapter (or compatible SLCAN adapter)
- Buderus WPS heat pump with CAN bus connection

## Installation via HACS

1. Open HACS in your Home Assistant instance
2. Click the three dots menu in the top right corner
3. Select "Custom repositories"
4. Add repository URL: `https://github.com/reinlemmens/buderus-wps-ha`
5. Select category: "Integration"
6. Click "Add"
7. Search for "Buderus WPS" and click "Download"
8. Restart Home Assistant
9. Go to Settings → Devices & Services → Add Integration → Buderus WPS

## Configuration

After installation, the integration creates the following entities:

### Temperature Sensors

| Entity | Description |
|--------|-------------|
| `sensor.heat_pump_outdoor_temperature` | Outside air temperature |
| `sensor.heat_pump_supply_temperature` | Heating supply water temperature |
| `sensor.heat_pump_return_temperature` | Heating return water temperature |
| `sensor.heat_pump_hot_water_temperature` | Domestic hot water temperature |
| `sensor.heat_pump_brine_inlet_temperature` | Ground source brine inlet temperature |
| `sensor.heat_pump_room_temperature_c1` | Room temperature from RC10 thermostat (Circuit 1) |
| `sensor.heat_pump_room_temperature_c2` | Room temperature from RC10 thermostat (Circuit 2) |
| `sensor.heat_pump_room_temperature_c3` | Room temperature from RC10 thermostat (Circuit 3) |
| `sensor.heat_pump_room_temperature_c4` | Room temperature from RC10 thermostat (Circuit 4) |
| `sensor.heat_pump_room_setpoint_c1` | Target temperature for Circuit 1 |
| `sensor.heat_pump_room_setpoint_c2` | Target temperature for Circuit 2 |
| `sensor.heat_pump_room_setpoint_c3` | Target temperature for Circuit 3 |
| `sensor.heat_pump_room_setpoint_c4` | Target temperature for Circuit 4 |

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.heat_pump_compressor` | Binary Sensor | Compressor running state |
| `switch.heat_pump_energy_block` | Switch | Block heating operation |
| `number.heat_pump_dhw_extra_duration` | Number | DHW boost duration (hours) |

### Advanced parameter access

Use this when you want to expose parameters that are readable in FHEM but not part of the default entity set.

1) Discover available parameters with the `buderus_wps.list_parameters` service:

```yaml
service: buderus_wps.list_parameters
data:
  name_contains: COMPRESSOR
  limit: 10
```

2) Add the keys you want to the Options flow (Settings -> Devices & Services -> Buderus WPS -> Options) in the "Parameter allowlist" field (comma-separated):

```
GT10_TEMP, GT11_TEMP, COMPRESSOR_STATE
```

Allowed parameters become sensors named `Parameter <KEY>` and update on the normal refresh interval.

You can also read a single parameter on demand:

```yaml
service: buderus_wps.read_parameter
data:
  name: GT10_TEMP
```

If you call the service via the REST API, add `?return_response` to receive the response payload.

## Example Automations

### Block heating during peak electricity rates

```yaml
automation:
  - alias: "Block heat pump during peak rates"
    trigger:
      - platform: time
        at: "17:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.heat_pump_energy_block

  - alias: "Resume heating after peak rates"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.heat_pump_energy_block
```

### Boost hot water before morning shower

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

## Troubleshooting

### Serial Port Access Denied

Add the Home Assistant user to the dialout group:

```bash
sudo usermod -a -G dialout homeassistant
```

### Port Not Found

- Verify USB adapter is connected: `ls /dev/tty*`
- Look for `/dev/ttyACM0` or similar
- Try a different USB port

### No Response / Timeout

- Check CAN bus wiring to heat pump
- Verify heat pump is powered on
- Check CAN bus termination (120Ω resistors at each end)

## Support

- [GitHub Issues](https://github.com/reinlemmens/buderus-wps-ha/issues)
- [GitHub Discussions](https://github.com/reinlemmens/buderus-wps-ha/discussions)

## License

MIT License - see [LICENSE](LICENSE) file for details.
