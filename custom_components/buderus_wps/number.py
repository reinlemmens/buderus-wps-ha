"""Number entities for Buderus WPS Heat Pump."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_WATER_HEATER
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the number platform."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities(
        [
            BuderusDHWExtraDurationNumber(coordinator),
        ]
    )


class BuderusDHWExtraDurationNumber(BuderusEntity, NumberEntity):
    """Number entity for DHW extra production duration (0-24 hours)."""

    _attr_name = "DHW Extra Duration"
    _attr_icon = ICON_WATER_HEATER
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: BuderusCoordinator) -> None:
        """Initialize the DHW extra duration number."""
        super().__init__(coordinator, "dhw_extra_duration")

    @property
    def native_value(self) -> int | None:
        """Return the current DHW extra duration in hours."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_extra_duration

    async def async_set_native_value(self, value: float) -> None:
        """Set DHW extra production duration.

        Args:
            value: Duration in hours (0-24). Setting 0 stops production.
        """
        await self.coordinator.async_set_dhw_extra_duration(int(value))
        await self.coordinator.async_request_refresh()
