# Quick Start: DHW Setpoint Temperature Implementation

**Feature**: 017-dhw-setpoint-temp
**Date**: 2026-01-04

## Overview

This guide provides step-by-step implementation instructions for adding the DHW Setpoint Temperature parameter. Total estimated changes: ~60 lines of code across 3 files.

---

## Step 1: Update BuderusData Dataclass

**File**: `custom_components/buderus_wps/coordinator.py`

Add new field to the dataclass (around line 48):

```python
@dataclass
class BuderusData:
    """Data class for heat pump readings."""
    temperatures: dict[str, float | None]
    compressor_running: bool
    energy_blocked: bool
    dhw_extra_duration: int
    heating_season_mode: int | None
    dhw_program_mode: int | None
    heating_curve_offset: float | None
    dhw_stop_temp: float | None
    dhw_setpoint: float | None  # ADD THIS LINE
```

---

## Step 2: Add Read Logic to Coordinator

**File**: `custom_components/buderus_wps/coordinator.py`

In `_sync_fetch_data()`, add read logic after `dhw_stop_temp` section (around line 625):

```python
# Get DHW setpoint temperature (best-effort)
# PROTOCOL: DHW_CALCULATED_SETPOINT_TEMP is the normal operation target temp
dhw_setpoint: float | None = None
try:
    result = self._client.read_parameter("DHW_CALCULATED_SETPOINT_TEMP")
    decoded = result.get("decoded")
    if decoded is not None:
        dhw_setpoint = float(decoded)
except Exception as err:
    _LOGGER.warning("RTR FAILED for DHW_CALCULATED_SETPOINT_TEMP: %s", err)
    if self._last_known_good_data is not None:
        dhw_setpoint = self._last_known_good_data.dhw_setpoint
```

Update the `BuderusData` construction to include the new field:

```python
result = BuderusData(
    temperatures=temperatures,
    compressor_running=compressor_running,
    energy_blocked=energy_blocked,
    dhw_extra_duration=dhw_extra_duration,
    heating_season_mode=heating_season_mode,
    dhw_program_mode=dhw_program_mode,
    heating_curve_offset=heating_curve_offset,
    dhw_stop_temp=dhw_stop_temp,
    dhw_setpoint=dhw_setpoint,  # ADD THIS LINE
)
```

---

## Step 3: Add Write Method to Coordinator

**File**: `custom_components/buderus_wps/coordinator.py`

Add after `async_set_dhw_stop_temp` method (around line 920):

```python
async def async_set_dhw_setpoint(self, temp: float) -> None:
    """Set DHW setpoint temperature.

    Args:
        temp: Temperature in °C (40.0 to 70.0)

    Raises:
        ValueError: If temperature outside allowed range
    """
    if not 40.0 <= temp <= 70.0:
        raise ValueError(
            f"DHW setpoint must be between 40.0 and 70.0°C, got {temp}"
        )
    _LOGGER.debug("async_set_dhw_setpoint called with temp=%.1f", temp)
    try:
        async with self._lock:
            await self.hass.async_add_executor_job(
                self._sync_set_dhw_setpoint, temp
            )
        _LOGGER.debug("async_set_dhw_setpoint completed successfully")
    except Exception as err:
        _LOGGER.error("async_set_dhw_setpoint FAILED: %s", err)
        raise

def _sync_set_dhw_setpoint(self, temp: float) -> None:
    """Synchronous DHW setpoint set (runs in executor)."""
    _LOGGER.debug("_sync_set_dhw_setpoint called with temp=%.1f", temp)
    try:
        self._client.write_value("DHW_CALCULATED_SETPOINT_TEMP", temp)
        _LOGGER.info("Set DHW setpoint to %.1f°C", temp)
    except Exception as err:
        _LOGGER.error("_sync_set_dhw_setpoint FAILED: %s", err)
        raise
```

---

## Step 4: Add Number Entity

**File**: `custom_components/buderus_wps/number.py`

Add new entity class after `BuderusDHWStopTempNumber`:

```python
class BuderusDHWSetpointNumber(BuderusEntity, NumberEntity):
    """Number entity for DHW setpoint temperature (40-70°C).

    This parameter controls the target temperature for normal DHW operation.
    Distinct from DHW Stop Temperature which is for boost/extra mode.
    """

    _attr_name = "DHW Setpoint Temperature"
    _attr_icon = ICON_WATER_THERMOMETER
    _attr_native_min_value = 40.0
    _attr_native_max_value = 70.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the DHW setpoint temperature number."""
        super().__init__(coordinator, "dhw_setpoint", entry)

    @property
    def native_value(self) -> float | None:
        """Return the current DHW setpoint in °C."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_setpoint

    async def async_set_native_value(self, value: float) -> None:
        """Set DHW setpoint temperature.

        Args:
            value: Temperature in °C (40.0 to 70.0)
        """
        import logging
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.debug("BuderusDHWSetpointNumber.async_set_native_value called with value=%.1f", value)
        try:
            await self.coordinator.async_set_dhw_setpoint(value)
            # Optimistic update for immediate UI feedback
            if self.coordinator.data is not None:
                from dataclasses import replace
                self.coordinator.async_set_updated_data(
                    replace(self.coordinator.data, dhw_setpoint=value)
                )
            _LOGGER.debug("BuderusDHWSetpointNumber.async_set_native_value completed")
        except Exception as err:
            _LOGGER.error("BuderusDHWSetpointNumber.async_set_native_value FAILED: %s", err)
            raise
```

---

## Step 5: Register Entity

**File**: `custom_components/buderus_wps/number.py`

Update `async_setup_entry` to include the new entity (around line 25):

```python
async_add_entities([
    BuderusDHWExtraDurationNumber(coordinator, entry),
    BuderusHeatingCurveOffsetNumber(coordinator, entry),
    BuderusDHWStopTempNumber(coordinator, entry),
    BuderusDHWSetpointNumber(coordinator, entry),  # ADD THIS LINE
])
```

---

## Step 6: Add Tests

**File**: `tests/unit/test_ha_number.py` (add to existing file)

```python
def test_dhw_setpoint_number_properties():
    """Test DHW setpoint number entity properties."""
    # Verify min/max/step match parameter definition
    assert BuderusDHWSetpointNumber._attr_native_min_value == 40.0
    assert BuderusDHWSetpointNumber._attr_native_max_value == 70.0
    assert BuderusDHWSetpointNumber._attr_native_step == 0.5
```

---

## Verification Checklist

- [ ] `BuderusData` has `dhw_setpoint` field
- [ ] Coordinator reads `DHW_CALCULATED_SETPOINT_TEMP` in `_sync_fetch_data`
- [ ] Coordinator has `async_set_dhw_setpoint` method with 40-70°C validation
- [ ] `BuderusDHWSetpointNumber` entity class exists
- [ ] Entity registered in `async_setup_entry`
- [ ] Tests pass: `pytest tests/unit/test_ha_number.py -v`
- [ ] Manual test: Entity appears in HA, read/write works

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `coordinator.py` | Add field to dataclass, read in fetch, add write methods |
| `number.py` | Add `BuderusDHWSetpointNumber` class, register in setup |
| `test_ha_number.py` | Add property validation tests |

**Total**: ~60 lines of new code
