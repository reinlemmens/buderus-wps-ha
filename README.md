# Buderus WPS Heat Pump Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Monitor and control your Buderus WPS heat pump directly from Home Assistant via CAN bus.

## Features

- 5 temperature sensors (Outdoor, Supply, Return, DHW, Brine Inlet)
- Compressor status monitoring
- Energy blocking switch (disable heating during peak electricity rates)
- DHW extra production control (boost hot water on demand)
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

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.heat_pump_outdoor_temperature` | Sensor | Outside air temperature |
| `sensor.heat_pump_supply_temperature` | Sensor | Heating supply water temperature |
| `sensor.heat_pump_return_temperature` | Sensor | Heating return water temperature |
| `sensor.heat_pump_hot_water_temperature` | Sensor | Domestic hot water temperature |
| `sensor.heat_pump_brine_inlet_temperature` | Sensor | Ground source brine inlet temperature |
| `binary_sensor.heat_pump_compressor` | Binary Sensor | Compressor running state |
| `switch.heat_pump_energy_block` | Switch | Block heating operation |
| `number.heat_pump_dhw_extra_duration` | Number | DHW boost duration (hours) |

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
