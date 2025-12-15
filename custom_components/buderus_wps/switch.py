"""Switch platform for Buderus WPS Heat Pump."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BuderusConfigEntry
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import BuderusDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BuderusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Buderus switch entities."""
    coordinator = entry.runtime_data
    
    # TODO: Define switch entities (e.g., holiday mode, manual DHW)
    switches: list[SwitchEntity] = []
    
    async_add_entities(switches)
