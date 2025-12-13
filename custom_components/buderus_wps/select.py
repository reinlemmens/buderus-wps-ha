"""Select entities for Buderus WPS Heat Pump.

These select entities provide control over heating and DHW modes,
enabling peak hour blocking via automation.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HEATING_SEASON_OPTIONS,
    DHW_PROGRAM_OPTIONS,
)
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the select platform."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities([
        BuderusHeatingSeasonModeSelect(coordinator),
        BuderusDHWProgramModeSelect(coordinator),
    ])


class BuderusHeatingSeasonModeSelect(BuderusEntity, SelectEntity):
    """Select entity for heating season mode.

    Used for peak hour blocking:
    - Set to "Off (Summer)" to disable heating during peak electricity rates
    - Set to "Automatic" for normal operation
    - Set to "Winter (Forced)" to force heating regardless of outdoor temp

    Hardware-verified parameter: HEATING_SEASON_MODE (idx=884)
    """

    _attr_name = "Heat Pump Heating Season Mode"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: BuderusCoordinator) -> None:
        """Initialize the heating season mode select."""
        super().__init__(coordinator, "heating_season_mode")
        self._attr_options = list(HEATING_SEASON_OPTIONS.values())
        self._value_to_option = HEATING_SEASON_OPTIONS
        self._option_to_value = {v: k for k, v in HEATING_SEASON_OPTIONS.items()}

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.heating_season_mode
        if mode is None:
            return None
        return self._value_to_option.get(mode)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self._option_to_value.get(option)
        if value is not None:
            await self.coordinator.async_set_heating_season_mode(value)
            await self.coordinator.async_request_refresh()


class BuderusDHWProgramModeSelect(BuderusEntity, SelectEntity):
    """Select entity for DHW (hot water) program mode.

    Used for peak hour blocking:
    - Set to "Always Off" to disable DHW heating during peak electricity rates
    - Set to "Automatic" for normal operation (follows time program)
    - Set to "Always On" to force DHW heating

    Hardware-verified parameter: DHW_PROGRAM_MODE (idx=489)
    """

    _attr_name = "Heat Pump DHW Program Mode"
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator: BuderusCoordinator) -> None:
        """Initialize the DHW program mode select."""
        super().__init__(coordinator, "dhw_program_mode")
        self._attr_options = list(DHW_PROGRAM_OPTIONS.values())
        self._value_to_option = DHW_PROGRAM_OPTIONS
        self._option_to_value = {v: k for k, v in DHW_PROGRAM_OPTIONS.items()}

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.dhw_program_mode
        if mode is None:
            return None
        return self._value_to_option.get(mode)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self._option_to_value.get(option)
        if value is not None:
            await self.coordinator.async_set_dhw_program_mode(value)
            await self.coordinator.async_request_refresh()
