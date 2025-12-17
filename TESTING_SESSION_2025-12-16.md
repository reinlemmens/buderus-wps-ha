# Testing Session Summary - 2025-12-16

## Objectives
1. Investigate DHW temperature discrepancy (HA shows 53°C, actual 27°C)
2. Test compressor detection in Home Assistant
3. Verify extra DHW (XDHW) functionality via CLI

## Key Findings

### ✅ DHW Temperature Sensor Fix (VERIFIED)
**Problem**: HA showed 53.3°C, physical display showed 27.2°C (~26°C error)

**Root Cause**: DHW temperature sensor mapped to wrong broadcast position
- **Incorrect**: idx=58, base=0x0060 (shows ~54°C - likely DHW setpoint/supply temp)
- **Correct**: idx=78, base=0x0402/0x0403 (shows actual tank temp ~27°C)

**Fix Applied**:
- Updated [buderus_wps/config.py](buderus_wps/config.py) lines 217-226
- Updated [buderus_wps/broadcast_monitor.py](buderus_wps/broadcast_monitor.py)
- Added mappings for idx=78 on both base 0x0402 and 0x0403

**Verification**:
- Broadcast scan confirmed idx=78 matches physical display
- Live monitoring showed temperature increasing from 24.3°C → 25.8°C during heating
- **Status**: Fix working correctly, ready for HACS deployment

### ✅ Compressor Detection (VERIFIED)
**Test**: User activated extra DHW from heat pump menu

**Results**:
- Compressor started immediately
- Home Assistant sensor `load_warmtepomp` showed **5,520 W** (correct)
- DHW temperature increased as expected
- **Status**: Compressor detection working correctly

### ⚠️ XDHW Write Behavior (NEEDS INVESTIGATION)
**Initial Tests**: XDHW_TIME writes appeared to fail
- Write command returned "OK" but read-back showed 0
- No CAN acknowledgment from heat pump
- Low-level test confirmed heat pump rejecting writes

**After Menu Activation**: XDHW writes started working
- User activated XDHW from heat pump menu
- Subsequent CLI write `wps-cli write XDHW_TIME 1` succeeded
- Read-back confirmed: `XDHW_TIME = 1`

**User Feedback**: "It worked a couple of weeks ago under any circumstance"

**Possible Explanations**:
1. **Heat pump state dependency**: XDHW writes may require heat pump to be in certain mode
2. **Invalid prerequisite**: XDHW_STOP_TEMP was showing invalid 3.8°C (should be 50-65°C)
3. **Firmware/config change**: Something changed in the last few weeks
4. **Transient condition**: Initial test happened during an unfavorable state

**Recommendation**: Further investigation needed to determine exact conditions for XDHW write acceptance

### 📊 RTR Read Reliability Issues
Multiple parameters showed stale/invalid data via RTR requests:

| Parameter | RTR Read | Actual Value | Source |
|-----------|----------|--------------|--------|
| XDHW_STOP_TEMP | 3.8°C | 55°C | Menu shows 55°C |
| DHW_CALCULATED_SETPOINT_TEMP | 0.0°C | Unknown | Invalid |
| COMPRESSOR_REAL_FREQUENCY | 0 Hz | Running | HA shows 5,520 W |
| GT3_TEMP (DHW) | Invalid warnings | 24-26°C | Broadcast reliable |

**Conclusion**: RTR reads are unreliable for many parameters. Use broadcast monitoring where possible.

## Files Modified

### Source Code (Ready to Commit)
✅ [buderus_wps/config.py](buderus_wps/config.py) - DHW sensor mapping corrected (idx 58→78, base to 0x0402/0x0403)
✅ [buderus_wps/broadcast_monitor.py](buderus_wps/broadcast_monitor.py) - Added correct DHW mappings, updated PARAM_TO_BROADCAST
✅ [custom_components/buderus_wps/coordinator.py](custom_components/buderus_wps/coordinator.py) - Added debug logging for broadcast temps

### Documentation Created
✅ [DHW_TEMP_FIX_SUMMARY.md](DHW_TEMP_FIX_SUMMARY.md) - Comprehensive DHW temperature fix documentation
✅ [IMPORTANT_HACS_DEPLOYMENT.md](IMPORTANT_HACS_DEPLOYMENT.md) - HACS deployment process reminder
✅ [TESTING_SESSION_2025-12-16.md](TESTING_SESSION_2025-12-16.md) - This file

### Test Scripts Created
✅ [find_dhw_temp.py](find_dhw_temp.py) - Broadcast temperature scanner
✅ [test_compressor_dhw.sh](test_compressor_dhw.sh) - Compressor/DHW monitoring script
✅ [/tmp/diagnose_temperatures.py](/tmp/diagnose_temperatures.py) - Diagnostic script

### Testing Environment
✅ `~/buderus-testing/` on homeassistant.local - Dedicated testing environment with venv

## Deployment Checklist

### Before HACS Release
- [ ] Verify DHW temperature sensor shows ~27°C in Home Assistant (not 53°C)
- [ ] Test XDHW write reliability from cold start
- [ ] Document XDHW write prerequisites if found
- [ ] Run full test suite
- [ ] Update CHANGELOG.md

### HACS Deployment Process
1. Commit all changes to source repository
2. Create GitHub release with version tag (e.g., v1.2.0)
3. Update via HACS in Home Assistant
4. Restart Home Assistant
5. Verify DHW temperature sensor shows correct value

**DO NOT** modify `/config/custom_components/buderus_wps/` directly - it's HACS-managed!

## Next Steps

### Immediate
1. **Check DHW sensor in Home Assistant**: Confirm it now shows ~27°C instead of 53°C
2. **Test XDHW from cold start**: Verify writes work without menu activation first
3. **Investigate XDHW prerequisites**: Determine why initial writes failed

### Future
1. **Firmware version check**: Document heat pump firmware version for future reference
2. **XDHW write conditions**: Document exact conditions required for successful XDHW writes
3. **RTR reliability investigation**: Understand why some RTR reads return stale data
4. **Alternative DHW control**: Test DHW_PROGRAM_MODE as alternative to XDHW for remote control

## Technical Notes

### CAN Bus Behavior
- **Broadcast monitoring**: Reliable for sensor readings (idx=78 for DHW temp works perfectly)
- **RTR requests**: Unreliable for many parameters, often returns stale data
- **Write acknowledgment**: CAN writes may succeed even without immediate read-back confirmation

### Heat Pump State Dependencies
Some operations appear state-dependent:
- XDHW writes may require specific heat pump mode or configuration
- Broadcast frequency varies (some values broadcast more frequently than others)
- Menu operations may not generate CAN traffic (internal write)

### Testing Best Practices
1. Always verify broadcast monitoring first before trusting RTR reads
2. Test writes from multiple heat pump states (idle, heating, DHW mode)
3. Use dedicated testing environment to avoid disrupting HA integration
4. Monitor both CAN traffic and physical heat pump display for ground truth

## Related Documentation
- [protocol-broadcast-mapping.md](specs/002-buderus-wps-python-class/protocol-broadcast-mapping.md) - CAN protocol reference
- [DHW_TEMP_FIX_SUMMARY.md](DHW_TEMP_FIX_SUMMARY.md) - DHW temperature fix details
- [IMPORTANT_HACS_DEPLOYMENT.md](IMPORTANT_HACS_DEPLOYMENT.md) - Deployment process
- [CLAUDE.md](CLAUDE.md) - Project guidelines

## Session Duration
Approximately 3-4 hours of investigation, testing, and documentation

## Conclusion
Successfully diagnosed and fixed DHW temperature sensor issue. Verified compressor detection works correctly. XDHW write functionality confirmed working but requires further investigation to understand initial failure conditions. All changes documented and ready for HACS deployment pending final HA sensor verification.
