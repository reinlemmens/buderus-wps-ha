"""DataUpdateCoordinator for Buderus WPS Heat Pump."""

from __future__ import annotations

import asyncio
import logging
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

    async def _handle_connection_failure(self) -> None:
        """Schedule reconnection with exponential backoff."""
        if self._reconnect_task is not None:
            return  # Already reconnecting

        self._reconnect_task = self.hass.async_create_background_task(
            self._reconnect_with_backoff(),
            "buderus_wps_reconnect",
        )

    async def _reconnect_with_backoff(self) -> None:
        """Attempt reconnection with exponential backoff."""
        while not self._connected:
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
        # Import here to avoid loading at module level
        import os
        import sys

        # Add the parent directory to path so we can import buderus_wps
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)

        from buderus_wps import (
            BroadcastMonitor,
            HeatPumpClient,
            ParameterRegistry,
            USBtinAdapter,
        )
        from buderus_wps.menu_api import MenuAPI

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
        """Fetch data from the heat pump."""
        async with self._lock:
            if not self._connected:
                # Trigger reconnection if not already in progress
                await self._handle_connection_failure()
                raise UpdateFailed("Not connected to heat pump")

            try:
                return await self.hass.async_add_executor_job(self._sync_fetch_data)
            except Exception as err:
                _LOGGER.error("Error fetching data from heat pump: %s", err)
                # Mark as disconnected and trigger reconnection
                self._connected = False
                await self._handle_connection_failure()
                raise UpdateFailed(f"Error fetching data: {err}") from err

    def _sync_fetch_data(self) -> BuderusData:
        """Synchronous data fetch (runs in executor)."""
        from buderus_wps.config import get_default_sensor_map

        # Get temperature readings from broadcast monitoring
        # This is more reliable than RTR requests
        sensor_map = get_default_sensor_map()

        # Collect broadcast data for a short duration
        cache = self._monitor.collect(duration=5.0)

        # Extract temperatures from cache
        temperatures: dict[str, float | None] = {
            SENSOR_OUTDOOR: None,
            SENSOR_SUPPLY: None,
            SENSOR_RETURN: None,
            SENSOR_DHW: None,
            SENSOR_BRINE_IN: None,
        }

        for (base, idx), sensor_name in sensor_map.items():
            reading = cache.get_by_idx_and_base(idx, base)
            if reading is not None and sensor_name in temperatures:
                temperatures[sensor_name] = reading.temperature

        # Get compressor status from MenuAPI
        compressor_running = False
        try:
            status = self._api.status
            compressor_running = status.compressor_running
        except Exception as err:
            _LOGGER.warning("Could not read compressor status: %s", err)

        # Get energy blocking status
        energy_blocked = False
        try:
            result = self._client.read_parameter("ADDITIONAL_BLOCKED")
            energy_blocked = int(result.get("decoded", 0)) > 0
        except Exception as err:
            _LOGGER.debug("Could not read energy blocking status: %s", err)

        # Get DHW extra duration (hours remaining)
        dhw_extra_duration = 0
        try:
            dhw_extra_duration = self._api.hot_water.extra_duration
        except Exception as err:
            _LOGGER.debug("Could not read DHW extra duration: %s", err)

        # Get heating season mode (idx=884)
        # Used for peak hour blocking - set to 2 (Off) to disable heating
        heating_season_mode: int | None = None
        try:
            result = self._client.read_parameter("HEATING_SEASON_MODE")
            heating_season_mode = int(result.get("decoded", 0))
        except Exception as err:
            _LOGGER.debug("Could not read heating season mode: %s", err)

        # Get DHW program mode (idx=489)
        # Used for peak hour blocking - set to 2 (Off) to disable DHW
        dhw_program_mode: int | None = None
        try:
            result = self._client.read_parameter("DHW_PROGRAM_MODE")
            dhw_program_mode = int(result.get("decoded", 0))
        except Exception as err:
            _LOGGER.debug("Could not read DHW program mode: %s", err)

        return BuderusData(
            temperatures=temperatures,
            compressor_running=compressor_running,
            energy_blocked=energy_blocked,
            dhw_extra_duration=dhw_extra_duration,
            heating_season_mode=heating_season_mode,
            dhw_program_mode=dhw_program_mode,
        )

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
