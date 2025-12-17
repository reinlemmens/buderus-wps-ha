"""Switches for Buderus WPS Heat Pump."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_ENERGY_BLOCK, ICON_USB
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    async_add_entities(
        [
            BuderusEnergyBlockSwitch(coordinator, entry),
            BuderusUSBConnectionSwitch(coordinator, entry),
        ]
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the switch platform via YAML (legacy)."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities([BuderusEnergyBlockSwitch(coordinator)])


class BuderusEnergyBlockSwitch(BuderusEntity, SwitchEntity):
    """Switch for energy blocking control."""

    _attr_name = "Energy Block"
    _attr_icon = ICON_ENERGY_BLOCK

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the energy block switch."""
        super().__init__(coordinator, "energy_block", entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if energy blocking is enabled.

        Energy blocking is active when both heating and DHW are set to "Off" mode.
        """
        if self.coordinator.data is None:
            return None

        # Check if both heating and DHW are in blocked state
        # HEATING_SEASON_MODE: 2 = Off (summer/blocked)
        # DHW_PROGRAM_MODE: 2 = Always Off (blocked)
        heating_blocked = self.coordinator.data.heating_season_mode == 2
        dhw_blocked = self.coordinator.data.dhw_program_mode == 2

        return heating_blocked and dhw_blocked

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable energy blocking.

        Sets both heating and DHW to blocked state:
        - HEATING_SEASON_MODE to 2 (Off/Summer)
        - DHW_PROGRAM_MODE to 2 (Always Off)
        """
        # Block both heating and DHW
        await self.coordinator.async_set_heating_season_mode(2)  # Off (summer)
        await self.coordinator.async_set_dhw_program_mode(2)  # Always Off
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable energy blocking.

        Restores normal operation:
        - HEATING_SEASON_MODE to 1 (Automatic)
        - DHW_PROGRAM_MODE to 0 (Automatic)
        """
        # Restore automatic operation
        await self.coordinator.async_set_heating_season_mode(1)  # Automatic
        await self.coordinator.async_set_dhw_program_mode(0)  # Automatic
        await self.coordinator.async_request_refresh()


class BuderusUSBConnectionSwitch(BuderusEntity, SwitchEntity):
    """Switch to control USB connection for CLI access.

    This switch allows developers to temporarily release the USB serial port
    so the CLI tool can access it for debugging. When toggled OFF, the
    integration disconnects from the USB port. When toggled ON, it reconnects.
    """

    _attr_name = "USB Connection"
    _attr_icon = ICON_USB

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the USB connection switch."""
        super().__init__(coordinator, "usb_connection", entry)

    @property
    def is_on(self) -> bool:
        """Return True if USB is connected.

        Returns False if manually disconnected (released for CLI access).
        """
        return not self.coordinator._manually_disconnected

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Release USB port for CLI access.

        Sets the manual disconnect flag and disconnects from the USB serial port.
        This allows the CLI tool to open and use the port for debugging.
        The integration will continue showing last-known-good data (stale) while
        disconnected.
        """
        await self.coordinator.async_manual_disconnect()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Reconnect USB port.

        Clears the manual disconnect flag and attempts to reconnect to the
        USB serial port. If the port is still in use by the CLI tool, this
        will fail with a clear error message.

        Raises:
            HomeAssistantError: If USB port is still in use or connection fails
        """
        # Import exception types from bundled library to avoid module-level conflicts
        from .buderus_wps.exceptions import (
            DeviceInitializationError,
            DeviceNotFoundError,
            DevicePermissionError,
        )

        try:
            await self.coordinator.async_manual_connect()
        except (
            DeviceNotFoundError,
            DevicePermissionError,
            DeviceInitializationError,
        ) as err:
            _LOGGER.warning("Cannot connect - port may be in use by CLI: %s", err)
            raise HomeAssistantError(f"USB port in use: {err}") from err
