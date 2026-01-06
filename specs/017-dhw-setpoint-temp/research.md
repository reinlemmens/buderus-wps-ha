# Research: DHW Setpoint Temperature Parameter

**Feature**: 017-dhw-setpoint-temp
**Date**: 2026-01-04

## Research Questions

### 1. Parameter Verification

**Question**: Does `DHW_CALCULATED_SETPOINT_TEMP` (idx 385) work correctly for read/write?

**Finding**: Yes - parameter is defined in FHEM reference (`26_KM273v018.pm` line 3254-3255) as "preset for hot water temperature" and is included in the settable parameters list.

**Evidence**:
- Parameter definition in `parameter_defaults.py`:
  ```python
  {
      "idx": 385,
      "extid": "EE5991A93A02B8",
      "max": 700,  # 70.0°C
      "min": 400,  # 40.0°C
      "format": "tem",
      "read": 1,
      "text": "DHW_CALCULATED_SETPOINT_TEMP",
  }
  ```
- Writable: `min < max` confirms write capability
- Format: `tem` (temperature, value / 10 = °C)

**Decision**: Use `DHW_CALCULATED_SETPOINT_TEMP` as the parameter name.

---

### 2. Existing Pattern Analysis

**Question**: What is the established pattern for temperature number entities?

**Finding**: `BuderusDHWStopTempNumber` in `number.py` provides the exact pattern to follow.

**Evidence** (from `custom_components/buderus_wps/number.py:137-188`):
- Extends `BuderusEntity` and `NumberEntity`
- Uses `_attr_name`, `_attr_icon`, `_attr_native_min/max_value`, `_attr_native_step`
- `native_value` property reads from `coordinator.data.dhw_stop_temp`
- `async_set_native_value` calls coordinator write method with optimistic update

**Decision**: Clone `BuderusDHWStopTempNumber` pattern for `BuderusDHWSetpointNumber`.

---

### 3. Step Increment

**Question**: What step increment should be used (0.5°C vs 1.0°C)?

**Finding**: Use 0.5°C for consistency with existing temperature controls.

**Evidence**:
- `BuderusDHWStopTempNumber` uses `_attr_native_step = 0.5`
- `BuderusHeatingCurveOffsetNumber` uses `_attr_native_step = 0.5`
- Heat pump display typically shows 0.5°C increments

**Decision**: Use `_attr_native_step = 0.5` for consistency.

---

### 4. Naming Conventions

**Question**: What should the entity be named in Home Assistant?

**Finding**: Use "DHW Setpoint Temperature" to distinguish from "DHW Stop Temperature".

**Rationale**:
- "Setpoint" clearly indicates this is the target temperature
- "Stop Temperature" is used for the charging cutoff (`XDHW_STOP_TEMP`)
- Consistent with HVAC terminology where "setpoint" = desired target

**Decision**:
- Entity name: "DHW Setpoint Temperature"
- Entity ID: `number.heat_pump_dhw_setpoint_temperature`
- Icon: `ICON_WATER_THERMOMETER` (same as DHW Stop Temp)

---

### 5. Coordinator Data Field

**Question**: What field name should be used in `BuderusData`?

**Finding**: Use `dhw_setpoint` to parallel existing `dhw_stop_temp`.

**Evidence**: Existing fields follow pattern:
- `dhw_stop_temp` for XDHW_STOP_TEMP
- `dhw_extra_duration` for XDHW_TIME
- `heating_curve_offset` for HEATING_CURVE_PARALLEL_OFFSET_GLOBAL

**Decision**: Add `dhw_setpoint: float | None` to `BuderusData` dataclass.

---

## Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Parameter | `DHW_CALCULATED_SETPOINT_TEMP` (idx 385) | FHEM documented as "preset for hot water temperature" |
| Range | 40.0°C - 70.0°C | From parameter definition (min=400, max=700) |
| Step | 0.5°C | Consistent with existing temperature controls |
| Entity name | "DHW Setpoint Temperature" | Clear distinction from "DHW Stop Temperature" |
| Data field | `dhw_setpoint` | Follows existing naming pattern |
| Pattern | Clone `BuderusDHWStopTempNumber` | Proven, tested implementation |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| 1.0°C step | Inconsistent with other temperature entities |
| "Hot Water Target" name | Less technical, might confuse with actual tank temperature |
| Separate API in menu_api.py | Overkill for single parameter, direct coordinator access sufficient |
