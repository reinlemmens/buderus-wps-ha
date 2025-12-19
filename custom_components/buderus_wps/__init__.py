"""Buderus WPS Heat Pump integration for Home Assistant.

This integration provides monitoring and control of Buderus WPS heat pumps
via CAN bus over USB serial connection (USBtin adapter).

Features:
- Temperature sensors (outdoor, supply, return, DHW, brine inlet)
- Compressor running status
- Energy blocking control
- DHW extra production control
"""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery

from .const import (
    CONF_PORT,
    CONF_SERIAL_DEVICE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import BuderusCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(cv.positive_int, vol.Range(min=10, max=300)),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Buderus WPS integration from YAML configuration."""
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    port = conf.get(CONF_PORT, DEFAULT_PORT)
    scan_interval = conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    _LOGGER.info(
        "Setting up Buderus WPS integration via YAML (port=%s, scan_interval=%d)",
        port,
        scan_interval,
    )

    # Create coordinator
    coordinator = BuderusCoordinator(hass, port, scan_interval)

    # Connect to heat pump
    if not await coordinator.async_setup():
        _LOGGER.error("Failed to set up Buderus WPS integration")
        return False

    # Perform initial data fetch
    await coordinator.async_refresh()

    # Store coordinator for platforms to use (YAML mode uses "coordinator" key)
    hass.data[DOMAIN]["coordinator"] = coordinator

    # Set up platforms via discovery (legacy YAML mode)
    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    # Register shutdown handler
    async def async_shutdown(event: Any) -> None:
        """Handle Home Assistant shutdown."""
        await coordinator.async_shutdown()

    hass.bus.async_listen_once("homeassistant_stop", async_shutdown)

    _LOGGER.info("Buderus WPS integration setup complete (YAML)")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Buderus WPS from a config entry."""
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})

    port = entry.data.get(CONF_SERIAL_DEVICE, DEFAULT_PORT)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    _LOGGER.info(
        "Setting up Buderus WPS integration via config entry (port=%s, scan_interval=%d)",
        port,
        scan_interval,
    )

    # Create coordinator
    coordinator = BuderusCoordinator(hass, port, scan_interval)

    # Connect to heat pump
    if not await coordinator.async_setup():
        _LOGGER.error("Failed to connect to heat pump at %s", port)
        return False

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator keyed by entry_id for config entry mode
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "entry": entry,
    }

    # Set up platforms via config entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Buderus WPS integration setup complete (config entry)")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data:
            coordinator = entry_data.get("coordinator")
            if coordinator:
                await coordinator.async_shutdown()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
