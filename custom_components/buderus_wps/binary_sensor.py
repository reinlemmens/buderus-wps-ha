"""Binary sensors for Buderus WPS Heat Pump."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_COMPRESSOR
from .coordinator import BuderusCoordinator
from .entity import BuderusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BuderusCoordinator = data["coordinator"]

    async_add_entities([BuderusCompressorSensor(coordinator, entry)])


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the binary sensor platform via YAML (legacy)."""
    if discovery_info is None:
        return

    coordinator: BuderusCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities([BuderusCompressorSensor(coordinator)])


class BuderusCompressorSensor(BuderusEntity, BinarySensorEntity):
    """Binary sensor for compressor running status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = ICON_COMPRESSOR
    _attr_name = "Compressor"

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the compressor sensor."""
        super().__init__(coordinator, "compressor_running", entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if the compressor is running."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.compressor_running
