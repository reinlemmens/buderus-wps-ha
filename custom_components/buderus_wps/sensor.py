"""Temperature sensors for Buderus WPS Heat Pump."""

from __future__ import annotations

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
    SENSOR_DHW,
    SENSOR_NAMES,
    SENSOR_OUTDOOR,
    SENSOR_RETURN,
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
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    sensors = [
        BuderusTemperatureSensor(coordinator, sensor_type, entry)
        for sensor_type in SENSOR_TYPES
    ]

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

    sensors = [
        BuderusTemperatureSensor(coordinator, sensor_type)
        for sensor_type in SENSOR_TYPES
    ]

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
