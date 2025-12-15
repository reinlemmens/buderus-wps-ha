"""Binary sensors for Buderus WPS Heat Pump."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the binary sensor platform."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities(
        [
            BuderusCompressorSensor(coordinator),
        ]
    )


class BuderusCompressorSensor(BuderusEntity, BinarySensorEntity):
    """Binary sensor for compressor running status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_name = "Compressor"

    def __init__(self, coordinator: BuderusCoordinator) -> None:
        """Initialize the compressor sensor."""
        super().__init__(coordinator, "compressor_running")

    @property
    def is_on(self) -> bool | None:
        """Return true if the compressor is running."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.compressor_running
