"""DataUpdateCoordinator for Buderus WPS Heat Pump."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BACKOFF_INITIAL,
    BACKOFF_MAX,
    DOMAIN,
    SENSOR_BRINE_IN,
    SENSOR_DHW,
    SENSOR_OUTDOOR,
    SENSOR_RETURN,
    SENSOR_SUPPLY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class BuderusData:
    """Data class for heat pump readings."""

    temperatures: dict[str, float | None]
    compressor_running: bool
    energy_blocked: bool
    dhw_extra_duration: int  # Hours remaining (0-24), 0 = not active
    heating_season_mode: int | None  # 0=Winter, 1=Auto, 2=Off
    dhw_program_mode: int | None  # 0=Auto, 1=On, 2=Off


class BuderusCoordinator(DataUpdateCoordinator[BuderusData]):
    """Coordinator for fetching data from Buderus WPS heat pump."""

    def __init__(
        self,
        hass: HomeAssistant,
        port: str,
        scan_interval: int,
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
        self._lock = asyncio.Lock()
        self._connected = False
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
            HeatPumpClient,
            ParameterRegistry,
            USBtinAdapter,
        )
        from .buderus_wps.menu_api import MenuAPI
        from .buderus_wps.exceptions import (
            TimeoutError as BuderusTimeoutError,
            DeviceCommunicationError,
            DeviceDisconnectedError,
            DeviceInitializationError,
            DeviceNotFoundError,
            DevicePermissionError,
            ReadTimeoutError,
        )

        _LOGGER.debug("Connecting to heat pump at %s", self.port)

        self._adapter = USBtinAdapter(self.port)
        self._adapter.connect()

        self._registry = ParameterRegistry()
        self._client = HeatPumpClient(self._adapter, self._registry)
        self._monitor = BroadcastMonitor(self._adapter)
        self._api = MenuAPI(self._client)

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
                fresh_data = await self.hass.async_add_executor_job(
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
        }

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

        # Get compressor status from broadcast cache (best-effort)
        # Uses COMPRESSOR_REAL_FREQUENCY (idx=278) from broadcast instead of RTR
        compressor_running = False
        try:
            # Read compressor frequency from broadcast cache (idx=278)
            reading = cache.get_by_idx(278)  # COMPRESSOR_REAL_FREQUENCY idx
            if reading is not None:
                compressor_running = reading.raw_value > 0
                _LOGGER.debug(
                    "Compressor frequency from broadcast: %d Hz (running=%s)",
                    reading.raw_value,
                    compressor_running,
                )
            else:
                _LOGGER.debug("No compressor frequency broadcast found in cache")
                # Use stale value if available
                if self._last_known_good_data is not None:
                    compressor_running = self._last_known_good_data.compressor_running
        except Exception as err:
            _LOGGER.debug("Could not read compressor status from broadcast: %s", err)
            # Use stale value if available
            if self._last_known_good_data is not None:
                compressor_running = self._last_known_good_data.compressor_running

        # Get energy blocking status (best-effort)
        energy_blocked = False
        try:
            result = self._client.read_parameter("ADDITIONAL_BLOCKED")
            energy_blocked = int(result.get("decoded", 0)) > 0
        except Exception as err:
            _LOGGER.debug("Could not read energy blocking status: %s", err)
            if self._last_known_good_data is not None:
                energy_blocked = self._last_known_good_data.energy_blocked

        # Get DHW extra duration (best-effort)
        dhw_extra_duration = 0
        try:
            dhw_extra_duration = self._api.hot_water.extra_duration
        except Exception as err:
            _LOGGER.debug("Could not read DHW extra duration: %s", err)
            if self._last_known_good_data is not None:
                dhw_extra_duration = self._last_known_good_data.dhw_extra_duration

        # Get heating season mode (best-effort)
        heating_season_mode: int | None = None
        try:
            result = self._client.read_parameter("HEATING_SEASON_MODE")
            heating_season_mode = int(result.get("decoded", 0))
        except Exception as err:
            _LOGGER.debug("Could not read heating season mode: %s", err)
            if self._last_known_good_data is not None:
                heating_season_mode = self._last_known_good_data.heating_season_mode

        # Get DHW program mode (best-effort)
        dhw_program_mode: int | None = None
        try:
            result = self._client.read_parameter("DHW_PROGRAM_MODE")
            dhw_program_mode = int(result.get("decoded", 0))
        except Exception as err:
            _LOGGER.debug("Could not read DHW program mode: %s", err)
            if self._last_known_good_data is not None:
                dhw_program_mode = self._last_known_good_data.dhw_program_mode

        # Build result with mix of fresh and stale data
        result = BuderusData(
            temperatures=temperatures,
            compressor_running=compressor_running,
            energy_blocked=energy_blocked,
            dhw_extra_duration=dhw_extra_duration,
            heating_season_mode=heating_season_mode,
            dhw_program_mode=dhw_program_mode,
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
        async with self._lock:
            await self.hass.async_add_executor_job(
                self._sync_set_energy_blocking, blocked
            )

    def _sync_set_energy_blocking(self, blocked: bool) -> None:
        """Synchronous energy blocking set (runs in executor)."""
        value = 1 if blocked else 0
        self._client.write_value("ADDITIONAL_BLOCKED", value)
        _LOGGER.info("Set energy blocking to %s", blocked)

    async def async_set_dhw_extra_duration(self, hours: int) -> None:
        """Set DHW extra production duration.

        Args:
            hours: Duration in hours (0-24). 0 stops extra production.
        """
        async with self._lock:
            await self.hass.async_add_executor_job(
                self._sync_set_dhw_extra_duration, hours
            )

    def _sync_set_dhw_extra_duration(self, hours: int) -> None:
        """Synchronous DHW extra duration set (runs in executor)."""
        self._api.hot_water.extra_duration = hours
        if hours > 0:
            _LOGGER.info("Started DHW extra production for %d hours", hours)
        else:
            _LOGGER.info("Stopped DHW extra production")

    async def async_set_heating_season_mode(self, mode: int) -> None:
        """Set heating season mode for peak hour blocking.

        Args:
            mode: 0=Winter (forced), 1=Auto, 2=Off (summer/blocked)
        """
        async with self._lock:
            await self.hass.async_add_executor_job(
                self._sync_set_heating_season_mode, mode
            )

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
        async with self._lock:
            await self.hass.async_add_executor_job(
                self._sync_set_dhw_program_mode, mode
            )

    def _sync_set_dhw_program_mode(self, mode: int) -> None:
        """Synchronous DHW program mode set (runs in executor)."""
        self._client.write_value("DHW_PROGRAM_MODE", mode)
        mode_names = {0: "Automatic", 1: "Always On", 2: "Always Off"}
        _LOGGER.info(
            "Set DHW program mode to %s (%d)", mode_names.get(mode, "Unknown"), mode
        )
