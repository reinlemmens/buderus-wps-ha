# Implementation Plan: Indefinite Last-Known-Good Data Caching

**Branch**: `016-indefinite-caching-implementation` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)

## Summary

Implement indefinite retention of last-known-good sensor values in the Home Assistant integration coordinator, eliminating "Unknown" states for sensors when CAN bus communication is temporarily unavailable.

**Key Deliverables**:
- Remove 3-failure threshold from coordinator
- Always return cached data when available
- Add staleness metadata to all entities
- Update tests to verify new behavior

## Technical Context

**Language/Version**: Python 3.9+ (Home Assistant compatibility)
**Primary Files to Modify**:
- `custom_components/buderus_wps/coordinator.py` (remove threshold, update error handling, add helpers)
- `custom_components/buderus_wps/entity.py` (add staleness attributes)
- `tests/integration/test_ha_reconnection.py` (verify indefinite caching)
- `tests/acceptance/test_ha_us1_temperature.py` (update scenario 3)

**No Changes Required**:
- `sensor.py`, `binary_sensor.py`, `switch.py`, `number.py` (entities already handle None correctly)

## Implementation Strategy

### Phase 1: Coordinator Changes

**File**: `custom_components/buderus_wps/coordinator.py`

1. **Remove threshold** (line 72):
   ```python
   # REMOVE: self._stale_data_threshold: int = 3
   ```

2. **Update _async_update_data** (lines 295-374):
   - Remove all threshold checks (lines 296, 340, 361)
   - Always return `self._last_known_good_data` if not None
   - Simplify error handling: log warning, return cache, continue reconnection

3. **Add helper methods** (after line 513):
   ```python
   def get_data_age_seconds(self) -> int | None:
       """Get age of current data in seconds."""
       if self._last_successful_update is None:
           return None
       return int(time.time() - self._last_successful_update)

   def is_data_stale(self) -> bool:
       """Check if current data is stale (connection issues)."""
       return self._consecutive_failures > 0
   ```

### Phase 2: Entity Staleness Attributes

**File**: `custom_components/buderus_wps/entity.py`

Add to `BuderusEntity` class:
```python
@property
def extra_state_attributes(self) -> dict[str, Any]:
    """Return entity state attributes including staleness indicators."""
    attrs = {}

    age = self.coordinator.get_data_age_seconds()
    if age is not None:
        attrs["last_update_age_seconds"] = age
        attrs["data_is_stale"] = self.coordinator.is_data_stale()

    if self.coordinator._last_successful_update:
        from datetime import datetime
        attrs["last_successful_update"] = datetime.fromtimestamp(
            self.coordinator._last_successful_update
        ).isoformat()

    return attrs
```

### Phase 3: Test Updates

**File**: `tests/integration/test_ha_reconnection.py`

Add new test:
```python
async def test_indefinite_caching_after_many_failures():
    """Coordinator returns cached data even after 10+ consecutive failures."""
    # Setup: Get initial successful read
    initial_data = coordinator.data

    # Simulate 10 consecutive failures
    for _ in range(10):
        # Mock CAN timeout error
        await coordinator.async_refresh()

    # Verify: Still returns cached data
    assert coordinator.data is not None
    assert coordinator.data == initial_data
    assert coordinator.is_data_stale() is True
```

**File**: `tests/acceptance/test_ha_us1_temperature.py`

Update test for acceptance scenario 3:
```python
async def test_connection_lost_retains_stale_data():
    """When connection lost, sensors retain last values with staleness indicators."""
    # Get initial reading
    initial_temp = sensor.native_value

    # Simulate 5+ failures
    for _ in range(5):
        # Mock CAN timeout
        await coordinator.async_refresh()

    # Assert: Sensor shows stale data with metadata
    assert sensor.native_value == initial_temp  # Not "Unknown"
    assert sensor.available is True  # Still available
    assert sensor.extra_state_attributes["data_is_stale"] is True
    assert sensor.extra_state_attributes["last_update_age_seconds"] > 0
```

## Files to Modify

**Implementation** (2 files):
1. `custom_components/buderus_wps/coordinator.py` (~3 changes: remove threshold, update error handling, add helpers)
2. `custom_components/buderus_wps/entity.py` (~1 change: add extra_state_attributes property)

**Tests** (2 files):
1. `tests/integration/test_ha_reconnection.py` (add indefinite caching test)
2. `tests/acceptance/test_ha_us1_temperature.py` (update scenario 3 test)

## Risk Assessment

**Risk Level**: LOW

- Changes are localized to coordinator and entity base class
- Existing entities automatically inherit staleness attributes
- All sensor entities already handle None correctly
- Cache is single BuderusData object (~1KB, negligible memory)

## Success Validation

- [ ] Coordinator no longer has `_stale_data_threshold` attribute
- [ ] Coordinator always returns cached data when available (never None after first read)
- [ ] All entities show staleness attributes (age, timestamp, is_stale flag)
- [ ] New integration test passes (10+ failures scenario)
- [ ] Updated acceptance test passes (scenario 3)
- [ ] All existing tests continue to pass
- [ ] Type checking passes (`mypy`)
- [ ] Linting passes (`ruff`)
