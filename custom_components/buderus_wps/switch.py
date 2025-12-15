"""Switches for Buderus WPS Heat Pump."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_ENERGY_BLOCK
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    async_add_entities([BuderusEnergyBlockSwitch(coordinator, entry)])


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
        """Return true if energy blocking is enabled."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.energy_blocked

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable energy blocking."""
        await self.coordinator.async_set_energy_blocking(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable energy blocking."""
        await self.coordinator.async_set_energy_blocking(False)
        await self.coordinator.async_request_refresh()
