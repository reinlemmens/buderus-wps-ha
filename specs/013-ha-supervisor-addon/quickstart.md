# Quickstart: Home Assistant Supervisor Add-on

**Feature**: 013-ha-supervisor-addon
**Date**: 2025-12-13

## Prerequisites

- Home Assistant OS or Home Assistant Supervised installation
- MQTT broker configured (Mosquitto add-on recommended)
- USBtin CAN adapter connected via USB

## Installation

### 1. Add Repository

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three-dot menu (⋮) → **Repositories**
3. Add repository URL: `https://github.com/your-username/buderus-wps-ha`
4. Click **Add**

### 2. Install Add-on

1. Find "Buderus WPS Heat Pump" in the Add-on Store
2. Click **Install**
3. Wait for installation to complete (typically under 5 minutes)

### 3. Configure Add-on

1. Go to the add-on's **Configuration** tab
2. Set the serial device path:
   ```yaml
   serial_device: /dev/ttyACM0
   ```
   Or use stable path:
   ```yaml
   serial_device: /dev/serial/by-id/usb-MCS_USBtin-if00
   ```
3. (Optional) Configure MQTT if not auto-detected:
   ```yaml
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   mqtt_username: mqtt_user
   mqtt_password: mqtt_pass
   ```
4. (Optional) Adjust scan interval:
   ```yaml
   scan_interval: 60
   ```

### 4. Start Add-on

1. Go to the **Info** tab
2. Click **Start**
3. Check the **Log** tab for connection status

## Verification

### Check MQTT Discovery

1. Navigate to **Settings** → **Devices & Services** → **MQTT**
2. Look for "Buderus WPS Heat Pump" device
3. Verify entities appear:
   - 6 temperature sensors
   - 1 compressor binary sensor
   - 2 select entities (heating mode, DHW mode)
   - 1 switch (holiday mode)
   - 2 number entities (extra DHW)

### Check Sensor Values

1. Navigate to **Developer Tools** → **States**
2. Filter by "buderus"
3. Verify sensors show numeric values (not "unavailable")

## Troubleshooting

### Device Not Found

**Symptom**: Log shows "Device not found" or "Permission denied"

**Solutions**:
1. Check USB connection: `ls /dev/tty*`
2. Use stable device path: `/dev/serial/by-id/...`
3. Verify device permissions in config.yaml

### MQTT Connection Failed

**Symptom**: Log shows "Unable to connect to MQTT broker"

**Solutions**:
1. Verify Mosquitto add-on is running
2. Check MQTT credentials in configuration
3. Ensure MQTT integration is configured in Home Assistant

### No Sensor Updates

**Symptom**: Sensors show "unavailable" or stale values

**Solutions**:
1. Check add-on logs for CAN bus errors
2. Verify heat pump is powered and responding
3. Try restarting the add-on

### Temperature Shows 0.1°C

**Symptom**: Temperature sensors show 0.1°C instead of real values

**Solution**: This indicates the heat pump returned incomplete data. The add-on uses broadcast monitoring which should resolve this automatically after a few seconds.

## Entity Reference

### Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.buderus_wps_outdoor_temperature` | Outside air temperature |
| `sensor.buderus_wps_supply_temperature` | Heat pump supply line |
| `sensor.buderus_wps_return_temperature` | Heat pump return line |
| `sensor.buderus_wps_hot_water_temperature` | DHW tank temperature |
| `sensor.buderus_wps_buffer_top_temperature` | Buffer tank top |
| `sensor.buderus_wps_buffer_bottom_temperature` | Buffer tank bottom |
| `binary_sensor.buderus_wps_compressor` | Compressor running state |

### Controls

| Entity ID | Description | Options/Range |
|-----------|-------------|---------------|
| `select.buderus_wps_heating_season_mode` | Space heating control | Winter, Automatic, Summer |
| `select.buderus_wps_dhw_program_mode` | Hot water control | Automatic, Always On, Always Off |
| `switch.buderus_wps_holiday_mode` | Holiday/absence mode | On/Off |
| `number.buderus_wps_extra_hot_water_duration` | Extra DHW boost time | 0-48 hours |
| `number.buderus_wps_extra_hot_water_target` | Extra DHW target temp | 50.0-65.0°C |

## Example Automations

### Peak Hour Blocking

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

### Temperature Alert

```yaml
automation:
  - alias: "Alert on low DHW temperature"
    trigger:
      - platform: numeric_state
        entity_id: sensor.buderus_wps_hot_water_temperature
        below: 45
    action:
      - service: notify.mobile_app
        data:
          message: "Hot water temperature is low: {{ states('sensor.buderus_wps_hot_water_temperature') }}°C"
```

## Logs

### Enable Debug Logging

In add-on configuration:
```yaml
log_level: debug
```

### View Logs

1. Go to add-on page
2. Click **Log** tab
3. Click **Refresh** to see latest entries

### Log Examples

**Successful startup**:
```
[INFO] Starting Buderus WPS add-on
[INFO] Connecting to serial device: /dev/ttyACM0
[INFO] Connected to USBtin CAN adapter
[INFO] Connecting to MQTT broker: core-mosquitto:1883
[INFO] MQTT connected, publishing discovery messages
[INFO] Published 12 entity configurations
[INFO] Add-on running, polling every 60 seconds
```

**Connection error**:
```
[ERROR] Failed to connect to serial device: /dev/ttyUSB0
[ERROR] Device not found or permission denied
[INFO] Retrying in 30 seconds...
```
