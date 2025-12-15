"""Base entity for Buderus WPS Heat Pump integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_HEAT_PUMP, MANUFACTURER, MODEL
from .coordinator import BuderusCoordinator


class BuderusEntity(CoordinatorEntity[BuderusCoordinator]):
    """Base class for Buderus WPS entities."""

    _attr_has_entity_name = True
    _attr_icon = ICON_HEAT_PUMP  # Default icon for all entities

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entity_key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.port}_{entity_key}"
        self.entity_key = entity_key

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.port)},
            name="Heat Pump",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version="0.1.0",
        )
