# Research: USB Connection Control Switch

**Date**: 2025-12-16
**Phase**: 0 (Research & Design Decisions)
**Purpose**: Document existing patterns and design decisions for USB connection switch implementation

## Research Questions Answered

### 1. Home Assistant Switch Entity Pattern

**Question**: How do existing switches work in this integration?

**Finding**: The existing `BuderusEnergyBlockSwitch` (custom_components/buderus_wps/switch.py:44) provides a clear pattern to follow.

**Decision**: **Follow the BuderusEnergyBlockSwitch pattern exactly**

**Rationale**:
- Proven pattern in this codebase
- Consistent user experience
- Minimal learning curve for maintainers

**Implementation Details**:

```python
class BuderusUSBConnectionSwitch(BuderusEntity, SwitchEntity):
    """Switch to control USB connection for CLI access."""

    _attr_name = "USB Connection"
    _attr_icon = ICON_USB  # "mdi:usb-port"

    @property
    def is_on(self) -> bool:
        """Return True if USB is connected."""
        return not self.coordinator._manually_disconnected

    async def async_turn_on(self) -> None:
        """Reconnect USB port."""
        await self.coordinator.async_manual_connect()

    async def async_turn_off(self) -> None:
        """Release USB port for CLI access."""
        await self.coordinator.async_manual_disconnect()
```

**Key Patterns Observed**:
1. **No exception handling** in entity methods - exceptions bubble to Home Assistant framework
2. **Simple property-based state** - `is_on` returns boolean based on coordinator state
3. **Direct coordinator delegation** - turn_on/off call coordinator methods directly
4. **No refresh needed** - Unlike energy block switch, connection state doesn't require data refresh

**Differences from Energy Block Switch**:
- Energy block calls `async_request_refresh()` after state change
- USB connection switch does NOT need refresh (connection state is immediate)
- Energy block state is derived from data (heating_season_mode + dhw_program_mode)
- USB connection state is direct boolean flag

### 2. Coordinator State Management

**Question**: Where and how to add manual disconnect flag?

**Finding**: Coordinator.py uses `_connected` flag (line 64) and manages reconnection via `_reconnect_task` (line 67).

**Decision**: **Add `_manually_disconnected` flag in coordinator `__init__` after line 72**

**Rationale**:
- Groups with other connection-related state variables
- Naturally follows `_connected`, `_backoff_delay`, `_reconnect_task` pattern
- Accessible from both switch entity and update method

**Implementation Location**:
```python
# In BuderusCoordinator.__init__ (line ~72)
self._manually_disconnected: bool = False  # Track user-initiated disconnect
```

**State Tracking Design**:

| State Variable | Purpose | Updated When |
|----------------|---------|--------------|
| `_connected` | Actual connection status | Connect/disconnect/failure |
| `_manually_disconnected` | User intent | Manual connect/disconnect only |
| `_reconnect_task` | Background reconnection | Failure/cancel/complete |

**Three-State Model**:
1. **Normal**: `_connected=True`, `_manually_disconnected=False`
2. **Manual Disconnect**: `_connected=False`, `_manually_disconnected=True`
3. **Connection Failure**: `_connected=False`, `_manually_disconnected=False`

**Where `_manually_disconnected` is Checked**:
- `_reconnect_with_backoff()` (line 166): Skip reconnection if manual disconnect
- `is_on` property in switch entity: Show OFF state when manual disconnect

### 3. Graceful Degradation Integration

**Question**: Does existing graceful degradation (v1.1.0) handle manual disconnect?

**Finding**: Graceful degradation (coordinator.py:234-311) returns `_last_known_good_data` when `not self._connected`.

**Decision**: **No modifications needed to graceful degradation logic**

**Rationale**:
- Existing logic already returns stale data when `_connected=False`
- Three-strike failure threshold (line 72) provides appropriate behavior
- Manual disconnect sets `_connected=False`, triggering stale data path automatically

**How It Works**:
1. Manual disconnect sets `_connected = False`
2. Next update cycle: Line 237 checks `if not self._connected`
3. Returns `self._last_known_good_data` (line 246)
4. Sensors show stale data instead of "unavailable"

**Integration Point** (line 237):
```python
if not self._connected:
    # NEW: Check if disconnection was manual
    if self._manually_disconnected:
        _LOGGER.debug("Manual disconnect active - returning stale data")
        # Don't trigger reconnection
        if self._last_known_good_data is not None:
            return self._last_known_good_data
        raise UpdateFailed("Manually disconnected from heat pump")

    # Existing graceful degradation logic continues...
```

**Benefit**: Sensors remain responsive during CLI debugging sessions without showing "unavailable" state.

### 4. Error Handling Patterns

**Question**: How to communicate port-busy errors to user?

**Finding**: Home Assistant switch entities let exceptions bubble up (switch.py:75-97), but errors are only visible in logs.

**Decision**: **Use logging for port-busy errors, raise HomeAssistantError for UI feedback**

**Rationale**:
- Home Assistant displays raised exceptions in UI action response
- Logging provides diagnostic details for developers
- Switch returns to OFF state when turn_on fails (HA behavior)

**Implementation**:
```python
async def async_turn_on(self) -> None:
    """Reconnect USB port."""
    try:
        await self.coordinator.async_manual_connect()
    except (DeviceNotFoundError, DevicePermissionError) as err:
        _LOGGER.warning("Cannot connect - port may be in use by CLI: %s", err)
        raise HomeAssistantError(f"USB port in use: {err}") from err
```

**Error Flow**:
1. User toggles switch ON
2. CLI still has port open
3. `async_manual_connect()` raises DeviceNotFoundError
4. Switch catches and logs warning
5. Switch raises HomeAssistantError (shows in UI)
6. Home Assistant keeps switch in OFF state
7. User closes CLI and tries again

**Why Not Silent Failure**:
- User needs immediate feedback that toggle failed
- Prevents confusion about why CLI still works
- Guides user to close CLI before reconnecting

### 5. Testing Strategy

**Question**: How to mock coordinator methods and test auto-reconnection cancellation?

**Finding**: Existing test structure (tests/conftest.py) uses AsyncMock for coordinator methods.

**Decision**: **Extend existing coordinator fixture in conftest.py**

**Rationale**:
- Consistent with existing test patterns
- Minimal changes to test infrastructure
- AsyncMock provides sufficient control for testing

**Implementation** (tests/conftest.py, after line ~216):
```python
# In mock_coordinator fixture
coordinator.async_manual_connect = AsyncMock()
coordinator.async_manual_disconnect = AsyncMock()
coordinator._manually_disconnected = False
```

**Test Patterns**:

**Unit Test Example** (test_usb_connection_switch.py):
```python
async def test_turn_off_calls_manual_disconnect(mock_coordinator, mock_entry):
    """Test switch turn_off calls coordinator manual disconnect."""
    switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

    await switch.async_turn_off()

    mock_coordinator.async_manual_disconnect.assert_called_once()
```

**Integration Test Example** (test_coordinator_manual_disconnect.py):
```python
async def test_manual_disconnect_stops_auto_reconnect():
    """Test manual disconnect cancels pending auto-reconnection."""
    coordinator = BuderusCoordinator(hass, port="/dev/ttyACM0", scan_interval=30)

    # Simulate connection failure (triggers auto-reconnect)
    coordinator._connected = False
    coordinator._reconnect_task = asyncio.create_task(
        coordinator._reconnect_with_backoff()
    )

    # Manual disconnect should cancel reconnection
    await coordinator.async_manual_disconnect()

    assert coordinator._reconnect_task is None or coordinator._reconnect_task.cancelled()
    assert coordinator._manually_disconnected is True
```

**Reconnection Cancellation Test**:
- Create real reconnection task (not mocked)
- Call manual disconnect
- Verify task is cancelled
- Verify `_manually_disconnected` flag is set

## Design Decisions Summary

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Follow BuderusEnergyBlockSwitch pattern | Consistency, proven pattern | Create new pattern (unnecessary complexity) |
| Add `_manually_disconnected` flag in coordinator | Central state management, accessible to all components | Track in switch only (loses state on reload) |
| No modifications to graceful degradation | Existing logic already handles disconnected state | Add special case for manual disconnect (unnecessary) |
| Raise HomeAssistantError for port-busy | User-visible feedback in UI | Silent failure (confusing), only log (invisible) |
| Extend existing test fixtures | Consistency with existing tests | Create new fixtures (duplication) |
| No data refresh after connect/disconnect | Connection state is immediate | Call async_request_refresh (unnecessary delay) |
| Three-state model (normal/manual/failure) | Clear semantics, testable | Two-state model (ambiguous intent) |

## Auto-Reconnection Cancellation Strategy

**Challenge**: When user manually disconnects, auto-reconnection loop must stop immediately.

**Solution**: Check `_manually_disconnected` at start of `_reconnect_with_backoff()` loop.

**Implementation** (coordinator.py line ~166):
```python
async def _reconnect_with_backoff(self) -> None:
    """Attempt reconnection with exponential backoff."""
    while not self._connected:
        # CRITICAL: Check manual disconnect flag first
        if self._manually_disconnected:
            _LOGGER.debug("Skipping auto-reconnect - manual disconnect active")
            self._reconnect_task = None
            return  # Exit loop immediately

        _LOGGER.info("Attempting reconnection in %d seconds", self._backoff_delay)
        await asyncio.sleep(self._backoff_delay)

        # ... rest of reconnection logic
```

**Behavior**:
1. Connection fails → auto-reconnect starts (backoff loop)
2. User toggles switch OFF → `_manually_disconnected = True`
3. Next loop iteration → checks flag and exits immediately
4. User toggles switch ON → `_manually_disconnected = False`, calls `async_manual_connect()`
5. Manual connect succeeds → `_connected = True`, no auto-reconnect needed

**Edge Case**: What if manual disconnect happens mid-sleep?
- Loop continues sleeping (up to BACKOFF_MAX = 120 seconds)
- On wake, checks `_manually_disconnected` and exits
- **Acceptable**: 120-second delay before full stop is fine (user already disconnected)

**Alternative Considered**: Cancel `_reconnect_task` from manual disconnect
- **Rejected**: Task may be in middle of connection attempt (not just sleeping)
- Cancellation during `_sync_connect()` could leave adapter in inconsistent state
- Checking flag is safer and cleaner

## Refresh After State Change

**Question**: Should switch call `async_request_refresh()` after connect/disconnect?

**Finding**: Energy block switch calls refresh (line 85, 97) to sync data with device state.

**Decision**: **No refresh needed for USB connection switch**

**Rationale**:
- Connection state is immediate (not derived from polled data)
- Graceful degradation handles stale data automatically
- Refresh would trigger update cycle that returns stale data anyway
- Unnecessary delay (1-5 seconds) in UI response

**Comparison**:

| Aspect | Energy Block Switch | USB Connection Switch |
|--------|---------------------|----------------------|
| State source | Device data (modes) | Coordinator flag |
| Refresh needed? | Yes (fetch new modes) | No (flag is immediate) |
| Delay | 1-5 seconds | <1 second |
| Data dependency | Requires poll | Independent |

## Coordinator Method Signatures

**New Public Methods** to add to BuderusCoordinator:

```python
async def async_manual_disconnect(self) -> None:
    """Manually disconnect USB for CLI tool usage.

    Sets manual disconnect flag to prevent automatic reconnection.
    This allows the CLI tool to access the USB port.

    Raises:
        No exceptions (disconnection always succeeds)
    """
    self._manually_disconnected = True

    # Cancel any pending auto-reconnection
    if self._reconnect_task is not None:
        self._reconnect_task.cancel()
        self._reconnect_task = None

    # Disconnect if currently connected
    if self._connected:
        await self.hass.async_add_executor_job(self._sync_disconnect)
        self._connected = False

    _LOGGER.info("Manual disconnect: USB port released for CLI access")


async def async_manual_connect(self) -> None:
    """Manually reconnect USB after CLI tool usage.

    Clears manual disconnect flag and initiates connection.

    Raises:
        DeviceNotFoundError: If USB device not available (port in use by CLI)
        DevicePermissionError: If user lacks USB device permissions
        DeviceInitializationError: If device fails to initialize
    """
    self._manually_disconnected = False
    self._backoff_delay = BACKOFF_INITIAL  # Reset backoff on manual connect

    # Attempt immediate connection (bypass backoff)
    await self.hass.async_add_executor_job(self._sync_connect)
    self._connected = True

    _LOGGER.info("Manual connect: USB port reconnected")
```

## Next Steps

**Phase 1 Artifacts** (continue with data-model.md, contracts/, quickstart.md):
1. Document entity and state model
2. Define API contracts for new methods
3. Create quick-start implementation guide

**Implementation Order**:
1. Add ICON_USB to const.py
2. Add coordinator methods (async_manual_disconnect, async_manual_connect)
3. Modify _reconnect_with_backoff to check flag
4. Create switch entity class
5. Add switch to async_setup_entry
6. Write unit tests
7. Write integration tests
8. Manual hardware testing
