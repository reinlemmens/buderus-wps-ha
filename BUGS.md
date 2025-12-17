# Bug List

This document tracks known bugs and issues in the Buderus WPS Home Assistant integration and CLI.

## Active Bugs

### BUG-001: Missing Circuit Control Entities in HA Integration
**Priority**: High
**Component**: Home Assistant Integration
**Reported**: 2025-12-16
**GitHub Issue**: [#3](https://github.com/reinlemmens/buderus-wps-ha/issues/3)

**Description**:
The Home Assistant integration does not expose individual heating circuit controls. Users cannot control circuit modes (Comfort/Eco/Auto/Off) or setpoints from Home Assistant.

**Current State**:
- Integration only exposes global controls (heating season mode, DHW mode)
- Circuit parameters exist in the library (`ROOM_PROGRAM_MODE_C1`, `ROOM_SETPOINT_C1`, etc.)
- Circuit API exists in `buderus_wps.menu_api.Circuit` class
- No HA entities created for circuits

**Impact**:
- Users must stop HA integration and use CLI to control individual circuits
- Cannot automate circuit-specific heating control from HA
- Ventilo/floor heating circuits cannot be controlled per-room

**Expected Behavior**:
The integration should provide:
- Select entity for each circuit's program mode (Comfort/Eco/Auto/Off)
- Number entity for each circuit's setpoint temperature
- Sensor entities for each circuit's current temperature
- Entities should respect `sensor_config.yaml` circuit definitions

**Workaround**:
1. Stop HA integration to release USB lock
2. Use CLI: `wps-cli write ROOM_PROGRAM_MODE_C1 <value>`
3. Restart HA integration

**Related Files**:
- `custom_components/buderus_wps/select.py` - needs circuit mode selects
- `custom_components/buderus_wps/number.py` - needs circuit setpoint numbers
- `custom_components/buderus_wps/sensor.py` - needs circuit temperature sensors
- `custom_components/buderus_wps/coordinator.py` - needs circuit data polling
- `buderus_wps/menu_api.py` - Circuit class already implemented

**References**:
- Spec 009-sensor-config mentions circuit configuration
- FHEM parameters: `ROOM_PROGRAM_MODE_C{n}`, `ROOM_SETPOINT_C{n}`, `ROOM_TEMP_C{n}`

---

### BUG-002: Compressor Running Status Not Displayed in HA
**Priority**: Medium
**Component**: Home Assistant Integration - Binary Sensor
**Reported**: 2025-12-16
**GitHub Issue**: [#4](https://github.com/reinlemmens/buderus-wps-ha/issues/4)

**Description**:
The heat pump compressor is running, but the Home Assistant integration does not show the compressor status correctly.

**Current State**:
- Compressor is physically running (verified by user)
- HA integration does not display "running" status
- May be missing binary sensor or sensor shows incorrect state

**Impact**:
- Users cannot monitor compressor operation from HA
- Cannot create automations based on compressor status
- No visibility into actual heat pump operation

**Expected Behavior**:
- Binary sensor `binary_sensor.buderus_wps_compressor` should show "on" when compressor is running
- Binary sensor should show "off" when compressor is idle
- Status should update within scan interval (default 30s)

**Root Cause Analysis**:
The compressor status is determined by reading `COMPRESSOR_REAL_FREQUENCY` and checking if it's > 0:
- Parameter: `COMPRESSOR_REAL_FREQUENCY`
- Location: `buderus_wps/menu_api.py:164-174` (StatusView.compressor_running)
- Logic: Returns `True` if frequency > 0 Hz, `False` if 0 or on error
- Method: RTR (Remote Transmission Request) read

**Possible Issues**:
1. **RTR Read Failing**: Similar to temperature parameters (see spec 012-broadcast-read-fallback), `COMPRESSOR_REAL_FREQUENCY` may return invalid data via RTR (0.1 Hz or 0 Hz) even when compressor is running
2. **Exception Swallowing**: The try/except catches KeyError and returns False, hiding read failures
3. **Broadcast-Only Parameter**: Parameter may be broadcast by heat pump but not respond to RTR queries
4. **Logging**: Debug-level only - coordinator.py:364 logs "Could not read compressor status" at DEBUG level

**Diagnostic Steps**:
1. Test direct CLI read: `wps-cli read COMPRESSOR_REAL_FREQUENCY`
2. Compare RTR vs broadcast: `wps-cli read COMPRESSOR_REAL_FREQUENCY --broadcast --duration 10`
3. Check if value is exactly 0.1 (invalid) or actual frequency
4. Review coordinator logs at DEBUG level for exceptions

**Likely Fix**:
Apply broadcast fallback to compressor frequency (similar to temperature reads in spec 012):
- Try RTR read first
- If result is 0 or invalid, fall back to broadcast monitoring
- Or always use broadcast for compressor frequency

**Related Files**:
- `buderus_wps/menu_api.py:164-174` - StatusView.compressor_running (needs broadcast fallback)
- `buderus_wps/menu_structure.py:72` - COMPRESSOR_REAL_FREQUENCY parameter mapping
- `custom_components/buderus_wps/coordinator.py:359-367` - compressor status polling
- `custom_components/buderus_wps/binary_sensor.py:61-65` - displays the status

**Related Specs**:
- Spec 012-broadcast-read-fallback: Similar issue with temperature parameters returning 0.1°C via RTR

---

## Bug Tracking Notes

### Status Values
- **Active**: Bug is confirmed and not yet fixed
- **In Progress**: Fix is being developed
- **Fixed**: Fix is complete and committed
- **Verified**: Fix is tested and confirmed working

### Priority Levels
- **Critical**: System unusable or data loss
- **High**: Major functionality broken
- **Medium**: Feature not working as expected
- **Low**: Minor issue or cosmetic

### Reporting New Bugs
When adding a bug:
1. Assign next BUG-XXX number
2. Include priority, component, and date
3. Describe current vs expected behavior
4. List affected files and workarounds
5. Add investigation steps if needed
