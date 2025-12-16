# Quick Start: USB Connection Control Switch Implementation

**Date**: 2025-12-16
**Phase**: 1 (Design & Contracts)
**Purpose**: Step-by-step implementation guide following TDD principles

## Prerequisites

- Feature branch `015-usb-connection-switch` checked out
- Virtual environment activated (`source venv/bin/activate`)
- All tests currently passing
- Read: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md)

## Implementation Steps (TDD Order)

### Step 1: Write Unit Tests FIRST (RED)

**File**: `tests/unit/test_usb_connection_switch.py` (CREATE NEW FILE)

```python
"""Unit tests for USB connection switch."""

import pytest
from unittest.mock import AsyncMock
from homeassistant.exceptions import HomeAssistantError

from custom_components.buderus_wps.switch import BuderusUSBConnectionSwitch
from custom_components.buderus_wps.const import ICON_USB


class TestUSBConnectionSwitch:
    """Test USB connection switch properties."""

    def test_switch_has_correct_name(self, mock_coordinator, mock_entry):
        """Test switch has correct display name."""
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)
        assert switch._attr_name == "USB Connection"

    def test_switch_has_usb_icon(self, mock_coordinator, mock_entry):
        """Test switch has USB port icon."""
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)
        assert switch._attr_icon == ICON_USB

    def test_switch_returns_true_when_connected(self, mock_coordinator, mock_entry):
        """Test switch returns True when not manually disconnected."""
        mock_coordinator._manually_disconnected = False
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        assert switch.is_on is True

    def test_switch_returns_false_when_manually_disconnected(
        self, mock_coordinator, mock_entry
    ):
        """Test switch returns False when manually disconnected."""
        mock_coordinator._manually_disconnected = True
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        assert switch.is_on is False

    def test_switch_entity_key(self, mock_coordinator, mock_entry):
        """Test switch generates correct unique ID."""
        mock_coordinator.port = "/dev/ttyACM0"
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        # Unique ID format from BuderusEntity base class
        assert switch.unique_id == "/dev/ttyACM0_usb_connection"


class TestUSBConnectionSwitchActions:
    """Test USB connection switch turn_on/turn_off actions."""

    async def test_turn_off_calls_manual_disconnect(
        self, mock_coordinator, mock_entry
    ):
        """Test switch turn_off calls coordinator manual disconnect."""
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        await switch.async_turn_off()

        mock_coordinator.async_manual_disconnect.assert_called_once()

    async def test_turn_on_calls_manual_connect(self, mock_coordinator, mock_entry):
        """Test switch turn_on calls coordinator manual connect."""
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        await switch.async_turn_on()

        mock_coordinator.async_manual_connect.assert_called_once()

    async def test_turn_on_handles_port_in_use_error(
        self, mock_coordinator, mock_entry
    ):
        """Test switch turn_on raises HomeAssistantError when port busy."""
        from buderus_wps.exceptions import DeviceNotFoundError

        mock_coordinator.async_manual_connect.side_effect = DeviceNotFoundError(
            "Port in use"
        )
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        with pytest.raises(HomeAssistantError, match="USB port in use"):
            await switch.async_turn_on()


# Add to conftest.py: Extend mock_coordinator fixture
# (See Step 7 for conftest.py modifications)
```

**Expected Result**: Run `pytest tests/unit/test_usb_connection_switch.py` → **ALL TESTS FAIL** (RED)

---

### Step 2: Add Icon Constant (GREEN for icon test)

**File**: `custom_components/buderus_wps/const.py`

**Location**: After existing icon constants (after line ~45 `ICON_ENERGY_BLOCK`)

```python
# Icons
ICON_WATER_HEATER = "mdi:water-boiler"
ICON_SNOWFLAKE = "mdi:snowflake"
ICON_THERMOMETER = "mdi:thermometer"
ICON_ENERGY_BLOCK = "mdi:power-plug-off"
ICON_USB = "mdi:usb-port"  # NEW
```

**Test**: `pytest tests/unit/test_usb_connection_switch.py::TestUSBConnectionSwitch::test_switch_has_usb_icon` → **PASS**

---

### Step 3: Implement Coordinator Methods (GREEN for more tests)

**File**: `custom_components/buderus_wps/coordinator.py`

**3a. Add State Variable** (in `__init__` after line 72):

```python
self._lock = asyncio.Lock()
self._connected = False
# ... existing variables ...
self._stale_data_threshold: int = 3  # Failures before declaring disconnected

# NEW: Manual disconnect tracking
self._manually_disconnected: bool = False
```

**3b. Add Manual Disconnect Method** (after `async_shutdown` at line ~93):

```python
async def async_shutdown(self) -> None:
    """Shut down the connection."""
    # ... existing code ...

async def async_manual_disconnect(self) -> None:
    """Manually disconnect USB for CLI tool usage.

    Sets manual disconnect flag to prevent automatic reconnection.
    This allows the CLI tool to access the USB port.
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

**Test**: `pytest tests/unit/test_usb_connection_switch.py::TestUSBConnectionSwitchActions` → **PASS** (mocked coordinator)

---

### Step 4: Modify Auto-Reconnection Logic (GREEN for state machine)

**File**: `custom_components/buderus_wps/coordinator.py`

**Location**: In `_reconnect_with_backoff` method (line ~166)

**Before**:
```python
async def _reconnect_with_backoff(self) -> None:
    """Attempt reconnection with exponential backoff."""
    while not self._connected:
        _LOGGER.info(
            "Attempting reconnection to heat pump in %d seconds",
            self._backoff_delay,
        )
        # ... rest of method
```

**After**:
```python
async def _reconnect_with_backoff(self) -> None:
    """Attempt reconnection with exponential backoff."""
    while not self._connected:
        # CRITICAL: Don't auto-reconnect if manually disconnected
        if self._manually_disconnected:
            _LOGGER.debug("Skipping auto-reconnect - manual disconnect active")
            self._reconnect_task = None
            return

        _LOGGER.info(
            "Attempting reconnection to heat pump in %d seconds",
            self._backoff_delay,
        )
        # ... rest of method unchanged
```

---

### Step 5: Implement Switch Entity Class (GREEN for entity tests)

**File**: `custom_components/buderus_wps/switch.py`

**Location**: After `BuderusEnergyBlockSwitch` class (after line ~98)

```python
class BuderusEnergyBlockSwitch(BuderusEntity, SwitchEntity):
    # ... existing energy block switch code ...


class BuderusUSBConnectionSwitch(BuderusEntity, SwitchEntity):
    """Switch to control USB connection for CLI access."""

    _attr_name = "USB Connection"
    _attr_icon = ICON_USB

    @property
    def is_on(self) -> bool:
        """Return True if USB is connected."""
        return not self.coordinator._manually_disconnected

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Reconnect USB port."""
        try:
            await self.coordinator.async_manual_connect()
        except Exception as err:
            _LOGGER.warning("Cannot connect - port may be in use by CLI: %s", err)
            raise HomeAssistantError(f"USB port in use: {err}") from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Release USB port for CLI access."""
        await self.coordinator.async_manual_disconnect()
```

**Import Addition** (top of file):
```python
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, ICON_ENERGY_BLOCK, ICON_USB  # Add ICON_USB
```

**Test**: `pytest tests/unit/test_usb_connection_switch.py` → **ALL PASS** (GREEN)

---

### Step 6: Add Switch to Setup Entry (GREEN for integration)

**File**: `custom_components/buderus_wps/switch.py`

**Location**: In `async_setup_entry` function (line ~26)

**Before**:
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    async_add_entities([BuderusEnergyBlockSwitch(coordinator, entry)])
```

**After**:
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    async_add_entities([
        BuderusEnergyBlockSwitch(coordinator, entry),
        BuderusUSBConnectionSwitch(coordinator, entry),  # NEW
    ])
```

---

### Step 7: Update Test Fixtures (GREEN for test infrastructure)

**File**: `tests/conftest.py`

**Location**: In `mock_coordinator` fixture (around line ~216)

**Add** to the coordinator mock setup:
```python
# In mock_coordinator fixture definition
coordinator.async_manual_connect = AsyncMock()
coordinator.async_manual_disconnect = AsyncMock()
coordinator._manually_disconnected = False
```

**Complete fixture example**:
```python
@pytest.fixture
def mock_coordinator():
    """Mock coordinator fixture."""
    coordinator = MagicMock(spec=BuderusCoordinator)
    coordinator.data = BuderusData(
        temperatures={...},
        compressor_running=False,
        energy_blocked=False,
        dhw_extra_duration=0,
        heating_season_mode=1,
        dhw_program_mode=0,
    )
    coordinator.port = "/dev/ttyACM0"
    coordinator._connected = True
    coordinator.async_request_refresh = AsyncMock()

    # NEW: Manual disconnect mocks
    coordinator.async_manual_connect = AsyncMock()
    coordinator.async_manual_disconnect = AsyncMock()
    coordinator._manually_disconnected = False

    return coordinator
```

---

### Step 8: Write Integration Tests (RED → GREEN → REFACTOR)

**File**: `tests/integration/test_coordinator_manual_disconnect.py` (CREATE NEW FILE)

```python
"""Integration tests for coordinator manual disconnect/connect."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from custom_components.buderus_wps.coordinator import BuderusCoordinator
from custom_components.buderus_wps.const import BACKOFF_INITIAL


@pytest.mark.asyncio
class TestCoordinatorManualDisconnect:
    """Test coordinator manual disconnect behavior."""

    async def test_manual_disconnect_stops_auto_reconnect(self, hass):
        """Test manual disconnect cancels pending auto-reconnection."""
        coordinator = BuderusCoordinator(hass, port="/dev/ttyACM0", scan_interval=30)

        # Simulate connection failure (triggers auto-reconnect)
        coordinator._connected = False
        coordinator._reconnect_task = asyncio.create_task(
            coordinator._reconnect_with_backoff()
        )

        # Give reconnection task time to start
        await asyncio.sleep(0.1)

        # Manual disconnect should cancel reconnection
        await coordinator.async_manual_disconnect()

        # Verify task cancelled or completed
        assert (
            coordinator._reconnect_task is None
            or coordinator._reconnect_task.cancelled()
        )
        assert coordinator._manually_disconnected is True

    async def test_manual_connect_restarts_connection(self, hass):
        """Test manual connect restarts connection."""
        coordinator = BuderusCoordinator(hass, port="/dev/ttyACM0", scan_interval=30)

        # Set to manual disconnect state
        coordinator._manually_disconnected = True
        coordinator._connected = False

        # Mock _sync_connect to simulate successful connection
        with patch.object(coordinator, "_sync_connect"):
            await coordinator.async_manual_connect()

        assert coordinator._manually_disconnected is False
        assert coordinator._connected is True
        assert coordinator._backoff_delay == BACKOFF_INITIAL

    async def test_manual_disconnect_preserves_stale_data(self, hass):
        """Test stale data preserved during manual disconnect."""
        coordinator = BuderusCoordinator(hass, port="/dev/ttyACM0", scan_interval=30)

        # Set up last known good data
        coordinator._last_known_good_data = MagicMock()
        coordinator._connected = True

        # Manual disconnect
        await coordinator.async_manual_disconnect()

        # Verify stale data still available
        assert coordinator._last_known_good_data is not None
        assert coordinator._connected is False

    async def test_reconnect_loop_exits_on_manual_disconnect(self, hass):
        """Test _reconnect_with_backoff exits when manual disconnect set."""
        coordinator = BuderusCoordinator(hass, port="/dev/ttyACM0", scan_interval=30)

        coordinator._connected = False
        coordinator._manually_disconnected = False

        # Start reconnection task
        task = asyncio.create_task(coordinator._reconnect_with_backoff())

        # Give it time to enter loop
        await asyncio.sleep(0.1)

        # Set manual disconnect flag
        coordinator._manually_disconnected = True

        # Task should exit within reasonable time
        await asyncio.wait_for(task, timeout=2.0)

        assert task.done()
        assert coordinator._reconnect_task is None


# Run with: pytest tests/integration/test_coordinator_manual_disconnect.py -v
```

**Expected Result**: All integration tests **PASS** (GREEN)

---

### Step 9: Run Quality Gates

**9a. Type Checking**:
```bash
mypy custom_components/buderus_wps/coordinator.py custom_components/buderus_wps/switch.py
```
**Expected**: No type errors

**9b. Linting**:
```bash
ruff check custom_components/buderus_wps/coordinator.py custom_components/buderus_wps/switch.py
```
**Expected**: No linting errors

**9c. Code Formatting**:
```bash
black custom_components/buderus_wps/coordinator.py custom_components/buderus_wps/switch.py tests/
```
**Expected**: All files formatted

**9d. Test Coverage**:
```bash
pytest tests/unit/test_usb_connection_switch.py tests/integration/test_coordinator_manual_disconnect.py --cov=custom_components.buderus_wps.switch --cov=custom_components.buderus_wps.coordinator --cov-report=term-missing
```
**Expected**: 100% coverage for new code

---

### Step 10: Run Full Test Suite

```bash
pytest --ignore=tests/hil/
```

**Expected**: All existing tests still pass + new tests pass

---

### Step 11: Manual Acceptance Testing (Hardware)

**Prerequisites**:
- Physical Buderus WPS heat pump connected via USB
- Home Assistant instance with integration installed
- CLI tool available

**Test Scenarios**:

**Test 1: Manual Disconnect Flow**
1. Verify integration connected (sensors showing data)
2. Navigate to USB Connection switch in HA UI
3. Toggle switch OFF
4. Verify sensors show stale data (not unavailable)
5. Open terminal, run CLI read command
6. Verify CLI successfully connects to USB port
7. Exit CLI

**Expected**: ✅ Pass all steps

**Test 2: Manual Reconnect Flow**
1. With switch OFF and CLI closed
2. Toggle switch ON in HA UI
3. Wait 5 seconds
4. Verify sensors show fresh data
5. Verify switch shows ON state

**Expected**: ✅ Pass all steps

**Test 3: Port Busy Error**
1. Toggle switch OFF
2. Open CLI and keep connection active
3. Toggle switch ON (while CLI still open)
4. Verify error message in HA logs
5. Verify switch returns to OFF state
6. Close CLI, toggle ON again
7. Verify reconnection succeeds

**Expected**: ✅ Pass all steps

**Test 4: Auto-Reconnection Behavior**
1. With switch ON, unplug USB cable
2. Verify auto-reconnection starts (check logs)
3. Toggle switch OFF (while auto-reconnecting)
4. Verify auto-reconnection stops
5. Plug USB cable back in
6. Toggle switch ON
7. Verify immediate reconnection (no backoff delay)

**Expected**: ✅ Pass all steps

**Test 5: Rapid Toggling**
1. Toggle switch OFF and ON rapidly 10 times
2. Verify no crashes or state corruption
3. Verify final state is consistent

**Expected**: ✅ Pass all steps

---

## Verification Checklist

Before marking implementation complete:

- [ ] All unit tests pass (test_usb_connection_switch.py)
- [ ] All integration tests pass (test_coordinator_manual_disconnect.py)
- [ ] All existing tests still pass
- [ ] Type checking passes (`mypy`)
- [ ] Linting passes (`ruff`)
- [ ] Code formatted (`black`)
- [ ] 100% test coverage for new code
- [ ] ICON_USB constant added
- [ ] Coordinator methods implemented (async_manual_disconnect, async_manual_connect)
- [ ] Auto-reconnection logic modified (manual disconnect check)
- [ ] Switch entity class implemented
- [ ] Switch added to async_setup_entry
- [ ] Test fixtures updated (conftest.py)
- [ ] Manual acceptance tests completed
- [ ] All 14 functional requirements verified (FR-001 through FR-014)
- [ ] All 11 acceptance scenarios verified (3 user stories)
- [ ] All 10 success criteria met (SC-001 through SC-010)

---

## Troubleshooting

### Issue: Tests fail with "ModuleNotFoundError: No module named 'custom_components'"

**Solution**: Run tests from repository root with pytest discovering custom_components:
```bash
PYTHONPATH=/mnt/supervisor/addons/local/buderus-wps-ha:$PYTHONPATH pytest
```

### Issue: Type checking fails with "Module 'buderus_wps' has no attribute 'exceptions'"

**Solution**: Ensure buderus_wps library is installed in editable mode:
```bash
pip install -e .
```

### Issue: Manual test fails - CLI cannot connect even with switch OFF

**Solution**:
1. Check if coordinator actually disconnected: `_LOGGER.info("Manual disconnect...")`
2. Verify USB port released: `lsof /dev/ttyACM0` (should show nothing)
3. Wait 1-2 seconds after toggle before CLI connect attempt
4. Check file permissions: `ls -l /dev/ttyACM0`

### Issue: Switch stays OFF after turn_on attempt

**Solution**: Check Home Assistant logs for exception details:
```bash
tail -f /config/home-assistant.log | grep buderus_wps
```
Common causes:
- CLI still has port open
- USB device unplugged
- Permission denied

---

## Next Steps After Implementation

1. **Generate tasks.md**: Run `/speckit.tasks` command
2. **Code review**: Review all changes before committing
3. **Git commit**: Create commit with all changes
4. **Manual testing**: Complete all acceptance test scenarios
5. **Documentation**: Update CLAUDE.md if needed
6. **Pull request**: Create PR for review

---

## Time Estimates

| Step | Estimated Time |
|------|----------------|
| Write unit tests | 30 minutes |
| Add icon constant | 2 minutes |
| Implement coordinator methods | 20 minutes |
| Modify auto-reconnection | 10 minutes |
| Implement switch entity | 15 minutes |
| Add switch to setup | 5 minutes |
| Update test fixtures | 10 minutes |
| Write integration tests | 45 minutes |
| Run quality gates | 10 minutes |
| Manual acceptance testing | 30 minutes |
| **Total** | **~3 hours** |

---

## References

- [spec.md](spec.md): Feature requirements and success criteria
- [plan.md](plan.md): Implementation plan and architecture
- [research.md](research.md): Design decisions and patterns
- [data-model.md](data-model.md): Entity and state model
- [contracts/switch_entity.md](contracts/switch_entity.md): API contracts
- Constitution: `.specify/memory/constitution.md` (v1.1.0)
