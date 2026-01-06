# Contract: DHW Setpoint Temperature API

**Feature**: 017-dhw-setpoint-temp
**Date**: 2026-01-04

## Overview

This contract defines the interfaces for reading and writing the DHW setpoint temperature across the library, coordinator, and Home Assistant entity layers.

---

## Layer 1: Library (HeatPumpClient)

### Read Operation

**Method**: `read_parameter("DHW_CALCULATED_SETPOINT_TEMP")`

**Request**:
```python
result = client.read_parameter("DHW_CALCULATED_SETPOINT_TEMP", timeout=2.0)
```

**Response**:
```python
{
    "name": "DHW_CALCULATED_SETPOINT_TEMP",
    "idx": 385,
    "extid": "EE5991A93A02B8",
    "format": "tem",
    "min": 400,
    "max": 700,
    "read": 1,
    "raw": b"\x02\x26",  # Example: 550 = 55.0°C
    "decoded": 55.0      # Human-readable value
}
```

### Write Operation

**Method**: `write_value("DHW_CALCULATED_SETPOINT_TEMP", value)`

**Request**:
```python
client.write_value("DHW_CALCULATED_SETPOINT_TEMP", 55.0, timeout=2.0)
```

**Behavior**:
- Accepts human-readable temperature (e.g., 55.0)
- Validates against min/max range (40.0-70.0°C)
- Encodes to raw bytes (value × 10)
- Sends CAN frame to heat pump
- Raises `ValueError` if out of range

---

## Layer 2: Coordinator (BuderusCoordinator)

### Data Structure

**BuderusData modification**:
```python
@dataclass
class BuderusData:
    # ... existing fields ...
    dhw_setpoint: float | None  # NEW: DHW target temperature (40-70°C)
```

### Read (in _sync_fetch_data)

**Contract**:
```python
# Read DHW setpoint (best-effort with fallback to stale data)
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

### Write Method

**Method**: `async_set_dhw_setpoint(temp: float) -> None`

**Contract**:
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
    async with self._lock:
        await self.hass.async_add_executor_job(
            self._sync_set_dhw_setpoint, temp
        )

def _sync_set_dhw_setpoint(self, temp: float) -> None:
    """Synchronous DHW setpoint set (runs in executor)."""
    self._client.write_value("DHW_CALCULATED_SETPOINT_TEMP", temp)
    _LOGGER.info("Set DHW setpoint to %.1f°C", temp)
```

---

## Layer 3: Home Assistant Entity

### Entity Definition

**Class**: `BuderusDHWSetpointNumber`

**Attributes**:
```python
_attr_name = "DHW Setpoint Temperature"
_attr_icon = ICON_WATER_THERMOMETER
_attr_native_min_value = 40.0
_attr_native_max_value = 70.0
_attr_native_step = 0.5
_attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
_attr_mode = NumberMode.BOX
```

### Read Interface

**Property**: `native_value -> float | None`

**Contract**:
```python
@property
def native_value(self) -> float | None:
    """Return the current DHW setpoint in °C."""
    if self.coordinator.data is None:
        return None
    return self.coordinator.data.dhw_setpoint
```

### Write Interface

**Method**: `async_set_native_value(value: float) -> None`

**Contract**:
```python
async def async_set_native_value(self, value: float) -> None:
    """Set DHW setpoint temperature.

    Args:
        value: Temperature in °C (40.0 to 70.0)
    """
    await self.coordinator.async_set_dhw_setpoint(value)
    # Optimistic update for immediate UI feedback
    if self.coordinator.data is not None:
        from dataclasses import replace
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dhw_setpoint=value)
        )
```

---

## Error Handling

| Error Condition | Layer | Response |
|----------------|-------|----------|
| Value < 40.0°C | Coordinator | `ValueError` with message |
| Value > 70.0°C | Coordinator | `ValueError` with message |
| Heat pump unreachable | Library | `DeviceCommunicationError` |
| Read timeout | Library | `TimeoutError` |
| Stale data | Coordinator | Return last known value, log warning |

---

## CLI Interface

**Read**:
```bash
buderus-wps read DHW_CALCULATED_SETPOINT_TEMP
# Output: 55.0
```

**Write**:
```bash
buderus-wps write DHW_CALCULATED_SETPOINT_TEMP 52.0
# Output: Set DHW_CALCULATED_SETPOINT_TEMP to 52.0
```

Note: CLI uses existing `read_parameter`/`write_value` infrastructure - no new code required.
