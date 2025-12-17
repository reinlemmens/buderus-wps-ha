# DHW Temperature Sensor Fix - Summary

## Problem Identified
- **HA was showing**: 53.3°C
- **Actual temperature**: 26.5-27°C
- **Discrepancy**: ~26°C error!

## Root Cause
The DHW temperature sensor was mapped to the WRONG broadcast position:
- **Incorrect**: Base=0x0060-0x0063, Idx=58 (reading ~54°C - likely DHW setpoint or supply temp)
- **Correct**: Base=0x0402/0x0403, Idx=78 (actual DHW tank temperature ~27°C)

## Fix Applied

### Files Modified
1. **buderus_wps/config.py** (lines 217-226)
   - Changed DHW sensor mapping from idx=58 to idx=78
   - Changed bases from 0x0060-0x0063 to 0x0402-0x0403

2. **buderus_wps/broadcast_monitor.py**
   - Added correct DHW_TEMP_ACTUAL mapping at (0x0402, 78) and (0x0403, 78)
   - Renamed old idx=58 to "DHW_SETPOINT_OR_SUPPLY" (not actual tank temp)
   - Updated PARAM_TO_BROADCAST for GT3_TEMP

3. **custom_components/buderus_wps/coordinator.py**
   - Added debug logging to show all broadcast temperatures

## How We Found It
Ran broadcast scanner on homeassistant.local which revealed:
```
Base       Idx    Temp       Note
----------------------------------------------------------------------
0x0060     58     54.8°C     >>> CURRENTLY USED (WRONG!)
0x0402     78     26.8°C     *** MATCHES PHYSICAL DISPLAY! ***
0x0403     78     27.6°C     *** MATCHES PHYSICAL DISPLAY! ***
```

## Testing Setup on homeassistant.local
Created dedicated testing environment at `~/buderus-testing/`:
- Full project copy with venv
- Can run CLI commands with: `cd ~/buderus-testing && sudo venv/bin/wps-cli <command>`
- Useful for future debugging

## Next Steps
1. **Restart Home Assistant** to apply the fix
2. **Verify** the DHW temperature sensor now shows ~27°C (matches physical display)
3. **Monitor** for a few heating cycles to ensure stability

## What idx=58 Actually Represents
Based on the ~54°C reading, idx=58 likely represents:
- DHW setpoint temperature (target), OR
- DHW supply temperature from heat pump

This needs further investigation but is NOT the actual tank temperature.

## Additional Findings
- Compressor frequency reading works correctly (0 Hz when off)
- Compressor status in HA should be verified during operation

##  Files Updated on HA
✅ `/config/custom_components/buderus_wps/config.py`
✅ `/config/custom_components/buderus_wps/broadcast_monitor.py`
✅ `/config/custom_components/buderus_wps/coordinator.py` (with debug logging)

Date: 2025-12-16
