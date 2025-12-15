"""Sensor platform for Buderus WPS Heat Pump."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up Buderus sensor entities."""
    coordinator = entry.runtime_data
    
    # Define sensors to create
    # TODO: Expand this list based on available parameters
    sensors = [
        BuderusSensor(
            coordinator,
            "example_sensor",
            "Example Sensor",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
        ),
    ]
    
    async_add_entities(sensors)


class BuderusSensor(CoordinatorEntity[BuderusDataUpdateCoordinator], SensorEntity):
    """Representation of a Buderus WPS sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: BuderusDataUpdateCoordinator,
        sensor_id: str,
        name: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor_id = sensor_id
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        
        # Set unique ID
        self._attr_unique_id = f"{coordinator._port}_{sensor_id}"
        
        # Device info for grouping entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator._port)},
            "name": "Buderus WPS Heat Pump",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        # TODO: Get actual value from coordinator data
        # For now, return None
        return self.coordinator.data.get(self._sensor_id)
