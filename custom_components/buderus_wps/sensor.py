"""Temperature sensors for Buderus WPS Heat Pump."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SENSOR_BRINE_IN,
    SENSOR_BRINE_OUT,
    SENSOR_DHW,
    SENSOR_NAMES,
    SENSOR_OUTDOOR,
    SENSOR_RETURN,
    SENSOR_ROOM_C1,
    SENSOR_ROOM_C2,
    SENSOR_ROOM_C3,
    SENSOR_ROOM_C4,
    SENSOR_SETPOINT_C1,
    SENSOR_SETPOINT_C2,
    SENSOR_SETPOINT_C3,
    SENSOR_SETPOINT_C4,
    SENSOR_SUPPLY,
)
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity

SENSOR_TYPES = [
    SENSOR_OUTDOOR,
    SENSOR_SUPPLY,
    SENSOR_RETURN,
    SENSOR_DHW,
    SENSOR_BRINE_IN,
    SENSOR_BRINE_OUT,
    SENSOR_ROOM_C1,
    SENSOR_ROOM_C2,
    SENSOR_ROOM_C3,
    SENSOR_ROOM_C4,
    SENSOR_SETPOINT_C1,
    SENSOR_SETPOINT_C2,
    SENSOR_SETPOINT_C3,
    SENSOR_SETPOINT_C4,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    sensors: list[SensorEntity] = [
        BuderusTemperatureSensor(coordinator, sensor_type, entry)
        for sensor_type in SENSOR_TYPES
    ]

    allowlist = coordinator.parameter_allowlist
    if allowlist:
        sensors.extend(
            BuderusParameterSensor(coordinator, param_key, entry)
            for param_key in allowlist
        )

    async_add_entities(sensors)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the sensor platform via YAML (legacy)."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    sensors: list[SensorEntity] = [
        BuderusTemperatureSensor(coordinator, sensor_type)
        for sensor_type in SENSOR_TYPES
    ]

    allowlist = coordinator.parameter_allowlist
    if allowlist:
        sensors.extend(
            BuderusParameterSensor(coordinator, param_key)
            for param_key in allowlist
        )

    async_add_entities(sensors)


class BuderusTemperatureSensor(BuderusEntity, SensorEntity):
    """Temperature sensor for Buderus WPS heat pump."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        sensor_type: str,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, f"temp_{sensor_type}", entry)
        self._sensor_type = sensor_type
        self._attr_name = SENSOR_NAMES.get(sensor_type, sensor_type)

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.temperatures.get(self._sensor_type)


def _sanitize_parameter_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value.strip())


class BuderusParameterSensor(BuderusEntity, SensorEntity):
    """Generic parameter sensor for allowlisted parameters."""

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        parameter_key: str,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the parameter sensor."""
        self._parameter_key = str(parameter_key).strip()
        entity_key = f"param_{_sanitize_parameter_key(self._parameter_key)}"
        super().__init__(coordinator, entity_key, entry)
        self._attr_name = f"Parameter {self._parameter_key}"

    @property
    def native_value(self) -> float | int | str | None:
        """Return the parameter value."""
        if self.coordinator.data is None:
            return None
        result = self.coordinator.data.parameter_results.get(self._parameter_key)
        if not result:
            return None
        decoded = result.get("decoded")
        if decoded is None:
            return None
        if isinstance(decoded, (float, int, str)):
            return decoded
        return str(decoded)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose parameter metadata as attributes."""
        attrs = super().extra_state_attributes
        if self.coordinator.data is None:
            return attrs
        result = self.coordinator.data.parameter_results.get(self._parameter_key)
        if not result:
            return attrs
        attrs.update(
            {
                "parameter_key": self._parameter_key,
                "parameter_name": result.get("name"),
                "parameter_index": result.get("idx"),
                "parameter_extid": result.get("extid"),
                "parameter_format": result.get("format"),
                "parameter_min": result.get("min"),
                "parameter_max": result.get("max"),
                "parameter_read": result.get("read"),
                "parameter_raw": result.get("raw"),
                "parameter_error": result.get("error"),
            }
        )
        return attrs
