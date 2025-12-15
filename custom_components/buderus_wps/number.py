"""Number platform for Buderus WPS Heat Pump."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
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
    """Set up Buderus number entities."""
    coordinator = entry.runtime_data
    
    # TODO: Define number entities (e.g., temperature setpoints)
    numbers: list[NumberEntity] = []
    
    async_add_entities(numbers)
