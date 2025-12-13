# Research: Home Assistant Integration

**Feature**: 011-ha-integration
**Date**: 2025-12-13

## Research Areas

### R1: Home Assistant NumberEntity Implementation

**Question**: How to properly implement a NumberEntity for DHW extra duration (0-24 hours)?

**Decision**: Use `NumberEntity` with `NumberMode.SLIDER` for intuitive UI

**Rationale**:
- Home Assistant's NumberEntity supports `native_min_value`, `native_max_value`, and `native_step`
- Mode can be `BOX` (text input) or `SLIDER` (visual slider)
- Slider is more intuitive for duration selection in the HA dashboard

**Implementation Pattern**:
```python
from homeassistant.components.number import NumberEntity, NumberMode

class DHWExtraDurationNumber(BuderusEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"
    _attr_mode = NumberMode.SLIDER
    _attr_device_class = None  # No standard device class for duration
    _attr_icon = "mdi:water-boiler"
```

**Alternatives Considered**:
- `NumberMode.BOX`: Requires typing exact value, less user-friendly
- Service call only: Requires automation/script, not accessible in dashboard

---

### R2: Exponential Backoff Pattern in Home Assistant

**Question**: How to implement exponential backoff for USB reconnection in HA coordinator?

**Decision**: Implement custom backoff in coordinator with `asyncio.sleep()`

**Rationale**:
- Home Assistant's `DataUpdateCoordinator` doesn't have built-in backoff for setup failures
- Must manage backoff state manually in the coordinator
- Reset backoff on successful connection

**Implementation Pattern**:
```python
class BuderusCoordinator(DataUpdateCoordinator):
    BACKOFF_INITIAL = 5  # seconds
    BACKOFF_MAX = 120    # seconds (2 minutes per spec)

    def __init__(self, ...):
        self._backoff_delay = self.BACKOFF_INITIAL
        self._reconnect_task: asyncio.Task | None = None

    async def _handle_connection_failure(self):
        """Schedule reconnection with exponential backoff."""
        if self._reconnect_task is not None:
            return  # Already reconnecting

        self._reconnect_task = self.hass.async_create_background_task(
            self._reconnect_with_backoff(),
            "buderus_wps_reconnect"
        )

    async def _reconnect_with_backoff(self):
        """Attempt reconnection with exponential backoff."""
        while not self._connected:
            _LOGGER.info("Attempting reconnection in %d seconds", self._backoff_delay)
            await asyncio.sleep(self._backoff_delay)

            try:
                await self.hass.async_add_executor_job(self._sync_connect)
                self._connected = True
                self._backoff_delay = self.BACKOFF_INITIAL  # Reset on success
                _LOGGER.info("Successfully reconnected to heat pump")
            except Exception as err:
                _LOGGER.warning("Reconnection failed: %s", err)
                self._backoff_delay = min(
                    self._backoff_delay * 2,
                    self.BACKOFF_MAX
                )

        self._reconnect_task = None
```

**Alternatives Considered**:
- `async_track_time_interval`: Too rigid, doesn't support backoff
- Third-party backoff library: Unnecessary dependency for simple pattern

---

### R3: Entity Naming Convention

**Question**: How to properly implement entity names with "Heat Pump" prefix in HA?

**Decision**: Set `_attr_name` with full descriptive name, rely on device grouping

**Rationale**:
- Home Assistant entities can have `has_entity_name = True` for device-prefixed names
- Since device name is "Buderus WPS Heat Pump", entity names like "Outdoor Temperature" would become "Buderus WPS Heat Pump Outdoor Temperature"
- Per spec clarification, names should be "Heat Pump X" format

**Implementation Pattern**:
```python
class BuderusEntity(CoordinatorEntity):
    _attr_has_entity_name = True  # Prefix with device name

# Sensor names become part of device context
SENSOR_NAMES = {
    SENSOR_OUTDOOR: "Outdoor Temperature",  # Shows as "Buderus WPS Heat Pump Outdoor Temperature"
    SENSOR_SUPPLY: "Supply Temperature",
    ...
}
```

**Alternative Approach** (if full name desired without device prefix):
```python
class BuderusEntity(CoordinatorEntity):
    _attr_has_entity_name = False  # Use full name directly

# Set full name in entity
_attr_name = "Heat Pump Outdoor Temperature"
```

**Decision**: Use `has_entity_name = True` with device name "Heat Pump" (not "Buderus WPS Heat Pump") to achieve desired naming pattern.

---

### R4: Scan Interval Validation

**Question**: How to validate scan_interval in YAML config (range 10-300 seconds)?

**Decision**: Use voluptuous `vol.All()` with `vol.Range()` validator

**Implementation Pattern**:
```python
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            cv.positive_int,
            vol.Range(min=10, max=300)
        ),
    })
}, extra=vol.ALLOW_EXTRA)
```

**Rationale**:
- Voluptuous is HA's standard validation library
- `vol.Range()` provides clear error messages for out-of-range values
- `cv.positive_int` ensures integer type

---

### R5: Home Assistant Test Patterns

**Question**: How to test Home Assistant custom integrations?

**Decision**: Use pytest with HA test fixtures and mock library components

**Test Structure**:
```
tests/
├── unit/
│   └── test_ha_integration.py      # Entity behavior tests with mocked coordinator
├── integration/
│   └── test_ha_coordinator.py      # Coordinator tests with mocked library
└── acceptance/
    └── test_ha_acceptance.py       # Full acceptance scenario tests
```

**Key Test Patterns**:
1. **Mock the library**: Don't import actual `buderus_wps` in tests
2. **Use HA test utilities**: `async_setup_component`, `async_fire_time_changed`
3. **Test entity states**: Verify `native_value`, `is_on`, etc.
4. **Test coordinator**: Verify data fetching, error handling, backoff

**Example Acceptance Test**:
```python
async def test_temperature_sensors_appear_on_startup(hass, mock_coordinator):
    """Test US1 acceptance scenario 1."""
    # Given integration is configured with correct serial port
    await async_setup_component(hass, DOMAIN, {DOMAIN: {"port": "/dev/ttyACM0"}})

    # When Home Assistant starts (setup completes)
    await hass.async_block_till_done()

    # Then five temperature sensors appear
    for sensor_type in ["outdoor", "supply", "return_temp", "dhw", "brine_in"]:
        state = hass.states.get(f"sensor.heat_pump_{sensor_type}_temperature")
        assert state is not None
```

---

## Summary

All research questions resolved. Key findings:

| Area | Decision | Impact |
|------|----------|--------|
| DHW Extra entity type | NumberEntity with slider | New file: `number.py` |
| Reconnection backoff | Custom implementation in coordinator | Modify: `coordinator.py` |
| Entity naming | `has_entity_name=True` + device name "Heat Pump" | Modify: `entity.py`, `const.py` |
| Scan interval validation | `vol.Range(min=10, max=300)` | Modify: `__init__.py` |
| Testing approach | pytest with mocked library | New test files |

Ready to proceed to Phase 1: data-model.md and contracts.
