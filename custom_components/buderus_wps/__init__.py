"""The Buderus WPS Heat Pump integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import BuderusDataUpdateCoordinator

if TYPE_CHECKING:
    from .coordinator import BuderusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

BuderusConfigEntry = ConfigEntry[BuderusDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BuderusConfigEntry) -> bool:
    """Set up Buderus WPS Heat Pump from a config entry."""
    coordinator = BuderusDataUpdateCoordinator(hass, entry)
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Unable to connect to heat pump: {err}") from err
    
    entry.runtime_data = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BuderusConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: BuderusConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
