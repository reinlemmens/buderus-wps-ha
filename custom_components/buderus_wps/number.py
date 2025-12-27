"""Number entities for Buderus WPS Heat Pump."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_HEATING_CURVE, ICON_WATER_HEATER, ICON_WATER_THERMOMETER
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    async_add_entities([
        BuderusDHWExtraDurationNumber(coordinator, entry),
        BuderusHeatingCurveOffsetNumber(coordinator, entry),
        BuderusDHWStopTempNumber(coordinator, entry),
    ])


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the number platform via YAML (legacy)."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities([BuderusDHWExtraDurationNumber(coordinator)])


class BuderusDHWExtraDurationNumber(BuderusEntity, NumberEntity):
    """Number entity for DHW extra production duration (0-48 hours)."""

    _attr_name = "DHW Extra Duration"
    _attr_icon = ICON_WATER_HEATER
    _attr_native_min_value = 0
    _attr_native_max_value = 48
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the DHW extra duration number."""
        super().__init__(coordinator, "dhw_extra_duration", entry)

    @property
    def native_value(self) -> int | None:
        """Return the current DHW extra duration in hours."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_extra_duration

    async def async_set_native_value(self, value: float) -> None:
        """Set DHW extra production duration.

        Args:
            value: Duration in hours (0-48). Setting 0 stops production.
        """
        await self.coordinator.async_set_dhw_extra_duration(int(value))
        await self.coordinator.async_request_refresh()


class BuderusHeatingCurveOffsetNumber(BuderusEntity, NumberEntity):
    """Number entity for heating curve parallel offset (-10.0 to +10.0 °C).

    This parameter shifts the entire heating curve up or down.
    Positive values increase supply temperature, negative values decrease it.
    """

    _attr_name = "Heating Curve Offset"
    _attr_icon = ICON_HEATING_CURVE
    _attr_native_min_value = -10.0
    _attr_native_max_value = 10.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the heating curve offset number."""
        super().__init__(coordinator, "heating_curve_offset", entry)

    @property
    def native_value(self) -> float | None:
        """Return the current heating curve offset in °C."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.heating_curve_offset

    async def async_set_native_value(self, value: float) -> None:
        """Set heating curve parallel offset.

        Args:
            value: Offset in °C (-10.0 to +10.0)
        """
        import logging
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.debug("BuderusHeatingCurveOffsetNumber.async_set_native_value called with value=%.1f", value)
        try:
            await self.coordinator.async_set_heating_curve_offset(value)
            # Optimistically update coordinator data for immediate UI feedback
            # The next scheduled refresh will confirm the actual value
            if self.coordinator.data is not None:
                from dataclasses import replace
                self.coordinator.async_set_updated_data(
                    replace(self.coordinator.data, heating_curve_offset=value)
                )
            _LOGGER.debug("BuderusHeatingCurveOffsetNumber.async_set_native_value completed")
        except Exception as err:
            _LOGGER.error("BuderusHeatingCurveOffsetNumber.async_set_native_value FAILED: %s", err)
            raise


class BuderusDHWStopTempNumber(BuderusEntity, NumberEntity):
    """Number entity for DHW stop charging temperature (50-65°C).

    This parameter controls when DHW tank heating stops.
    Higher values mean more stored hot water but higher energy use.
    """

    _attr_name = "DHW Stop Temperature"
    _attr_icon = ICON_WATER_THERMOMETER
    _attr_native_min_value = 50.0
    _attr_native_max_value = 65.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the DHW stop temperature number."""
        super().__init__(coordinator, "dhw_stop_temp", entry)

    @property
    def native_value(self) -> float | None:
        """Return the current DHW stop temperature in °C."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_stop_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set DHW stop charging temperature.

        Args:
            value: Temperature in °C (50.0 to 65.0)
        """
        import logging
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.debug("BuderusDHWStopTempNumber.async_set_native_value called with value=%.1f", value)
        try:
            await self.coordinator.async_set_dhw_stop_temp(value)
            # Optimistically update coordinator data for immediate UI feedback
            # The next scheduled refresh will confirm the actual value
            if self.coordinator.data is not None:
                from dataclasses import replace
                self.coordinator.async_set_updated_data(
                    replace(self.coordinator.data, dhw_stop_temp=value)
                )
            _LOGGER.debug("BuderusDHWStopTempNumber.async_set_native_value completed")
        except Exception as err:
            _LOGGER.error("BuderusDHWStopTempNumber.async_set_native_value FAILED: %s", err)
            raise
