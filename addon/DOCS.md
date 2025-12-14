# Buderus WPS Heat Pump Add-on

Control your Buderus WPS heat pump from Home Assistant via CAN bus over USB serial.

## Overview

This add-on connects to your Buderus WPS heat pump through a USBtin CAN adapter and exposes temperature sensors and control entities to Home Assistant via MQTT Discovery.

## Features

- **Temperature Monitoring**: Outdoor, supply, return, hot water, and buffer temperatures
- **Compressor Status**: Binary sensor showing running/stopped state
- **Heating Control**: Set heating season mode (Winter, Automatic, Summer)
- **Hot Water Control**: Set DHW program mode (Automatic, Always On, Always Off)
- **Holiday Mode**: Enable/disable holiday mode
- **Extra Hot Water**: Set duration and target temperature for extra hot water boost

## Prerequisites

1. **Home Assistant OS or Supervised** - Add-ons require the Supervisor
2. **USBtin CAN Adapter** - Connected via USB to the same machine running Home Assistant
3. **MQTT Integration** - Configured in Home Assistant (Mosquitto add-on recommended)

## Installation

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three-dot menu (⋮) → **Repositories**
3. Add the repository URL: `https://github.com/your-username/buderus-wps-ha`
4. Find "Buderus WPS Heat Pump" in the store and click **Install**

## Configuration

### Serial Device

Specify the USB serial device path where your USBtin adapter is connected.

**Common paths:**
- `/dev/ttyACM0` - Most USBtin adapters
- `/dev/ttyUSB0` - Some USB-serial converters
- `/dev/serial/by-id/usb-MCS_USBtin-if00` - Stable path (recommended)

**Tip:** Use the `/dev/serial/by-id/` path for stability. Device numbers like `/dev/ttyACM0` can change after reboot.

### MQTT Configuration

The add-on auto-detects the MQTT broker when using the Mosquitto add-on. For external brokers or custom configuration:

| Option | Description | Default |
|--------|-------------|---------|
| `mqtt_host` | MQTT broker hostname | Auto-detected |
| `mqtt_port` | MQTT broker port | 1883 |
| `mqtt_username` | MQTT username (optional) | - |
| `mqtt_password` | MQTT password (optional) | - |

### Scan Interval

How often to poll sensor values (in seconds). Lower values increase CAN bus traffic.

| Setting | Recommended Use |
|---------|-----------------|
| 30-60 | Normal operation |
| 10-30 | Debugging |
| 120+ | Energy saving |

### Log Level

Controls logging verbosity:

| Level | Description |
|-------|-------------|
| `debug` | Detailed CAN bus messages |
| `info` | Connection events and polling cycles |
| `warning` | Recoverable errors |
| `error` | Critical failures only |

## Example Configuration

```yaml
serial_device: /dev/serial/by-id/usb-MCS_USBtin-if00
mqtt_host: core-mosquitto
mqtt_port: 1883
scan_interval: 60
log_level: info
```

## Entities

After starting the add-on, the following entities appear automatically in Home Assistant:

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.buderus_wps_outdoor_temperature` | Outside air temperature |
| `sensor.buderus_wps_supply_temperature` | Heat pump supply line |
| `sensor.buderus_wps_return_temperature` | Heat pump return line |
| `sensor.buderus_wps_hot_water_temperature` | DHW tank temperature |
| `sensor.buderus_wps_buffer_top_temperature` | Buffer tank top |
| `sensor.buderus_wps_buffer_bottom_temperature` | Buffer tank bottom |
| `binary_sensor.buderus_wps_compressor` | Compressor running state |

### Controls

| Entity | Description | Options |
|--------|-------------|---------|
| `select.buderus_wps_heating_season_mode` | Heating control | Winter, Automatic, Summer |
| `select.buderus_wps_dhw_program_mode` | Hot water control | Automatic, Always On, Always Off |
| `switch.buderus_wps_holiday_mode` | Holiday mode | On/Off |
| `number.buderus_wps_extra_hot_water_duration` | Extra DHW time | 0-48 hours |
| `number.buderus_wps_extra_hot_water_target` | Extra DHW temp | 50-65 °C |

## Peak Hour Energy Blocking

To block heating during expensive electricity periods:

```yaml
automation:
  - alias: "Block heating during peak hours"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.buderus_wps_heating_season_mode
        data:
          option: "Summer"
      - service: select.select_option
        target:
          entity_id: select.buderus_wps_dhw_program_mode
        data:
          option: "Always Off"

  - alias: "Resume heating after peak hours"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.buderus_wps_heating_season_mode
        data:
          option: "Automatic"
      - service: select.select_option
        target:
          entity_id: select.buderus_wps_dhw_program_mode
        data:
          option: "Automatic"
```

## Troubleshooting

### Device Not Found

**Symptom:** Log shows "Serial device not found: /dev/ttyACM0"

**Solutions:**
1. Check USB connection: The USBtin adapter must be plugged into the machine running Home Assistant
2. Verify device path: Run `ls /dev/tty*` in the Terminal add-on to see available devices
3. Use stable path: Try `/dev/serial/by-id/...` instead of `/dev/ttyACM0` - this path persists across reboots
4. Check device mapping: Ensure the USB device is mapped in the add-on configuration

### Permission Denied

**Symptom:** Log shows "Permission denied for serial device"

**Solutions:**
1. Verify the add-on has the correct device mapping configured
2. Check that no other process is using the serial port
3. Restart the add-on after plugging in the USB device

### MQTT Connection Failed

**Symptom:** Log shows "Unable to connect to MQTT broker" or "MQTT connection failed"

**Solutions:**
1. Verify Mosquitto add-on is installed and running
2. Check MQTT credentials in configuration match your broker
3. Ensure MQTT integration is configured in Home Assistant
4. If using an external broker, verify host and port settings

### No Sensor Updates

**Symptom:** Sensors show "unavailable" or values don't update

**Solutions:**
1. Check add-on logs (Log tab) for CAN bus errors
2. Verify heat pump is powered and CAN bus cable is connected
3. Check that the USBtin adapter LEDs indicate activity
4. Try restarting the add-on
5. Reduce scan_interval to 30 seconds for debugging

### Temperature Shows 0.1°C

**Symptom:** Temperature readings show 0.1°C

**Explanation:** This indicates incomplete data from the heat pump. The add-on uses broadcast monitoring which should resolve this automatically within one scan interval.

### Commands Not Working

**Symptom:** Changing select/switch entities doesn't affect the heat pump

**Solutions:**
1. Check add-on logs for command execution messages
2. Verify heat pump is in a state that allows the change (e.g., not in manual mode)
3. Commands are rate-limited to 500ms between each - wait a moment between changes
4. Some parameters require specific conditions to be writable

### Reconnection Issues

**Symptom:** Add-on frequently disconnects and reconnects

**Solutions:**
1. Check USB cable quality and connection
2. Verify CAN bus wiring to the heat pump
3. Check add-on logs for specific error messages
4. The add-on uses exponential backoff (5s to 5min) for reconnection attempts

### Reading Logs

To view detailed logs:
1. Go to **Settings** → **Add-ons** → **Buderus WPS Heat Pump**
2. Click the **Log** tab
3. Set `log_level: debug` for verbose output including CAN bus messages
4. Logs include timestamps for tracking timing issues

## Support

- **Issues:** [GitHub Issues](https://github.com/your-username/buderus-wps-ha/issues)
- **Documentation:** [Project README](https://github.com/your-username/buderus-wps-ha)

## License

MIT License - See LICENSE file for details.
