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

    async_add_entities(
        [
            BuderusDHWExtraDurationNumber(coordinator, entry),
            BuderusHeatingCurveOffsetNumber(coordinator, entry),
            BuderusDHWStopTempNumber(coordinator, entry),
            BuderusDHWSetpointNumber(coordinator, entry),
            BuderusDHWStartTempComfortNumber(coordinator, entry),
            BuderusDHWStartTempEconomyNumber(coordinator, entry),
            BuderusDHWStopTempComfortNumber(coordinator, entry),
            BuderusDHWStopTempEconomyNumber(coordinator, entry),
            BuderusDHWStopMaxTempNumber(coordinator, entry),
            BuderusDHWStartTempActiveNumber(coordinator, entry),
        ]
    )


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
        _LOGGER.debug(
            "BuderusHeatingCurveOffsetNumber.async_set_native_value called with value=%.1f",
            value,
        )
        try:
            await self.coordinator.async_set_heating_curve_offset(value)
            # Optimistically update coordinator data for immediate UI feedback
            # The next scheduled refresh will confirm the actual value
            if self.coordinator.data is not None:
                from dataclasses import replace

                self.coordinator.async_set_updated_data(
                    replace(self.coordinator.data, heating_curve_offset=value)
                )
            _LOGGER.debug(
                "BuderusHeatingCurveOffsetNumber.async_set_native_value completed"
            )
        except Exception as err:
            _LOGGER.error(
                "BuderusHeatingCurveOffsetNumber.async_set_native_value FAILED: %s", err
            )
            raise


class BuderusDHWStopTempNumber(BuderusEntity, NumberEntity):
    """Number entity for DHW stop charging temperature (50-65°C).

    This parameter controls when DHW tank heating stops.
    Higher values mean more stored hot water but higher energy use.
    """

    _attr_name = "XDHW Stop Temperature"
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
        super().__init__(coordinator, "xdhw_stop_temp", entry)

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
        _LOGGER.debug(
            "BuderusDHWStopTempNumber.async_set_native_value called with value=%.1f",
            value,
        )
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
            _LOGGER.error(
                "BuderusDHWStopTempNumber.async_set_native_value FAILED: %s", err
            )
            raise


class BuderusDHWSetpointNumber(BuderusEntity, NumberEntity):
    """Number entity for DHW setpoint temperature (40-70°C).

    This parameter controls the target temperature for normal DHW operation.
    Distinct from DHW Stop Temperature which is for boost/extra mode.
    """

    _attr_name = "DHW Setpoint Temperature"
    _attr_icon = ICON_WATER_THERMOMETER
    _attr_native_min_value = 40.0
    _attr_native_max_value = 70.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the DHW setpoint temperature number."""
        super().__init__(coordinator, "dhw_setpoint", entry)

    @property
    def native_value(self) -> float | None:
        """Return the current DHW setpoint in °C."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_setpoint

    async def async_set_native_value(self, value: float) -> None:
        """Set DHW setpoint temperature.

        Args:
            value: Temperature in °C (40.0 to 70.0)
        """
        import logging

        _LOGGER = logging.getLogger(__name__)
        _LOGGER.debug("DHWSetpoint.async_set_native_value: %.1f", value)
        try:
            await self.coordinator.async_set_dhw_setpoint(value)
            # Optimistically update coordinator data for immediate UI feedback
            # The next scheduled refresh will confirm the actual value
            if self.coordinator.data is not None:
                from dataclasses import replace

                self.coordinator.async_set_updated_data(
                    replace(self.coordinator.data, dhw_setpoint=value)
                )
            _LOGGER.debug("DHWSetpoint.async_set_native_value completed")
        except Exception as err:
            _LOGGER.error("DHWSetpoint.async_set_native_value FAILED: %s", err)
            raise


class _BuderusDHWModeTempNumberBase(BuderusEntity, NumberEntity):
    """Base for DHW Comfort/Economy start/stop temperature number entities.

    Subclasses set: _attr_name, entity_key, _data_attr, _setter_name,
    _attr_native_min_value, _attr_native_max_value.
    """

    _attr_icon = ICON_WATER_THERMOMETER
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    # Subclasses must override:
    _entity_key: str = ""
    _data_attr: str = ""
    _setter_name: str = ""

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(coordinator, self._entity_key, entry)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, self._data_attr, None)

    async def async_set_native_value(self, value: float) -> None:
        setter = getattr(self.coordinator, self._setter_name)
        await setter(value)
        # Optimistic update for immediate UI feedback
        if self.coordinator.data is not None:
            from dataclasses import replace

            self.coordinator.async_set_updated_data(
                replace(self.coordinator.data, **{self._data_attr: value})
            )


class BuderusDHWStartTempComfortNumber(_BuderusDHWModeTempNumberBase):
    """DHW start temperature (GT3) used in Comfort mode (20.0-56.0°C).

    Hot water heating begins when GT3 drops below this value while the DHW
    schedule is in its Comfort window.
    """

    _attr_name = "DHW Start Temperature (Comfort)"
    _attr_native_min_value = 20.0
    _attr_native_max_value = 56.0
    _entity_key = "dhw_start_temp_comfort"
    _data_attr = "dhw_start_temp_comfort"
    _setter_name = "async_set_dhw_start_temp_comfort"


class BuderusDHWStartTempEconomyNumber(_BuderusDHWModeTempNumberBase):
    """DHW start temperature (GT3) used in Economy mode (20.0-56.0°C).

    Lower value than Comfort means the tank is allowed to cool further before
    a new heating cycle, reducing energy use.
    """

    _attr_name = "DHW Start Temperature (Economy)"
    _attr_native_min_value = 20.0
    _attr_native_max_value = 56.0
    _entity_key = "dhw_start_temp_economy"
    _data_attr = "dhw_start_temp_economy"
    _setter_name = "async_set_dhw_start_temp_economy"


class BuderusDHWStopTempComfortNumber(_BuderusDHWModeTempNumberBase):
    """DHW stop temperature (GT8) used in Comfort mode (21.0-64.0°C).

    Hot water heating stops when GT8 reaches this value during the
    Comfort window. Higher value = hotter water but more energy.
    """

    _attr_name = "DHW Stop Temperature (Comfort)"
    _attr_native_min_value = 21.0
    _attr_native_max_value = 64.0
    _entity_key = "dhw_stop_temp_comfort"
    _data_attr = "dhw_stop_temp_comfort"
    _setter_name = "async_set_dhw_stop_temp_comfort"


class BuderusDHWStopTempEconomyNumber(_BuderusDHWModeTempNumberBase):
    """DHW stop temperature (GT8) used in Economy mode (21.0-64.0°C)."""

    _attr_name = "DHW Stop Temperature (Economy)"
    _attr_native_min_value = 21.0
    _attr_native_max_value = 64.0
    _entity_key = "dhw_stop_temp_economy"
    _data_attr = "dhw_stop_temp_economy"
    _setter_name = "async_set_dhw_stop_temp_economy"


class BuderusDHWStopMaxTempNumber(_BuderusDHWModeTempNumberBase):
    """DHW stop temperature ceiling (GT8, idx 440) (20.0-64.0°C).

    In DHW_PROGRAM_MODE=1 ("Always On") the charge terminates on
    DHW_GT8_STOP_TEMP (idx 444), not on the Comfort/Economy profile
    registers. Idx 444 carries no write bounds in the FHEM reference and
    is read-only, so this ceiling is the writable control over where a
    charge stops; the active value is exposed as a sensor for comparison.
    """

    _attr_name = "DHW Stop Temperature Limit"
    _attr_native_min_value = 20.0
    _attr_native_max_value = 64.0
    _entity_key = "dhw_gt8_stop_max_temp"
    _data_attr = "dhw_gt8_stop_max_temp"
    _setter_name = "async_set_dhw_gt8_stop_max_temp"


class BuderusDHWStartTempActiveNumber(_BuderusDHWModeTempNumberBase):
    """Active DHW start temperature (DHW_USER_SET_START_TEMP, idx 498).

    Paired with the active stop temperature: a new charge begins when the
    tank drops below this value in "Always On" mode (20.0-79.0°C per the
    parameter table).
    """

    _attr_name = "DHW Start Temperature (Active)"
    _attr_native_min_value = 20.0
    _attr_native_max_value = 79.0
    _entity_key = "dhw_user_start_temp"
    _data_attr = "dhw_user_start_temp"
    _setter_name = "async_set_dhw_user_start_temp"
