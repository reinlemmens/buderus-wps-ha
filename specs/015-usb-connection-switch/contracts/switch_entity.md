# API Contract: USB Connection Switch Entity

**Date**: 2025-12-16
**Phase**: 1 (Design & Contracts)
**Purpose**: Define the public API contract for USB connection control

## Entity Contract: BuderusUSBConnectionSwitch

### Entity Platform Registration

**File**: `custom_components/buderus_wps/switch.py`

**Setup Function**:
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

### Class Definition

```python
class BuderusUSBConnectionSwitch(BuderusEntity, SwitchEntity):
    """Switch to control USB connection for CLI access.

    This switch allows developers to temporarily release the USB serial port
    so the CLI tool can access it for debugging. When toggled OFF, the
    integration disconnects from the USB port. When toggled ON, it reconnects.

    Attributes:
        _attr_name: Display name shown in Home Assistant UI
        _attr_icon: Material Design Icon identifier
    """

    _attr_name = "USB Connection"
    _attr_icon = ICON_USB  # "mdi:usb-port"

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the USB connection switch.

        Args:
            coordinator: The data update coordinator
            entry: The config entry for this integration
        """
        super().__init__(coordinator)
        self._entry = entry
```

### State Property

#### `is_on`

**Signature**:
```python
@property
def is_on(self) -> bool:
    """Return True if USB is connected."""
```

**Return Value**:
- Type: `bool`
- Values:
  - `True`: USB port is connected or attempting to connect (normal operation)
  - `False`: USB port is manually disconnected (released for CLI access)

**Implementation**:
```python
return not self.coordinator._manually_disconnected
```

**Home Assistant Behavior**:
- `True` → Switch shows as ON in UI
- `False` → Switch shows as OFF in UI

**Note**: Unlike sensor entities, switches do not return `None`. The switch always represents user intent (connected vs released), not actual connection status.

### Action Methods

#### `async_turn_on()`

**Purpose**: Reconnect to USB port after CLI debugging session

**Signature**:
```python
async def async_turn_on(self, **kwargs: Any) -> None:
    """Reconnect USB port.

    Clears the manual disconnect flag and attempts to reconnect to the
    USB serial port. If the port is still in use by the CLI tool, this
    will fail with a clear error message.

    Args:
        **kwargs: Additional keyword arguments (unused, required by HA contract)

    Raises:
        HomeAssistantError: If USB port is still in use or connection fails

    Example:
        User toggles switch ON → Integration reconnects → Resumes monitoring
    """
```

**Implementation**:
```python
try:
    await self.coordinator.async_manual_connect()
except (DeviceNotFoundError, DevicePermissionError, DeviceInitializationError) as err:
    _LOGGER.warning("Cannot connect - port may be in use by CLI: %s", err)
    raise HomeAssistantError(f"USB port in use: {err}") from err
```

**Behavior**:
1. Calls `coordinator.async_manual_connect()`
2. On success: Switch updates to ON, coordinator reconnects
3. On failure: Logs warning, raises `HomeAssistantError`, switch stays OFF

**Error Handling**:
- **Port busy** (CLI using port): `HomeAssistantError` with message "USB port in use"
- **Permission denied**: `HomeAssistantError` with message "Permission denied"
- **Device not found**: `HomeAssistantError` with message "USB device not found"

**User Experience**:
- Success: Switch turns ON, sensors resume showing fresh data within 5 seconds
- Failure: Switch stays OFF, error toast shown in UI, user must close CLI and retry

#### `async_turn_off()`

**Purpose**: Release USB port for CLI tool access

**Signature**:
```python
async def async_turn_off(self, **kwargs: Any) -> None:
    """Release USB port for CLI access.

    Sets the manual disconnect flag and disconnects from the USB serial port.
    This allows the CLI tool to open and use the port for debugging.
    The integration will continue showing last-known-good data (stale) while
    disconnected.

    Args:
        **kwargs: Additional keyword arguments (unused, required by HA contract)

    Raises:
        None - Disconnection always succeeds

    Example:
        User toggles switch OFF → USB released → CLI can connect
    """
```

**Implementation**:
```python
await self.coordinator.async_manual_disconnect()
```

**Behavior**:
1. Calls `coordinator.async_manual_disconnect()`
2. Always succeeds (no exceptions)
3. Switch updates to OFF immediately
4. Sensors continue showing stale data

**Error Handling**:
- No errors possible (disconnection is idempotent and safe)

**User Experience**:
- Switch turns OFF within <1 second
- Sensors show stale data with age indicator
- CLI tool can immediately connect to USB port

### Inherited Properties

From `BuderusEntity` base class:

#### `unique_id`

**Signature**:
```python
@property
def unique_id(self) -> str:
    """Return unique ID."""
```

**Return Value**: `f"{self.coordinator.port}_usb_connection"`

**Example**: `/dev/ttyACM0_usb_connection`

#### `device_info`

**Signature**:
```python
@property
def device_info(self) -> DeviceInfo:
    """Return device information."""
```

**Return Value**:
```python
DeviceInfo(
    identifiers={(DOMAIN, self.coordinator.port)},
    name="Buderus WPS Heat Pump",
    manufacturer="Buderus",
    model="WPS",
)
```

## Coordinator Contract: Manual Connection Control

### Method: `async_manual_disconnect()`

**Purpose**: Release USB port for CLI tool usage

**Signature**:
```python
async def async_manual_disconnect(self) -> None:
    """Manually disconnect USB for CLI tool usage.

    Sets manual disconnect flag to prevent automatic reconnection.
    This allows the CLI tool to access the USB port.

    Side Effects:
        - Sets _manually_disconnected = True
        - Cancels _reconnect_task if active
        - Calls _sync_disconnect() if currently connected
        - Sets _connected = False
        - Logs info message

    Raises:
        No exceptions - disconnection always succeeds

    Thread Safety:
        Uses hass.async_add_executor_job for synchronous _sync_disconnect call
    """
```

**Implementation Contract**:
```python
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
```

**Post-Conditions**:
- `_manually_disconnected == True`
- `_connected == False`
- `_reconnect_task == None`
- USB port is closed and available for CLI

**Next Update Cycle Behavior**:
- Returns `_last_known_good_data` (stale)
- Does NOT trigger auto-reconnection
- Sensors remain available with stale data

### Method: `async_manual_connect()`

**Purpose**: Reconnect USB port after CLI tool usage

**Signature**:
```python
async def async_manual_connect(self) -> None:
    """Manually reconnect USB after CLI tool usage.

    Clears manual disconnect flag and initiates connection.

    Side Effects:
        - Sets _manually_disconnected = False
        - Resets _backoff_delay = BACKOFF_INITIAL
        - Calls _sync_connect()
        - Sets _connected = True on success
        - Logs info message

    Raises:
        DeviceNotFoundError: If USB device not available (port in use by CLI)
        DevicePermissionError: If user lacks USB device permissions
        DeviceInitializationError: If device fails to initialize

    Thread Safety:
        Uses hass.async_add_executor_job for synchronous _sync_connect call

    Recovery:
        On exception:
        - _manually_disconnected already cleared to False
        - _connected remains False
        - Exception propagates to caller (switch entity)
        - User must close CLI and retry
    """
```

**Implementation Contract**:
```python
self._manually_disconnected = False
self._backoff_delay = BACKOFF_INITIAL  # Reset backoff on manual connect

# Attempt immediate connection (bypass backoff)
await self.hass.async_add_executor_job(self._sync_connect)
self._connected = True

_LOGGER.info("Manual connect: USB port reconnected")
```

**Post-Conditions** (success):
- `_manually_disconnected == False`
- `_connected == True`
- `_backoff_delay == BACKOFF_INITIAL`
- USB port is open and ready for communication

**Post-Conditions** (failure):
- `_manually_disconnected == False` (cleared before attempt)
- `_connected == False` (not changed)
- Exception raised (propagates to caller)

**Next Update Cycle Behavior** (success):
- Fetches fresh data from device
- Updates `_last_known_good_data`
- Resets `_consecutive_failures = 0`
- Sensors show fresh data

### Modified Method: `_reconnect_with_backoff()`

**Purpose**: Auto-reconnection loop with manual disconnect awareness

**Signature**: (existing method, no signature change)

**Modification**: Add manual disconnect check at loop start

**Implementation Contract**:
```python
async def _reconnect_with_backoff(self) -> None:
    """Attempt reconnection with exponential backoff."""
    while not self._connected:
        # CRITICAL: Check manual disconnect flag first
        if self._manually_disconnected:
            _LOGGER.debug("Skipping auto-reconnect - manual disconnect active")
            self._reconnect_task = None
            return  # Exit loop immediately

        _LOGGER.info(
            "Attempting reconnection to heat pump in %d seconds",
            self._backoff_delay,
        )
        await asyncio.sleep(self._backoff_delay)

        # ... rest of existing reconnection logic
```

**Contract Guarantee**:
- Auto-reconnection does NOT run when `_manually_disconnected == True`
- Loop exits immediately on first check after manual disconnect
- Task sets `_reconnect_task = None` before returning

## Constants Contract

### New Constant: `ICON_USB`

**File**: `custom_components/buderus_wps/const.py`

**Definition**:
```python
ICON_USB = "mdi:usb-port"
```

**Purpose**: Material Design Icon for USB connection switch

**Location**: Add after existing icon constants (after `ICON_ENERGY_BLOCK`)

## Exception Contract

### HomeAssistantError

**Purpose**: User-visible error for port busy scenarios

**Usage**:
```python
from homeassistant.exceptions import HomeAssistantError

raise HomeAssistantError(f"USB port in use: {err}") from err
```

**Display**: Home Assistant shows error message in UI action response

### DeviceNotFoundError, DevicePermissionError, DeviceInitializationError

**Source**: `buderus_wps` library (existing exceptions)

**Handling**: Caught by switch entity, converted to HomeAssistantError

## Home Assistant Integration Contract

### Entity ID

**Format**: `switch.{device_name}_usb_connection`

**Example**: `switch.buderus_wps_usb_connection`

**Stability**: Entity ID persists across HA restarts (determined by unique_id)

### Entity Registry

**Unique ID**: `/dev/ttyACM0_usb_connection`

**Device**: Grouped under "Buderus WPS Heat Pump" device

**Attributes**:
```yaml
friendly_name: USB Connection
icon: mdi:usb-port
supported_features: 0
```

### State Representation

**States**:
- `on`: USB port connected, integration active
- `off`: USB port released, CLI can access

**No "unavailable"**: Switch always has a state (user intent, not actual status)

### Services

**Service**: `switch.turn_on`
- **Target**: `entity_id: switch.buderus_wps_usb_connection`
- **Action**: Reconnect USB port
- **Response**: Success or error message

**Service**: `switch.turn_off`
- **Target**: `entity_id: switch.buderus_wps_usb_connection`
- **Action**: Release USB port
- **Response**: Always success

## Compatibility

**Home Assistant Version**: >=2024.3.0

**Breaking Changes**: None (additive only)

**Backward Compatibility**: Existing energy block switch continues working unchanged

**Forward Compatibility**: Design allows future addition of connection status binary sensor without breaking changes
