# GT10/GT11 Diagnostic Instructions

## Problem
GT10 and GT11 showing 0.1°C instead of realistic brine temperatures.

## Run Diagnostic

**Option 1: SSH into Home Assistant directly**

```bash
# 1. Stop Home Assistant to release USB
ha core stop

# 2. Wait for it to stop
sleep 10

# 3. Run diagnostic
cd /config/custom_components/buderus_wps
python3 diagnose_brine_temps.py

# 4. Restart Home Assistant
ha core start
```

**Option 2: From the devcontainer (if you have direct HA access)**

```bash
# 1. Use HA CLI to stop core
ssh hassio@homeassistant.local
ha core stop

# 2. Run diagnostic (in same SSH session)
cd /config/custom_components/buderus_wps
python3 diagnose_brine_temps.py

# 3. Restart
ha core start
exit
```

## What the Diagnostic Will Show

The script will check:

1. ✅ **Element discovery cache** - What GT10/GT11 parameters were discovered
2. ✅ **Parameter indices** - Static defaults vs. discovered values
3. ✅ **Live RTR reads** - What raw data is being returned
4. ✅ **Min/Max ranges** - Whether parameters have valid ranges

## Expected Output

Look for lines like:

```
--- Reading GT10_TEMP ---
  Using: idx=638, min=0, max=0
  Raw bytes: b'\x00\x01'
  Raw hex: 0001
  Decoded: 0.1
  ✗ PROBLEM: Decoded to 0.1°C (raw value = 1)
```

This will tell us if:
- Parameter doesn't exist on your heat pump model
- Wrong idx is being used
- RTR is returning garbage (value = 1)
- Sensor is physically disconnected (DEAD)

## Alternative: Check HA Logs

If you can't run the diagnostic, check Home Assistant logs for:

```
grep -i "GT10\|GT11\|Element discovery" /config/home-assistant.log
```

Look for:
- "Element discovery: X elements, Y indices updated"
- "GT10_TEMP: idx=XXX, CAN ID=0xXXXXXXXX"
- "RTR FAILED for GT10_TEMP (idx=XXX): <error>"
