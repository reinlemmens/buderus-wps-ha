# Compressor Detection Investigation

**Date**: 2024-12-28
**Status**: Under Investigation

## Problem Statement

The compressor binary sensor in Home Assistant consistently shows "Not running" even when the compressor is actively running (verified by user starting DHW extra production and observing power consumption).

## Current Implementation

The coordinator reads compressor status via RTR (Remote Transmit Request):

```python
result = self._client.read_parameter("COMPRESSOR_REAL_FREQUENCY")
frequency = int(result.get("decoded", 0) or 0)
compressor_running = frequency > 0
```

**Parameter Details:**
- `COMPRESSOR_REAL_FREQUENCY` is at idx=279 in parameter_data.py
- Previous implementation used `COMPRESSOR_STATE` (idx=278) which always returned 0

## RTR Testing Results (2024-12-28)

### Test Method
Sent RTR requests via USBtin while compressor was running (DHW extra production active).

### Observations

1. **RTR Command Format Tested:**
   - `R048B02700` (RTR for idx=139, base=0x0270) - got 'Z' (OK) but no matching response frame
   - `T048B02700` (Transmit 0 bytes for idx=139) - got 'Z' plus broadcast frames
   - Various idx values tested (138, 139, 141, 24)

2. **Response Analysis:**
   The RTR requests received acknowledgment ('Z') but the response frames didn't include the expected parameter index. Instead, general broadcast traffic was received.

3. **Broadcast Data on Base 0x0270:**
   ```
   idx=0: 51.6°C (likely condenser temp)
   idx=1: 10.1°C (outdoor temp)
   idx=2: 71.9°C (high temp, possibly discharge)
   ```

   No frequency-like values (0-100 Hz range) were observed in broadcasts.

## Potential Issues

### 1. RTR Response Format
The Buderus WPS may not respond to standard SLCAN RTR requests. The protocol might require:
- A specific message priority (high nibble of CAN ID)
- A different request format
- Multiple request retries with specific timing

### 2. Parameter Index Mismatch
The library's `read_parameter()` function should look up idx=279 for `COMPRESSOR_REAL_FREQUENCY`, but verification is needed.

### 3. CAN ID Construction
The RTR CAN ID might need different bit layout than:
```
CAN_ID = (priority << 24) | (idx << 16) | base
```

## Alternative Detection Methods

### Option A: Power-Based Detection
Monitor compressor power consumption via external sensor (e.g., Shelly EM). If power > threshold (e.g., 500W), compressor is running.

**Pros:** Reliable, independent of CAN protocol
**Cons:** Requires additional hardware

### Option B: Temperature Delta
Monitor supply-return temperature delta. When compressor runs, delta increases.

**Pros:** Uses existing sensors
**Cons:** Delayed detection, may have false positives during DHW charging

### Option C: Operating State Parameter
Try reading `HP_OPERATING_STATE` or similar parameters that might indicate compressor activity.

### Option D: Broadcast Frequency Detection
Some heat pumps broadcast compressor frequency periodically. Need longer capture to find if this exists.

## Raw CAN Capture Data

### Frames on Base 0x0270 (8-second capture):
```
Base=0x0270:
  idx=0: raw=516 (51.6°C)
  idx=1: raw=101 (10.1°C)
  idx=2: raw=719 (71.9°C)
```

### Frames on Related Bases:
```
Base=0x4270:
  idx=0: 72.6°C
  idx=1: 31.4°C (DHW temp)

Base=0x8270:
  idx=0: 42.8°C (supply?)
  idx=1: 39.4°C (return?)

Base=0xC270:
  idx=0: 55.3°C
```

## Update: 2025-12-28

### CAN ID Bit Extraction Verification

**Critical Finding:** The library's bit extraction formula was verified to be correct:
```python
base = can_id & 0x3FFF         # 14 bits
idx = (can_id >> 14) & 0xFFF   # 12 bits
direction = can_id >> 26       # 6 bits
```

Previous diagnostic scripts incorrectly used:
```python
base = can_id & 0xFFFF         # 16 bits - WRONG
idx = (can_id >> 16) & 0xFF    # 8 bits - WRONG
```

### Verified Sensor Mappings (10-second capture with CORRECT formula)

| Sensor | Base | Idx | Value |
|--------|------|-----|-------|
| DHW | 0x0270 | 4 | 40.8°C ✓ |
| Supply | 0x0270 | 6 | 28.1°C ✓ |
| Setpoint C1 | 0x0060 | 33 | 22.0°C ✓ |
| Setpoint C2 | 0x0061 | 33 | 23.2°C ✓ |
| Setpoint C3 | 0x0062 | 33 | 23.0°C ✓ |
| Return | 0x0270 | 5 | Not found in 10s window |
| Room temps | 0x006x | 0 | Not found in 10s window |

### Current Status

- **Config reverted:** DHW back to `(0x0270, 4)`, setpoints back to `(0x006x, 33)`
- **CAN data confirmed:** HA is receiving CAN frames (verified by checking USBtin buffer)
- **Integration active:** All sensor entities are registered in HA
- **Port contention:** HA holds serial port; direct testing not possible while HA connected

### Compressor Detection

The RTR-based compressor detection (`COMPRESSOR_REAL_FREQUENCY`) still needs verification. The RTR protocol implementation may need adjustment.

## Next Steps

1. [x] Verify library's bit extraction formula - DONE
2. [x] Revert sensor mappings to correct values - DONE
3. [ ] Verify RTR CAN ID construction for parameter reads
4. [ ] Test longer broadcast collection (15-30s) for infrequent values
5. [ ] Consider power-based compressor detection as fallback

## References

- Parameter registry: `buderus_wps/parameter_data.py` (idx=279 for COMPRESSOR_REAL_FREQUENCY)
- FHEM module: Uses similar RTR mechanism for parameter reads
- menu_api.py: Documents `COMPRESSOR_REAL_FREQUENCY > 0` as reliable indicator
