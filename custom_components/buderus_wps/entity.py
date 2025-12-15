"""Base entity for Buderus WPS Heat Pump integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
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
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        # Use entry_id for config entry setup, fall back to port for YAML setup
        if entry is not None:
            unique_prefix = entry.entry_id
        else:
            unique_prefix = coordinator.port

        self._attr_unique_id = f"{unique_prefix}_{entity_key}"
        self.entity_key = entity_key

        # Set device_info as attribute for proper device registration
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_prefix)},
            name="Heat Pump",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version="1.0.0",
        )
