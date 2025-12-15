"""Data update coordinator for Buderus WPS Heat Pump integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.heat_pump import HeatPumpClient
from buderus_wps.exceptions import (
    DeviceCommunicationError,
    DeviceDisconnectedError,
    TimeoutError as BuderusTimeoutError,
)

from .const import (
    CONF_SERIAL_DEVICE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class BuderusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching heat pump data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._port = entry.data[CONF_SERIAL_DEVICE]
        
        # Initialize adapter and client
        self._adapter = USBtinAdapter(self._port, timeout=DEFAULT_TIMEOUT)
        self._client: HeatPumpClient | None = None
        
        # Get scan interval from options or use default
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from heat pump."""
        try:
            return await self.hass.async_add_executor_job(self._update_data)
        except (DeviceCommunicationError, DeviceDisconnectedError, BuderusTimeoutError) as err:
            raise UpdateFailed(f"Error communicating with heat pump: {err}") from err

    def _update_data(self) -> dict[str, Any]:
        """Fetch data from heat pump (runs in executor)."""
        # Ensure adapter is open
        if not self._adapter._ser or not self._adapter._ser.is_open:
            self._adapter.open()
        
        # Initialize client if needed
        if self._client is None:
            self._client = HeatPumpClient(self._adapter)
        
        # For now, return empty data dict
        # We'll populate this with actual parameter reads in the platform files
        data: dict[str, Any] = {}
        
        return data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.hass.async_add_executor_job(self._shutdown)

    def _shutdown(self) -> None:
        """Close adapter connection (runs in executor)."""
        if self._adapter:
            try:
                self._adapter.close()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Error closing adapter: %s", err)
