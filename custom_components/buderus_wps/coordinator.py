"""DataUpdateCoordinator for Buderus WPS Heat Pump."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BACKOFF_INITIAL,
    BACKOFF_MAX,
    DOMAIN,
    SENSOR_BRINE_IN,
    SENSOR_BRINE_OUT,
    SENSOR_DHW,
    SENSOR_OUTDOOR,
    SENSOR_RETURN,
    SENSOR_ROOM_C1,
    SENSOR_ROOM_C2,
    SENSOR_ROOM_C3,
    SENSOR_ROOM_C4,
    SENSOR_SETPOINT_C1,
    SENSOR_SETPOINT_C2,
    SENSOR_SETPOINT_C3,
    SENSOR_SETPOINT_C4,
    SENSOR_SUPPLY,
)

# Timeout for acquiring the coordinator lock
LOCK_ACQUIRE_TIMEOUT = 5.0
# Timeout for sync executor jobs (prevent indefinite hangs)
EXECUTOR_JOB_TIMEOUT = 10.0

_LOGGER = logging.getLogger(__name__)


@dataclass
class BuderusData:
    """Data class for heat pump readings."""

    temperatures: dict[str, float | None]
    compressor_running: bool
    compressor_blocked: bool | None
    energy_blocked: bool
    dhw_active: bool
    g1_active: bool
    dhw_extra_duration: int  # Hours remaining (0-48), 0 = not active
    heating_season_mode: int | None  # 0=Winter, 1=Auto, 2=Off
    dhw_program_mode: int | None  # 0=Auto, 1=On, 2=Off
    heating_curve_offset: float | None  # Parallel offset in °C (-10.0 to +10.0)
    dhw_stop_temp: float | None  # DHW stop charging temperature (50.0-65.0°C)
    dhw_setpoint: float | None  # DHW setpoint temperature (40.0-70.0°C)
    compressor_state: int | None = None  # Raw compressor state (debug)
    compressor_frequency: int | None = None  # Hz (debug)
    parameter_results: dict[str, dict[str, Any]] = field(default_factory=dict)


class BuderusCoordinator(DataUpdateCoordinator[BuderusData]):
    """Coordinator for fetching data from Buderus WPS heat pump."""

    def __init__(
        self,
        hass: HomeAssistant,
        port: str,
        scan_interval: int,
        parameter_allowlist: list[str] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.port = port
        self._adapter: Any = None
        self._client: Any = None
        self._registry: Any = None
        self._monitor: Any = None
        self._api: Any = None
        self.energy_blocking: Any = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._parameter_allowlist = [
            item for item in (parameter_allowlist or []) if str(item).strip()
        ]
        # Exponential backoff for reconnection
        self._backoff_delay = BACKOFF_INITIAL
        self._reconnect_task: asyncio.Task[None] | None = None
        # Last-known-good data caching for graceful degradation
        # Cache is retained indefinitely - stale data preferred over "Unknown"
        self._last_known_good_data: BuderusData | None = None
        self._last_successful_update: float | None = None  # Timestamp
        self._consecutive_failures: int = 0
        # Removed _stale_data_threshold - cache never expires per FR-011
        self._manually_disconnected: bool = (
            False  # Track intentional disconnect for CLI access
        )
        # DHW boost fallback: used when XDHW_TIME writes don't take on the device.
        self._dhw_boost_end_time: float | None = None
        self._dhw_boost_original_program_mode: int | None = None
        self._dhw_boost_task: asyncio.Task[None] | None = None

    @property
    def parameter_allowlist(self) -> list[str]:
        """Return configured parameter allowlist entries."""
        return list(self._parameter_allowlist)

    async def async_setup(self) -> bool:
        """Set up the connection to the heat pump."""
        try:
            await self.hass.async_add_executor_job(self._sync_connect)
            self._connected = True
            return True
        except Exception as err:
            _LOGGER.error("Failed to connect to heat pump: %s", err)
            return False

    async def async_shutdown(self) -> None:
        """Shut down the connection."""
        # Cancel any pending reconnection
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        if self._dhw_boost_task is not None:
            self._dhw_boost_task.cancel()
            self._dhw_boost_task = None
        if self._connected:
            await self.hass.async_add_executor_job(self._sync_disconnect)
            self._connected = False

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

        # Trigger data refresh to update entities immediately
        await self.async_request_refresh()

    async def _handle_connection_failure(self) -> None:
        """Schedule reconnection with exponential backoff."""
        if self._reconnect_task is not None:
            return  # Already reconnecting

        self._reconnect_task = self.hass.async_create_background_task(
            self._reconnect_with_backoff(),
            "buderus_wps_reconnect",
        )

    def _classify_error(self, error: Exception) -> str:
        """Classify error as persistent, transient, or partial.

        Args:
            error: Exception that occurred during data fetch

        Returns:
            "persistent": Requires reconnection (device lost, multiple failures)
            "transient": Temporary issue, can use stale data
            "partial": Some data available, some failed (unused currently)
        """
        # Import exception types from buderus_wps to avoid module-level conflicts
        # with Python's built-in ConnectionError and TimeoutError
        try:
            from .buderus_wps.exceptions import (
                DeviceCommunicationError,
                DeviceDisconnectedError,
                DeviceNotFoundError,
                DevicePermissionError,
                ReadTimeoutError,
            )
            from .buderus_wps.exceptions import (
                TimeoutError as BuderusTimeoutError,
            )
        except ImportError:
            # If exceptions module not available, use conservative classification
            _LOGGER.debug(
                "Could not import buderus_wps.exceptions, using conservative error classification"
            )
            # Check consecutive failures - trigger reconnection after 3 failures
            if self._consecutive_failures >= 3:
                return "persistent"
            return "transient"

        # Persistent connection errors - device is gone or inaccessible
        if isinstance(
            error, (DeviceNotFoundError, DeviceDisconnectedError, DevicePermissionError)
        ):
            return "persistent"

        # Check if we've had multiple consecutive failures - likely persistent issue
        # Trigger reconnection after 3 failures (stale data still returned)
        if self._consecutive_failures >= 3:
            return "persistent"

        # Timeout errors are usually transient (CAN bus congestion, temporary USB glitch)
        if isinstance(error, (BuderusTimeoutError, ReadTimeoutError)):
            return "transient"

        # Communication errors might be transient (USB glitch) or persistent (disconnected)
        # Use consecutive failure count to decide
        if isinstance(error, DeviceCommunicationError):
            if self._consecutive_failures >= 2:
                return "persistent"
            return "transient"

        # OSError/IOError often indicate hardware issues
        if isinstance(error, (OSError, IOError)):
            # Serial port errors might be transient (USB glitch) or persistent
            # Use consecutive failure count to decide
            if self._consecutive_failures >= 2:
                return "persistent"
            return "transient"

        # Default: treat as transient on first occurrence, persistent after 3 failures
        # (triggers reconnection while still returning stale data)
        if self._consecutive_failures < 3:
            return "transient"
        return "persistent"

    async def _reconnect_with_backoff(self) -> None:
        """Attempt reconnection with exponential backoff."""
        while not self._connected:
            # CRITICAL: Don't auto-reconnect if manually disconnected
            if self._manually_disconnected:
                _LOGGER.debug("Skipping auto-reconnect - manual disconnect active")
                self._reconnect_task = None
                return  # Exit loop immediately

            _LOGGER.info(
                "Attempting reconnection to heat pump in %d seconds",
                self._backoff_delay,
            )
            await asyncio.sleep(self._backoff_delay)

            try:
                await self.hass.async_add_executor_job(self._sync_connect)
                self._connected = True
                self._backoff_delay = BACKOFF_INITIAL  # Reset on success
                _LOGGER.info("Successfully reconnected to heat pump")
                # Trigger a data refresh
                await self.async_request_refresh()
            except Exception as err:
                _LOGGER.warning("Reconnection failed: %s", err)
                # Double the delay, but cap at max
                self._backoff_delay = min(self._backoff_delay * 2, BACKOFF_MAX)

        self._reconnect_task = None

    def _sync_connect(self) -> None:
        """Synchronous connection setup (runs in executor)."""
        # Import bundled library using relative imports
        from .buderus_wps import (
            BroadcastMonitor,
            HeatPump,
            HeatPumpClient,
            USBtinAdapter,
            EnergyBlockingControl,
        )
        from .buderus_wps.element_discovery import ElementDiscovery
        from .buderus_wps.menu_api import MenuAPI

        _LOGGER.debug("Connecting to heat pump at %s", self.port)

        self._adapter = USBtinAdapter(self.port)
        self._adapter.connect()

        # Create registry with static defaults first
        self._registry = HeatPump()

        # Run element discovery to get actual device indices
        # This is critical because firmware versions may have different idx values
        # for the same parameter names (e.g., XDHW_TIME at idx=2475 in static
        # defaults but idx=2480 on actual device)
        #
        # IMPORTANT: Cache is stored in /config/ which persists across HA restarts.
        # On fresh install, discovery MUST succeed - we fail-fast rather than
        # silently use static defaults which produce wrong readings.
        from .buderus_wps.exceptions import DiscoveryRequiredError

        cache_path = "/config/buderus_wps_elements.json"
        _LOGGER.info("Element discovery cache path: %s", cache_path)

        try:
            discovery = ElementDiscovery(self._adapter)
            # Use cache to speed up subsequent connections
            # Cache expires after 24 hours or if previous discovery was incomplete
            # On discovery failure:
            #   - With valid cache: falls back to cached data
            #   - Without cache (fresh install): raises DiscoveryRequiredError
            discovered = discovery.discover_with_cache(
                cache_path=cache_path,
                refresh=False,  # Use cache if available
                max_cache_age=86400.0,  # 24 hours - refresh stale cache
                timeout=30.0,
                max_retries=3,  # Retry incomplete discovery up to 3 times
                min_completion_ratio=0.95,  # Require 95% of reported elements
            )
            if discovered:
                updated = self._registry.update_from_discovery(discovered)
                _LOGGER.info(
                    "Element discovery: %d elements, %d indices updated",
                    len(discovered),
                    updated,
                )
                # Log key parameters for debugging
                for name in [
                    "XDHW_STOP_TEMP",
                    "XDHW_TIME",
                    "GT3_TEMP",
                    "GT8_TEMP",
                    "GT9_TEMP",
                    "GT10_TEMP",
                    "GT11_TEMP",
                ]:
                    param = self._registry.get_parameter(name)
                    if param:
                        _LOGGER.info(
                            "%s: idx=%d, CAN ID=0x%08X",
                            name,
                            param.idx,
                            0x04003FE0 | (param.idx << 14),
                        )
        except DiscoveryRequiredError as err:
            # Fail-fast on fresh install - cannot proceed without discovery
            _LOGGER.error(
                "Discovery required but failed: %s. "
                "Ensure CAN adapter is connected and heat pump is powered on.",
                err.reason,
            )
            raise
        except Exception as err:
            _LOGGER.warning(
                "Element discovery error (non-fatal if cache exists): %s",
                err,
            )

        self._client = HeatPumpClient(self._adapter, self._registry)
        self._monitor = BroadcastMonitor(self._adapter)
        self._api = MenuAPI(self._client)
        self.energy_blocking = EnergyBlockingControl(self._client)

        _LOGGER.info("Successfully connected to heat pump at %s", self.port)

    def _sync_disconnect(self) -> None:
        """Synchronous disconnect (runs in executor)."""
        if self._adapter:
            try:
                self._adapter.disconnect()
            except Exception as err:
                _LOGGER.warning("Error disconnecting from heat pump: %s", err)
            self._adapter = None
            self._client = None
            self._monitor = None
            self._api = None
            self.energy_blocking = None

    def _coerce_parameter_key(self, key: str | int) -> str | int:
        if isinstance(key, int):
            return key
        value = str(key).strip()
        if value.isdigit():
            return int(value)
        return value

    def _normalize_parameter_result(self, result: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(result)
        raw = normalized.get("raw")
        if isinstance(raw, (bytes, bytearray)):
            normalized["raw"] = raw.hex()
        return normalized

    async def async_read_parameter(
        self,
        name_or_idx: str | int,
        *,
        expected_dlc: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Read any parameter via RTR using the active client."""
        async with self._lock:
            if not self._connected or self._client is None:
                raise HomeAssistantError("Not connected to heat pump")
            return await self.hass.async_add_executor_job(
                self._sync_read_parameter, name_or_idx, expected_dlc, timeout
            )

    def _sync_read_parameter(
        self,
        name_or_idx: str | int,
        expected_dlc: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Synchronous parameter read helper."""
        if self._client is None:
            raise HomeAssistantError("Heat pump client not available")
        coerced = self._coerce_parameter_key(name_or_idx)
        if expected_dlc is not None:
            result = self._client.read_parameter_with_validation(
                coerced, expected_dlc=expected_dlc, timeout=timeout
            )
        else:
            result = self._client.read_parameter(coerced, timeout=timeout)
        return self._normalize_parameter_result(result)

    async def async_list_parameters(
        self,
        *,
        name_contains: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return registry parameters for discovery and allowlist usage."""
        return await self.hass.async_add_executor_job(
            self._sync_list_parameters, name_contains, limit
        )

    def _sync_list_parameters(
        self, name_contains: str | None, limit: int | None
    ) -> list[dict[str, Any]]:
        if self._registry is None:
            raise HomeAssistantError("Parameter registry not available")

        needle = name_contains.upper() if name_contains else None
        results: list[dict[str, Any]] = []
        for param in self._registry.parameters:
            if needle and needle not in param.text.upper():
                continue
            results.append(
                {
                    "name": param.text,
                    "idx": param.idx,
                    "extid": param.extid,
                    "format": param.format,
                    "min": param.min,
                    "max": param.max,
                    "read": param.read,
                }
            )
            if limit is not None and len(results) >= limit:
                break
        return results

    async def _async_update_data(self) -> BuderusData:
        """Fetch data from the heat pump with graceful degradation.

        Per FR-011: Always return cached data when available (indefinite retention).
        Only raise UpdateFailed if no cache exists yet.
        """
        async with self._lock:
            if not self._connected:
                # Always return cached data if available (no threshold check)
                if self._last_known_good_data is not None:
                    _LOGGER.warning(
                        "Not connected, returning stale data (age: %.1fs, failures: %d)",
                        (
                            time.time() - self._last_successful_update
                            if self._last_successful_update
                            else 0
                        ),
                        self._consecutive_failures,
                    )
                    return self._last_known_good_data

                # No cache exists yet, trigger reconnection and fail
                await self._handle_connection_failure()
                raise UpdateFailed("Not connected to heat pump (no cached data)")

            try:
                # Attempt to fetch fresh data
                fresh_data: BuderusData = await self.hass.async_add_executor_job(
                    self._sync_fetch_data
                )

                # Success! Update cache and reset failure counter
                self._last_known_good_data = fresh_data
                self._last_successful_update = time.time()
                self._consecutive_failures = 0

                return fresh_data

            except Exception as err:
                self._consecutive_failures += 1

                # Classify the error
                error_type = self._classify_error(err)

                if error_type == "persistent":
                    # Persistent connection loss - mark disconnected and reconnect
                    _LOGGER.error(
                        "Persistent connection error (failure %d): %s",
                        self._consecutive_failures,
                        err,
                    )
                    self._connected = False
                    await self._handle_connection_failure()

                    # Always return stale data if available (no threshold)
                    if self._last_known_good_data is not None:
                        _LOGGER.warning(
                            "Returning stale data during reconnection (age: %.1fs)",
                            (
                                time.time() - self._last_successful_update
                                if self._last_successful_update
                                else 0
                            ),
                        )
                        return self._last_known_good_data
                    raise UpdateFailed(f"Persistent error: {err}") from err

                elif error_type == "transient":
                    # Transient error - always return stale data if available
                    _LOGGER.warning(
                        "Transient error during update (failure %d): %s",
                        self._consecutive_failures,
                        err,
                    )

                    if self._last_known_good_data is not None:
                        _LOGGER.info(
                            "Returning stale data (age: %.1fs)",
                            (
                                time.time() - self._last_successful_update
                                if self._last_successful_update
                                else 0
                            ),
                        )
                        return self._last_known_good_data

                    # No stale data available - this is a genuine failure
                    raise UpdateFailed(
                        f"Transient error with no cached data: {err}"
                    ) from err

                else:  # "partial"
                    # Partial failure - already handled in _sync_fetch_data
                    # Always return cached data if available
                    _LOGGER.warning(
                        "Unexpected partial failure classification: %s", err
                    )
                    if self._last_known_good_data is not None:
                        return self._last_known_good_data
                    raise UpdateFailed(f"Error fetching data: {err}") from err

    def _sync_fetch_data(self) -> BuderusData:
        """Synchronous data fetch (runs in executor) with partial success handling."""
        from .buderus_wps.config import get_default_sensor_map

        # Start with empty/None data
        temperatures: dict[str, float | None] = {
            SENSOR_OUTDOOR: None,
            SENSOR_SUPPLY: None,
            SENSOR_RETURN: None,
            SENSOR_DHW: None,
            SENSOR_BRINE_IN: None,
            SENSOR_BRINE_OUT: None,
            SENSOR_ROOM_C1: None,
            SENSOR_ROOM_C2: None,
            SENSOR_ROOM_C3: None,
            SENSOR_ROOM_C4: None,
            SENSOR_SETPOINT_C1: None,
            SENSOR_SETPOINT_C2: None,
            SENSOR_SETPOINT_C3: None,
            SENSOR_SETPOINT_C4: None,
        }

        # Pre-fill with last known good data to prevent "Unknown" flapping
        # if a specific sensor broadcast is missed in this cycle
        if self._last_known_good_data is not None:
            for key, value in self._last_known_good_data.temperatures.items():
                if value is not None:
                    temperatures[key] = value

        # Try to collect broadcast data
        broadcast_success = False
        try:
            sensor_map = get_default_sensor_map()
            cache = self._monitor.collect(duration=5.0)

            # DEBUG: Log ALL temperature readings to help diagnose DHW temp issue
            _LOGGER.debug("=== ALL BROADCAST TEMPERATURES (20-70°C range) ===")
            for reading in cache.readings.values():
                if reading.is_temperature and 20.0 <= reading.temperature <= 70.0:
                    _LOGGER.debug(
                        f"  Base=0x{reading.base:04X}, Idx={reading.idx:3d}, "
                        f"Temp={reading.temperature:5.1f}°C"
                    )

            # Extract temperatures from cache
            for (base, idx), sensor_name in sensor_map.items():
                reading = cache.get_by_idx_and_base(idx, base)
                if reading is not None and sensor_name in temperatures:
                    temperatures[sensor_name] = reading.temperature
                    _LOGGER.debug(
                        f"Mapped sensor '{sensor_name}': {reading.temperature:.1f}°C "
                        f"from base=0x{base:04X}, idx={idx}"
                    )

            broadcast_success = True
        except Exception as err:
            _LOGGER.warning(
                "Broadcast collection failed, using stale temperature data: %s", err
            )
            # If we have stale data, use those temperatures
            if self._last_known_good_data is not None:
                temperatures = self._last_known_good_data.temperatures.copy()

        parameter_results: dict[str, dict[str, Any]] = {}
        if self._parameter_allowlist:
            for key in self._parameter_allowlist:
                name_or_idx = self._coerce_parameter_key(key)
                try:
                    result = self._sync_read_parameter(name_or_idx)
                    parameter_results[key] = result
                except Exception as err:
                    fallback = None
                    if self._last_known_good_data is not None:
                        fallback = self._last_known_good_data.parameter_results.get(key)
                    if fallback is not None:
                        parameter_results[key] = fallback
                    else:
                        parameter_results[key] = {
                            "name": str(key),
                            "decoded": None,
                            "error": str(err),
                        }

        def _read_rtr_temperature(
            name: str,
            sensor_key: str,
            label: str,
            *,
            error_level: int = logging.DEBUG,
            dead_level: int = logging.DEBUG,
            invalid_dlc_level: int = logging.DEBUG,
        ) -> None:
            try:
                result = self._client.read_parameter_with_validation(
                    name, expected_dlc=2
                )
                error = result.get("error")
                decoded = result.get("decoded")

                if error == "invalid_dlc":
                    _LOGGER.log(
                        invalid_dlc_level,
                        "%s not available on this heat pump model (wrong data length)",
                        name,
                    )
                    return

                if decoded is None:
                    _LOGGER.log(
                        dead_level,
                        "%s sensor is DEAD (disconnected or faulty)",
                        name,
                    )
                    return

                try:
                    temperature = float(decoded)
                except (TypeError, ValueError):
                    _LOGGER.log(
                        error_level,
                        "%s returned non-numeric value: %s",
                        name,
                        decoded,
                    )
                    return

                temperatures[sensor_key] = temperature
                _LOGGER.debug("%s (%s) via RTR: %.1f°C", name, label, temperature)
            except Exception as err:
                param = self._registry.get_parameter(name)
                idx = param.idx if param else "unknown"
                _LOGGER.log(
                    error_level,
                    "RTR FAILED for %s (idx=%s): %s",
                    name,
                    idx,
                    err,
                )
                # Keep any broadcast or stale value that may exist

        # Get GT3_TEMP (DHW temperature) via RTR (best-effort)
        # PROTOCOL: GT3_TEMP must be read via RTR, NOT broadcast.
        # The broadcast mapping in config.py is incorrect - broadcasts don't contain GT3.
        # Element discovery finds the correct idx (682 on tested heat pump, varies by model).
        # The raw sensor value is returned; display may show +4K adjustment (GT3_KORRIGERING).
        # Verified 2026-01-02: idx=682 returns correct DHW temperature via RTR.
        _read_rtr_temperature(
            "GT3_TEMP",
            SENSOR_DHW,
            "DHW",
            error_level=logging.WARNING,
            dead_level=logging.WARNING,
            invalid_dlc_level=logging.WARNING,
        )

        # Get GT8_TEMP (Heat transfer fluid OUT / supply) via RTR (best-effort)
        # Broadcast values can be offset on some models; RTR provides the menu value.
        _read_rtr_temperature("GT8_TEMP", SENSOR_SUPPLY, "Supply")

        # Get GT9_TEMP (Heat transfer fluid IN / return) via RTR (best-effort)
        # Broadcast values can be offset on some models; RTR provides the menu value.
        _read_rtr_temperature("GT9_TEMP", SENSOR_RETURN, "Return")

        # Get GT10_TEMP (Brine/collector inlet) via RTR (best-effort)
        # PROTOCOL: GT10_TEMP is the collector circuit inlet temperature (brine in)
        # Uses discovered idx (varies by firmware, ~638 in FHEM reference)
        # NOTE: Not all heat pump models have this sensor
        _read_rtr_temperature(
            "GT10_TEMP",
            SENSOR_BRINE_IN,
            "Brine In",
            invalid_dlc_level=logging.INFO,
        )

        # Get GT11_TEMP (Brine/collector outlet) via RTR (best-effort)
        # PROTOCOL: GT11_TEMP is the collector circuit outlet temperature (brine out)
        # Uses discovered idx (varies by firmware, ~652 in FHEM reference)
        # NOTE: Not all heat pump models have this sensor
        _read_rtr_temperature(
            "GT11_TEMP",
            SENSOR_BRINE_OUT,
            "Brine Out",
            invalid_dlc_level=logging.INFO,
        )

        # Get compressor status via RTR request (best-effort with retry)
        # PROTOCOL: COMPRESSOR_STATE > 0 indicates compressor running (primary)
        # COMPRESSOR_REAL_FREQUENCY is kept as a secondary debug signal.
        compressor_running = False
        compressor_state: int | None = None
        compressor_frequency: int | None = None
        state_read = False

        def _parse_int(value: Any) -> int:
            if isinstance(value, str) and ":" in value:
                value = value.split(":")[0]
            return int(value or 0)

        for attempt in range(3):
            try:
                state_result = self._client.read_parameter("COMPRESSOR_STATE")
                compressor_state = _parse_int(state_result.get("decoded", 0))
                compressor_running = compressor_state > 0
                state_read = True
                _LOGGER.debug(
                    "Compressor state: %d (running=%s)",
                    compressor_state,
                    compressor_running,
                )
                break  # Success - exit retry loop
            except Exception as err:
                if attempt < 2:
                    _LOGGER.debug(
                        "RTR attempt %d/3 for COMPRESSOR_STATE failed: %s",
                        attempt + 1,
                        err,
                    )
                    time.sleep(0.3)  # Brief delay before retry
                else:
                    _LOGGER.warning(
                        "RTR FAILED for COMPRESSOR_STATE after 3 attempts: %s", err
                    )
                    if self._last_known_good_data is not None:
                        compressor_running = (
                            self._last_known_good_data.compressor_running
                        )
                        compressor_state = self._last_known_good_data.compressor_state

        try:
            result = self._client.read_parameter("COMPRESSOR_REAL_FREQUENCY")
            compressor_frequency = _parse_int(result.get("decoded", 0))
            _LOGGER.debug(
                "Compressor frequency: %d Hz (state_running=%s)",
                compressor_frequency,
                compressor_running,
            )
            if not state_read and compressor_frequency > 0:
                compressor_running = True
        except Exception as err:
            _LOGGER.debug("RTR FAILED for COMPRESSOR_REAL_FREQUENCY: %s", err)
            if not state_read and self._last_known_good_data is not None:
                compressor_running = self._last_known_good_data.compressor_running
                compressor_frequency = self._last_known_good_data.compressor_frequency

        # Get energy blocking status (best-effort)
        energy_blocked = False
        try:
            result = self._client.read_parameter("ADDITIONAL_BLOCKED")
            energy_blocked = int(result.get("decoded", 0)) > 0
        except Exception as err:
            _LOGGER.warning("RTR FAILED for ADDITIONAL_BLOCKED: %s", err)
            if self._last_known_good_data is not None:
                energy_blocked = self._last_known_good_data.energy_blocked

        # Get DHW extra duration (best-effort)
        dhw_extra_duration = 0
        if self._dhw_boost_end_time is not None:
            remaining_seconds = self._dhw_boost_end_time - time.time()
            if remaining_seconds > 0:
                # Round up to whole hours for a stable UI value.
                dhw_extra_duration = int((remaining_seconds + 3599) // 3600)
        else:
            try:
                dhw_extra_duration = self._api.hot_water.extra_duration
            except Exception as err:
                _LOGGER.warning("RTR FAILED for DHW_EXTRA_DURATION: %s", err)
                if self._last_known_good_data is not None:
                    dhw_extra_duration = self._last_known_good_data.dhw_extra_duration

        # Get heating season mode (best-effort)
        # PROTOCOL: dp2 format returns strings like "1:Always_On" - parse int prefix
        heating_season_mode: int | None = None
        try:
            result = self._client.read_parameter_with_validation(
                "HEATING_SEASON_MODE", expected_dlc=1
            )
            decoded = result.get("decoded")
            
            if decoded is None:
                # Read failed or invalid DLC
                raise ValueError(f"Invalid read: {result.get('error')}")

            if isinstance(decoded, str) and ":" in decoded:
                heating_season_mode = int(decoded.split(":")[0])
            else:
                heating_season_mode = int(decoded)
        except Exception as err:
            _LOGGER.warning("RTR FAILED for HEATING_SEASON_MODE: %s", err)
            if self._last_known_good_data is not None:
                heating_season_mode = self._last_known_good_data.heating_season_mode

        # Get DHW program mode (best-effort)
        # PROTOCOL: dp2 format returns strings like "1:Always_On" - parse int prefix
        dhw_program_mode: int | None = None
        try:
            result = self._client.read_parameter_with_validation(
                "DHW_PROGRAM_MODE", expected_dlc=1
            )
            decoded = result.get("decoded")
            
            if decoded is None:
                # Read failed or invalid DLC
                raise ValueError(f"Invalid read: {result.get('error')}")

            if isinstance(decoded, str) and ":" in decoded:
                dhw_program_mode = int(decoded.split(":")[0])
            else:
                dhw_program_mode = int(decoded)
        except Exception as err:
            _LOGGER.warning("RTR FAILED for DHW_PROGRAM_MODE: %s", err)
            if self._last_known_good_data is not None:
                dhw_program_mode = self._last_known_good_data.dhw_program_mode

        # Get heating curve parallel offset (best-effort)
        # PROTOCOL: Use GLOBAL parameter (idx=804) which is the user-adjustable setting
        # visible in the heat pump menu as "Parallel offset" / "Parallelle verschuiving"
        # The non-GLOBAL version (idx=802) is a different internal parameter
        heating_curve_offset: float | None = None
        try:
            result = self._client.read_parameter("HEATING_CURVE_PARALLEL_OFFSET_GLOBAL")
            decoded = result.get("decoded")
            if decoded is not None:
                heating_curve_offset = float(decoded)
        except Exception as err:
            _LOGGER.warning(
                "RTR FAILED for HEATING_CURVE_PARALLEL_OFFSET_GLOBAL: %s", err
            )
            if self._last_known_good_data is not None:
                heating_curve_offset = self._last_known_good_data.heating_curve_offset

        # Get DHW stop temperature (best-effort)
        # PROTOCOL: XDHW_STOP_TEMP controls when DHW charging stops (50-65°C)
        dhw_stop_temp: float | None = None
        try:
            if self._api is not None:
                dhw_stop_temp = self._api.hot_water.stop_temperature
        except Exception as err:
            _LOGGER.warning("RTR FAILED for XDHW_STOP_TEMP: %s", err)
            if self._last_known_good_data is not None:
                dhw_stop_temp = self._last_known_good_data.dhw_stop_temp

        # Get DHW setpoint temperature (best-effort)
        # PROTOCOL: DHW_CALCULATED_SETPOINT_TEMP is the normal DHW setpoint (40-70°C)
        # Note: parameter_defaults.py idx corrected from 385 to 386 per FHEM discovery
        dhw_setpoint: float | None = None
        try:
            result = self._client.read_parameter("DHW_CALCULATED_SETPOINT_TEMP")
            raw = result.get("raw")
            decoded = result.get("decoded")
            _LOGGER.debug(
                "DHW_CALCULATED_SETPOINT_TEMP: raw=%s, decoded=%s", raw, decoded
            )
            if decoded is not None:
                dhw_setpoint = float(decoded)
        except Exception as err:
            _LOGGER.warning("RTR FAILED for DHW_CALCULATED_SETPOINT_TEMP: %s", err)
            if self._last_known_good_data is not None:
                dhw_setpoint = self._last_known_good_data.dhw_setpoint

        # Get compressor blocked status (best-effort)
        compressor_blocked: bool | None = None
        # Helper to read binary status safely
        def _get_binary(param_name_or_idx: Any) -> bool:
            try:
                res = self._client.read_parameter_with_validation(
                    param_name_or_idx, expected_dlc=1, timeout=0.5
                )
                return bool(res.get("decoded", 0))
            except Exception:
                return False

        # Get digital status flags
        # Default to False if reading fails (safe fallback)
        # compressor_running = _get_binary("COMPRESSOR_RUNNING") # REMOVED: Unreliable
        energy_blocked = _get_binary(247)  # COMPRESSOR_BLOCKED
        dhw_active = _get_binary("PUMP_DHW_ACTIVE")  # idx 2016
        g1_active = _get_binary("PUMP_G1_CONTINUAL")  # idx 12796, Main/Heating pump
        
        # Get compressor status via RTR request (best-effort with retry)
        # PROTOCOL: COMPRESSOR_STATE > 0 indicates compressor running (primary)
        # COMPRESSOR_REAL_FREQUENCY is kept as a secondary debug signal.
        compressor_running = False
        compressor_state: int | None = None
        compressor_frequency: int | None = None
        state_read = False

        def _parse_int(value: Any) -> int:
            if isinstance(value, str) and ":" in value:
                value = value.split(":")[0]
            return int(value or 0)

        for attempt in range(3):
            try:
                state_result = self._client.read_parameter("COMPRESSOR_STATE")
                compressor_state = _parse_int(state_result.get("decoded", 0))
                compressor_running = compressor_state > 0
                state_read = True
                _LOGGER.debug(
                    "Compressor state: %d (running=%s)",
                    compressor_state,
                    compressor_running,
                )
                break  # Success - exit retry loop
            except Exception as err:
                if attempt < 2:
                    _LOGGER.debug(
                        "RTR attempt %d/3 for COMPRESSOR_STATE failed: %s",
                        attempt + 1,
                        err,
                    )
                    time.sleep(0.3)  # Brief delay before retry
                else:
                    _LOGGER.warning(
                        "RTR FAILED for COMPRESSOR_STATE after 3 attempts: %s", err
                    )
                    if self._last_known_good_data is not None:
                        compressor_running = (
                            self._last_known_good_data.compressor_running
                        )
                        compressor_state = self._last_known_good_data.compressor_state

        try:
            result = self._client.read_parameter("COMPRESSOR_REAL_FREQUENCY")
            # Handle potential None or string values safely
            val = result.get("decoded", 0)
            if val is None:
                val = 0
            compressor_frequency = _parse_int(val)
            _LOGGER.debug(
                "Compressor frequency: %d Hz (state_running=%s)",
                compressor_frequency,
                compressor_running,
            )
            # If state read failed but we have frequency > 0, assume running
            if not state_read and compressor_frequency > 0:
                compressor_running = True
            # If state read says OFF but frequency > 20Hz, trust frequency? 
            # (Maybe not, let's stick to simple logic for now, but freq is a good backup)
        except Exception as err:
            _LOGGER.debug("RTR FAILED for COMPRESSOR_REAL_FREQUENCY: %s", err)
            if not state_read and self._last_known_good_data is not None:
                # distinct from the COMPRESSOR_STATE fallback above
                if compressor_frequency is None: 
                     compressor_frequency = self._last_known_good_data.compressor_frequency

        # If we failed to read anything fresh related to compressor, 
        # checking _last_known_good_data for final fallback is wise, 
        # but the above blocks handle it partially.


        # Get compressor blocked status (best-effort)
        try:
            # Use the initialized energy_blocking helper to read status
            # This ensures we use the correct parameter (COMPRESSOR_BLOCKED idx 247)
            compressor_blocked = self.energy_blocking._read_compressor_status(timeout=2.0)
        except Exception as err:
            _LOGGER.warning("Failed to read compressor block status: %s", err)
            if self._last_known_good_data is not None:
                compressor_blocked = self._last_known_good_data.compressor_blocked
            else:
                compressor_blocked = None

        # Build result with mix of fresh and stale data
        result = BuderusData(
            temperatures=temperatures,
            compressor_running=compressor_running,
            compressor_blocked=compressor_blocked,
            energy_blocked=energy_blocked,
            dhw_active=dhw_active,
            g1_active=g1_active,
            dhw_extra_duration=dhw_extra_duration,
            heating_season_mode=heating_season_mode,
            dhw_program_mode=dhw_program_mode,
            heating_curve_offset=heating_curve_offset,
            dhw_stop_temp=dhw_stop_temp,
            dhw_setpoint=dhw_setpoint,
            compressor_state=compressor_state,
            compressor_frequency=compressor_frequency,
            parameter_results=parameter_results,
        )

        # Check if we got at least SOME fresh data
        # If broadcast failed and ALL parameters used stale data, this is a problem
        if not broadcast_success and self._last_known_good_data is not None:
            # Check if result is identical to stale data (nothing was fresh)
            if result == self._last_known_good_data:
                # Complete failure - raise exception to trigger error handling
                raise RuntimeError("All data reads failed, only stale data available")

        return result

    def get_data_age_seconds(self) -> int | None:
        """Get age of current data in seconds.

        Returns:
            Age in seconds since last successful update, or None if no data yet.
        """
        if self._last_successful_update is None:
            return None
        return int(time.time() - self._last_successful_update)

    def is_data_stale(self) -> bool:
        """Check if current data is stale (connection issues).

        Returns:
            True if there have been any consecutive failures, False otherwise.
        """
        return self._consecutive_failures > 0

    async def async_set_energy_blocking(self, blocked: bool) -> None:
        """Set energy blocking state."""
        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_set_energy_blocking, blocked
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
        except TimeoutError:
            _LOGGER.error("Timeout setting energy blocking")
            raise HomeAssistantError("Timeout communicating with heat pump") from None

    def _sync_set_energy_blocking(self, blocked: bool) -> None:
        """Synchronous energy blocking set (runs in executor)."""
        value = 1 if blocked else 0
        self._client.write_value("ADDITIONAL_BLOCKED", value)
        _LOGGER.info("Set energy blocking to %s", blocked)

    async def async_set_dhw_extra_duration(self, hours: int) -> None:
        """Set DHW extra production duration.

        Args:
            hours: Duration in hours (0-48). 0 stops extra production.
        """
        if hours < 0:
            raise ValueError(f"DHW extra duration must be >= 0, got {hours}")

        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    if hours == 0:
                        await self._async_stop_dhw_boost_locked()
                        return

                    result: dict[str, Any] = await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_start_dhw_extra_duration, hours
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
        except TimeoutError:
            _LOGGER.error("Timeout setting DHW extra duration")
            raise HomeAssistantError("Timeout communicating with heat pump") from None

            if result.get("strategy") == "program_mode_override":
                end_time = time.time() + hours * 3600
                self._dhw_boost_end_time = end_time
                self._dhw_boost_original_program_mode = result.get(
                    "original_program_mode"
                )

                if self._dhw_boost_task is not None:
                    self._dhw_boost_task.cancel()
                self._dhw_boost_task = self.hass.async_create_task(
                    self._async_dhw_boost_timer(end_time),
                    name="buderus_wps_dhw_boost_timer",
                )
            else:
                # XDHW_TIME accepted (or we at least attempted it) -> no HA-side timer needed.
                self._dhw_boost_end_time = None
                self._dhw_boost_original_program_mode = None
                if self._dhw_boost_task is not None:
                    self._dhw_boost_task.cancel()
                    self._dhw_boost_task = None

    async def _async_stop_dhw_boost_locked(self) -> None:
        """Stop any active DHW boost and restore program mode when applicable.

        Must be called with ``self._lock`` held.
        """
        if self._dhw_boost_task is not None:
            self._dhw_boost_task.cancel()
            self._dhw_boost_task = None

        # Always attempt to stop XDHW_TIME-based boost if the device supports it.
        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(self._sync_write_xdhw_time, 0),
                timeout=EXECUTOR_JOB_TIMEOUT,
            )
        except TimeoutError:
            _LOGGER.warning("Timeout stopping DHW boost (XDHW_TIME write)")

        original_mode = self._dhw_boost_original_program_mode
        self._dhw_boost_end_time = None
        self._dhw_boost_original_program_mode = None

        # If we used program-mode override, restore previous mode.
        if original_mode is not None and self._client is not None:
            try:
                await asyncio.wait_for(
                    self.hass.async_add_executor_job(
                        self._sync_set_dhw_program_mode, original_mode
                    ),
                    timeout=EXECUTOR_JOB_TIMEOUT,
                )
            except TimeoutError:
                _LOGGER.warning("Timeout restoring DHW program mode")
        _LOGGER.info("Stopped DHW extra production")

    async def _async_dhw_boost_timer(self, end_time: float) -> None:
        """Timer task to automatically stop DHW boost after the requested duration."""
        try:
            delay = max(end_time - time.time(), 0)
            await asyncio.sleep(delay)
            # Use timeout for lock acquisition in background task
            try:
                async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                    async with self._lock:
                        # If the timer was extended/replaced, ignore this run.
                        if self._dhw_boost_end_time != end_time:
                            return
                        await self._async_stop_dhw_boost_locked()
            except TimeoutError:
                 _LOGGER.error("Timeout acquiring lock for DHW boost timer completion")
            await self.async_request_refresh()
        except asyncio.CancelledError:
            return
        except Exception as err:
            _LOGGER.error("DHW boost timer failed: %s", err)

    def _sync_write_xdhw_time(self, hours: int) -> None:
        """Try to write XDHW_TIME via MenuAPI (best-effort)."""
        try:
            if self._api is None:
                return
            self._api.hot_water.extra_duration = hours
        except Exception as err:
            _LOGGER.debug("XDHW_TIME write ignored/failed: %s", err)

    def _sync_start_dhw_extra_duration(self, hours: int) -> dict[str, Any]:
        """Start DHW extra production for a duration.

        Strategy:
        1) Try the device-native XDHW_TIME write.
           With element discovery, this should use the correct CAN ID for the device.
        2) Only fall back to program mode override if XDHW_TIME write fails.

        Note: We don't verify the write via readback because:
        - Element discovery ensures we're using the correct parameter index
        - FHEM also trusts the write without verification
        - Readback adds latency and can fail due to CAN bus traffic
        """
        # 1) Try native extra duration with discovered parameter index
        try:
            if self._api is not None:
                self._api.hot_water.extra_duration = hours
                _LOGGER.info(
                    "Started DHW extra production for %d hours (XDHW_TIME)", hours
                )
                return {"strategy": "xdhw_time"}
        except Exception as err:
            _LOGGER.warning(
                "XDHW_TIME write failed, falling back to program mode: %s", err
            )

        # 2) Fallback: program mode override
        original_program_mode: int | None = None
        try:
            if self._client is not None:
                result = self._client.read_parameter("DHW_PROGRAM_MODE")
                decoded = result.get("decoded", 0)
                if isinstance(decoded, str) and ":" in decoded:
                    original_program_mode = int(decoded.split(":")[0])
                else:
                    original_program_mode = int(decoded)
        except Exception as err:
            _LOGGER.debug("Failed to read current DHW_PROGRAM_MODE: %s", err)

        if self._client is not None:
            self._client.write_value("DHW_PROGRAM_MODE", 1)  # Always On

        _LOGGER.info(
            "Started DHW extra production for %d hours (fallback: DHW program mode override)",
            hours,
        )
        return {
            "strategy": "program_mode_override",
            "original_program_mode": original_program_mode,
        }

    async def async_set_heating_season_mode(self, mode: int) -> None:
        """Set heating season mode for peak hour blocking.

        Args:
            mode: 0=Winter (forced), 1=Auto, 2=Off (summer/blocked)
        """

        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_set_heating_season_mode, mode
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
        except TimeoutError:
            _LOGGER.error("Timeout setting heating season mode")
            raise HomeAssistantError("Timeout communicating with heat pump") from None

    def _sync_set_heating_season_mode(self, mode: int) -> None:
        """Synchronous heating season mode set (runs in executor)."""
        self._client.write_value("HEATING_SEASON_MODE", mode)
        mode_names = {0: "Winter (forced)", 1: "Automatic", 2: "Off (summer)"}
        _LOGGER.info(
            "Set heating season mode to %s (%d)", mode_names.get(mode, "Unknown"), mode
        )

    async def async_set_dhw_program_mode(self, mode: int) -> None:
        """Set DHW program mode for peak hour blocking.

        Args:
            mode: 0=Auto, 1=Always On, 2=Always Off (blocked)
        """


        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_set_dhw_program_mode, mode
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
        except TimeoutError:
            _LOGGER.error("Timeout setting DHW program mode")
            raise HomeAssistantError("Timeout communicating with heat pump") from None

    def _sync_set_dhw_program_mode(self, mode: int) -> None:
        """Synchronous DHW program mode set (runs in executor)."""
        self._client.write_value("DHW_PROGRAM_MODE", mode)
        mode_names = {0: "Automatic", 1: "Always On", 2: "Always Off"}
        _LOGGER.info(
            "Set DHW program mode to %s (%d)", mode_names.get(mode, "Unknown"), mode
        )

    async def async_set_heating_curve_offset(self, offset: float) -> None:
        """Set heating curve parallel offset.

        Args:
            offset: Parallel offset in °C (-10.0 to +10.0)

        Raises:
            ValueError: If offset outside allowed range
        """
        if not -10.0 <= offset <= 10.0:
            raise ValueError(
                f"Heating curve offset must be between -10.0 and +10.0°C, got {offset}"
            )
        _LOGGER.debug("async_set_heating_curve_offset called with offset=%.1f", offset)
        _LOGGER.debug("async_set_heating_curve_offset called with offset=%.1f", offset)
        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_set_heating_curve_offset, offset
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
            _LOGGER.debug("async_set_heating_curve_offset completed successfully")
        except TimeoutError:
            _LOGGER.error("Timeout setting heating curve offset")
            raise HomeAssistantError("Timeout communicating with heat pump") from None
        except Exception as err:
            _LOGGER.error("async_set_heating_curve_offset FAILED: %s", err)
            raise

    def _sync_set_heating_curve_offset(self, offset: float) -> None:
        """Synchronous heating curve offset set (runs in executor)."""
        _LOGGER.debug("_sync_set_heating_curve_offset called with offset=%.1f", offset)
        try:
            # Write to GLOBAL parameter (idx=804) which is the user-adjustable setting
            self._client.write_value("HEATING_CURVE_PARALLEL_OFFSET_GLOBAL", offset)
            _LOGGER.info("Set heating curve parallel offset to %.1f°C", offset)
        except Exception as err:
            _LOGGER.error("_sync_set_heating_curve_offset FAILED: %s", err)
            raise

    async def async_set_dhw_stop_temp(self, temp: float) -> None:
        """Set DHW stop charging temperature.

        Args:
            temp: Temperature in °C (50.0 to 65.0)

        Raises:
            ValueError: If temperature outside allowed range
        """
        if not 50.0 <= temp <= 65.0:
            raise ValueError(
                f"DHW stop temperature must be between 50.0 and 65.0°C, got {temp}"
            )
        _LOGGER.debug("async_set_dhw_stop_temp called with temp=%.1f", temp)
        _LOGGER.debug("async_set_dhw_stop_temp called with temp=%.1f", temp)
        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_set_dhw_stop_temp, temp
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
            _LOGGER.debug("async_set_dhw_stop_temp completed successfully")
        except TimeoutError:
            _LOGGER.error("Timeout setting DHW stop temperature")
            raise HomeAssistantError("Timeout communicating with heat pump") from None
        except Exception as err:
            _LOGGER.error("async_set_dhw_stop_temp FAILED: %s", err)
            raise

    def _sync_set_dhw_stop_temp(self, temp: float) -> None:
        """Synchronous DHW stop temp set (runs in executor)."""
        _LOGGER.debug("_sync_set_dhw_stop_temp called with temp=%.1f", temp)
        try:
            if self._api is not None:
                self._api.hot_water.stop_temperature = temp
            _LOGGER.info("Set DHW stop temperature to %.1f°C", temp)
        except Exception as err:
            _LOGGER.error("_sync_set_dhw_stop_temp FAILED: %s", err)
            raise

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
        _LOGGER.debug("async_set_dhw_setpoint called with temp=%.1f", temp)
        try:
            async with asyncio.timeout(LOCK_ACQUIRE_TIMEOUT):
                async with self._lock:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(
                            self._sync_set_dhw_setpoint, temp
                        ),
                        timeout=EXECUTOR_JOB_TIMEOUT,
                    )
            _LOGGER.debug("async_set_dhw_setpoint completed successfully")
        except TimeoutError:
            _LOGGER.error("Timeout setting DHW setpoint")
            raise HomeAssistantError("Timeout communicating with heat pump") from None
        except Exception as err:
            _LOGGER.error("async_set_dhw_setpoint FAILED: %s", err)
            raise

    def _sync_set_dhw_setpoint(self, temp: float) -> None:
        """Synchronous DHW setpoint set (runs in executor)."""
        _LOGGER.debug("_sync_set_dhw_setpoint called with temp=%.1f", temp)
        try:
            # Note: parameter_defaults.py idx corrected from 385 to 386 per FHEM discovery
            self._client.write_value("DHW_CALCULATED_SETPOINT_TEMP", temp)
            _LOGGER.info("Set DHW setpoint to %.1f°C", temp)
        except Exception as err:
            _LOGGER.error("_sync_set_dhw_setpoint FAILED: %s", err)
            raise
