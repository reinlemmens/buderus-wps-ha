# DHW Temperature Sensor Diagnostic Steps

## Problem
Home Assistant shows DHW temperature as 51.9°C, but actual heat pump display shows 27.2°C.
The integration is reading from the wrong broadcast position.

## Solution: Enable Debug Logging

### Step 1: Enable Debug Logging in Home Assistant

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.buderus_wps: debug
```

### Step 2: Restart Home Assistant

Either:
- Restart Home Assistant completely, OR
- Reload the Buderus WPS integration from Settings → Devices & Services → Buderus WPS → "⋮" → Reload

### Step 3: Wait for Data Collection

The integration updates every 30 seconds by default. Wait for 1-2 minutes for data to be collected.

### Step 4: Check the Logs

Go to Settings → System → Logs

Look for lines like:
```
=== ALL BROADCAST TEMPERATURES (20-70°C range) ===
  Base=0x0060, Idx= 33, Temp= 22.1°C
  Base=0x0060, Idx= 58, Temp= 51.9°C
  Base=0x0061, Idx= 58, Temp= 51.9°C
  ...
```

### Step 5: Find the Matching Temperature

1. Look for the temperature value that matches your heat pump display (27.2°C)
2. Note the **Base** and **Idx** values for that row
3. Report these values

Example: If you see:
```
  Base=0x0060, Idx= 33, Temp= 27.2°C
```

Then the correct mapping is: `Base=0x0060, Idx=33`

### Step 6: Update Configuration (After Identification)

Once we identify the correct broadcast position, we'll update:
- `buderus_wps/config.py` - DEFAULT_SENSOR_MAPPINGS
- `buderus_wps/broadcast_monitor.py` - PARAM_TO_BROADCAST

## Alternative: Run Diagnostic Script

If you have direct access to the system with the USB CAN adapter:

```bash
python3 /mnt/supervisor/addons/local/buderus-wps-ha/find_dhw_temp.py
```

This will show all temperature broadcasts and highlight candidates.

## Current Incorrect Mapping

Currently using:
- Base: 0x0060, 0x0061, 0x0062, 0x0063
- Idx: 58
- Reading: ~52°C (WRONG!)

## Expected Result

We need to find:
- Broadcast position showing ~27°C (actual DHW tank temperature)
- This will be the correct GT3_TEMP sensor

## Questions to Answer

1. Which broadcast position shows 27.2°C?
2. What does broadcast position idx=58 actually represent (showing 52°C)?
   - Could be DHW setpoint?
   - Could be supply temperature?
   - Could be a different sensor?
