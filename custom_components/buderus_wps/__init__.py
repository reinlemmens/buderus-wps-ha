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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import discovery

try:
    from homeassistant.core import SupportsResponse
except ImportError:  # pragma: no cover - older HA versions
    SupportsResponse = None

from .const import (
    ATTR_ENTRY_ID,
    ATTR_EXPECTED_DLC,
    ATTR_LIMIT,
    ATTR_NAME_CONTAINS,
    ATTR_NAME_OR_IDX,
    ATTR_TIMEOUT,
    CONF_PARAMETER_ALLOWLIST,
    CONF_PORT,
    CONF_SERIAL_DEVICE,
    DEFAULT_PARAMETER_ALLOWLIST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_LIST_PARAMETERS,
    SERVICE_READ_PARAMETER,
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
                vol.Optional(
                    CONF_PARAMETER_ALLOWLIST,
                    default=list(DEFAULT_PARAMETER_ALLOWLIST),
                ): vol.All(cv.ensure_list, [cv.string]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _normalize_allowlist(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",")]
        return _dedupe_list([item for item in parts if item])
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                parts = [part.strip() for part in item.split(",")]
                items.extend([part for part in parts if part])
            else:
                items.append(str(item))
        return _dedupe_list(items)
    return [str(value)]


def _dedupe_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _iter_coordinators(
    hass: HomeAssistant,
) -> list[tuple[str, BuderusCoordinator]]:
    coordinators: list[tuple[str, BuderusCoordinator]] = []
    domain_data = hass.data.get(DOMAIN, {})
    yaml_coordinator = domain_data.get("coordinator")
    if isinstance(yaml_coordinator, BuderusCoordinator):
        coordinators.append(("yaml", yaml_coordinator))
    for entry_id, entry_data in domain_data.items():
        if entry_id in {"coordinator", "services_registered"}:
            continue
        if isinstance(entry_data, dict):
            coordinator = entry_data.get("coordinator")
            if isinstance(coordinator, BuderusCoordinator):
                coordinators.append((entry_id, coordinator))
    return coordinators


def _resolve_coordinator(
    hass: HomeAssistant, entry_id: str | None
) -> tuple[str, BuderusCoordinator]:
    coordinators = _iter_coordinators(hass)
    if entry_id:
        for coord_id, coordinator in coordinators:
            if coord_id == entry_id:
                return coord_id, coordinator
        raise HomeAssistantError(f"Unknown entry_id: {entry_id}")
    if len(coordinators) == 1:
        return coordinators[0]
    if not coordinators:
        raise HomeAssistantError("No Buderus WPS coordinators are available")
    raise HomeAssistantError(
        "Multiple Buderus WPS entries are configured; specify entry_id"
    )


async def _async_register_services(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("services_registered"):
        return

    service_schema = vol.Schema(
        {
            vol.Required(ATTR_NAME_OR_IDX): vol.Any(cv.string, cv.positive_int),
            vol.Optional(ATTR_ENTRY_ID): cv.string,
            vol.Optional(ATTR_EXPECTED_DLC): cv.positive_int,
            vol.Optional(ATTR_TIMEOUT): vol.Coerce(float),
        }
    )
    list_schema = vol.Schema(
        {
            vol.Optional(ATTR_ENTRY_ID): cv.string,
            vol.Optional(ATTR_NAME_CONTAINS): cv.string,
            vol.Optional(ATTR_LIMIT): cv.positive_int,
        }
    )

    async def _handle_read_parameter(call):
        coord_id, coordinator = _resolve_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
        name_or_idx = call.data[ATTR_NAME_OR_IDX]
        expected_dlc = call.data.get(ATTR_EXPECTED_DLC)
        timeout = call.data.get(ATTR_TIMEOUT)

        result = await coordinator.async_read_parameter(
            name_or_idx,
            expected_dlc=expected_dlc,
            timeout=timeout,
        )
        result["requested"] = name_or_idx
        result["entry_id"] = coord_id

        if SupportsResponse is not None:
            return result
        hass.bus.async_fire(f"{DOMAIN}_parameter_read", result)

    async def _handle_list_parameters(call):
        coord_id, coordinator = _resolve_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
        name_contains = call.data.get(ATTR_NAME_CONTAINS)
        limit = call.data.get(ATTR_LIMIT)

        parameters = await coordinator.async_list_parameters(
            name_contains=name_contains,
            limit=limit,
        )
        result = {"entry_id": coord_id, "parameters": parameters}

        if SupportsResponse is not None:
            return result
        hass.bus.async_fire(f"{DOMAIN}_parameters_listed", result)

    if SupportsResponse is not None:
        hass.services.async_register(
            DOMAIN,
            SERVICE_READ_PARAMETER,
            _handle_read_parameter,
            schema=service_schema,
            supports_response=SupportsResponse.ONLY,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_LIST_PARAMETERS,
            _handle_list_parameters,
            schema=list_schema,
            supports_response=SupportsResponse.ONLY,
        )
    else:
        hass.services.async_register(
            DOMAIN,
            SERVICE_READ_PARAMETER,
            _handle_read_parameter,
            schema=service_schema,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_LIST_PARAMETERS,
            _handle_list_parameters,
            schema=list_schema,
        )

    domain_data["services_registered"] = True


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Buderus WPS integration from YAML configuration."""
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})
    await _async_register_services(hass)

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    port = conf.get(CONF_PORT, DEFAULT_PORT)
    scan_interval = conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allowlist = _normalize_allowlist(conf.get(CONF_PARAMETER_ALLOWLIST, []))

    _LOGGER.info(
        "Setting up Buderus WPS integration via YAML (port=%s, scan_interval=%d)",
        port,
        scan_interval,
    )

    # Create coordinator
    coordinator = BuderusCoordinator(hass, port, scan_interval, allowlist)

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
    await _async_register_services(hass)

    port = entry.data.get(CONF_SERIAL_DEVICE, DEFAULT_PORT)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allowlist = _normalize_allowlist(
        entry.options.get(CONF_PARAMETER_ALLOWLIST, DEFAULT_PARAMETER_ALLOWLIST)
    )

    _LOGGER.info(
        "Setting up Buderus WPS integration via config entry (port=%s, scan_interval=%d)",
        port,
        scan_interval,
    )

    # Create coordinator
    coordinator = BuderusCoordinator(hass, port, scan_interval, allowlist)

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
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

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
