# DHW Temperature Sensor Bug Report

## Issue Summary

**Critical Bug**: Home Assistant integration shows incorrect DHW (hot water) temperature

- **HA Reading**: 51.9°C
- **Actual Temperature** (from heat pump display): 27.2°C
- **Discrepancy**: ~25°C difference
- **Impact**: HIGH - Users cannot trust DHW temperature readings, hot water is too cold to use

## Root Cause

The sensor mapping in `buderus_wps/config.py` uses broadcast position **idx=58** for DHW temperature, but this position does NOT contain the actual tank temperature (GT3_TEMP).

Current incorrect mapping:
```python
# In DEFAULT_SENSOR_MAPPINGS:
SensorMapping(base=0x0060, idx=58, sensor=SensorType.DHW),  # WRONG!
SensorMapping(base=0x0061, idx=58, sensor=SensorType.DHW),  # WRONG!
SensorMapping(base=0x0062, idx=58, sensor=SensorType.DHW),  # WRONG!
SensorMapping(base=0x0063, idx=58, sensor=SensorType.DHW),  # WRONG!
```

## What idx=58 Actually Contains

Broadcast position idx=58 shows ~52°C, which could be:
- DHW setpoint temperature (target, not actual)
- Supply temperature to DHW circuit
- Some other temperature sensor

**This needs investigation** to understand what idx=58 represents.

## Next Steps to Fix

### 1. Identify Correct Broadcast Position

Run one of these diagnostic methods:

**Method A: Enable HA Debug Logging**
```yaml
# configuration.yaml
logger:
  logs:
    custom_components.buderus_wps: debug
```

Then check logs for temperature broadcasts and find which shows 27.2°C.

**Method B: Run Diagnostic Script**
```bash
python3 /mnt/supervisor/addons/local/buderus-wps-ha/find_dhw_temp.py
```
or
```bash
python3 /mnt/supervisor/addons/local/buderus-wps-ha/test_broadcast_positions.py
```

### 2. Update Sensor Mappings

Once correct position is identified (e.g., if it's idx=33 on base 0x0060):

**File: `buderus_wps/config.py`** (lines 222-226)
```python
# GT3 - DHW tank temperature (broadcasts from multiple circuits)
SensorMapping(base=0x0060, idx=33, sensor=SensorType.DHW),  # CORRECTED
SensorMapping(base=0x0061, idx=33, sensor=SensorType.DHW),  # CORRECTED
SensorMapping(base=0x0062, idx=33, sensor=SensorType.DHW),  # CORRECTED
SensorMapping(base=0x0063, idx=33, sensor=SensorType.DHW),  # CORRECTED
```

**File: `buderus_wps/broadcast_monitor.py`** (line 155)
```python
"GT3_TEMP": (None, 33),  # CORRECTED - None = search all circuit bases
```

**File: `buderus_wps/broadcast_monitor.py`** (line 116)
```python
(0x0060, 33): ("GT3_TEMP_ACTUAL", "tem"),  # CORRECTED - Actual DHW tank temp
```

And rename the old idx=58 to reflect what it actually is (once we know).

### 3. Update Documentation

**File: `specs/012-broadcast-read-fallback/research.md`** (line 135)
```markdown
| GT3_TEMP | 0x0060 | 33 | GT3_TEMP_ACTUAL |  # CORRECTED
```

**File: `specs/002-buderus-wps-python-class/protocol-broadcast-mapping.md`** (lines 147-153)
Update DHW temperature section with correct broadcast position.

### 4. Add Tests

Create test to verify DHW temperature mapping:
- Contract test for GT3_TEMP broadcast position
- Integration test comparing RTR read vs broadcast read
- Acceptance test verifying temperature matches physical display

## Likely Candidates for Actual DHW Temp

Based on protocol documentation and typical ranges:

| Base | Idx | Typical Value | Description | Likelihood |
|------|-----|---------------|-------------|------------|
| 0x0060 | 33 | 17-30°C | Common sensor / Room temp | **HIGH** |
| 0x0270 | 4 | 20-50°C | Heat Exchanger temp | Medium |
| 0x0270 | 0 | 35-50°C | Supply Line temp | Low |

**Most likely**: idx=33 on circuit bases (0x0060-0x0063)

## Historical Context

The current mapping (idx=58) was documented in protocol-broadcast-mapping.md with:
```markdown
| 0x0C0E8060 | 0x0060 | 58 | DHW Actual Temperature |
```

This was based on hardware testing that observed ~54°C at that position. However, this appears to be incorrect or the testing was done when the DHW was at setpoint temperature, not showing the actual sensor reading.

## Impact on Users

Until this is fixed:
1. Users see incorrect DHW temperature in HA
2. Automations based on DHW temp will malfunction
3. Users cannot monitor actual hot water status
4. May not notice when DHW fails to heat properly

## Priority

**CRITICAL** - This affects core sensor functionality and could mask heating system failures.
