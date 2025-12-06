"""Switches for Buderus WPS Heat Pump."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the switch platform."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities([
        BuderusEnergyBlockSwitch(coordinator),
        BuderusDHWExtraSwitch(coordinator),
    ])


class BuderusEnergyBlockSwitch(BuderusEntity, SwitchEntity):
    """Switch for energy blocking control."""

    _attr_name = "Energy Block"
    _attr_icon = "mdi:power-plug-off"

    def __init__(self, coordinator: BuderusCoordinator) -> None:
        """Initialize the energy block switch."""
        super().__init__(coordinator, "energy_block")

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


class BuderusDHWExtraSwitch(BuderusEntity, SwitchEntity):
    """Switch for DHW extra production control."""

    _attr_name = "DHW Extra"
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator: BuderusCoordinator) -> None:
        """Initialize the DHW extra switch."""
        super().__init__(coordinator, "dhw_extra")

    @property
    def is_on(self) -> bool | None:
        """Return true if DHW extra production is active."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_extra_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start DHW extra production (default 60 minutes)."""
        await self.coordinator.async_set_dhw_extra(True, duration=60)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop DHW extra production."""
        await self.coordinator.async_set_dhw_extra(False)
        await self.coordinator.async_request_refresh()
