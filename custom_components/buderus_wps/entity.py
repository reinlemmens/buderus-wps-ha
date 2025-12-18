"""Base entity for Buderus WPS Heat Pump integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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
            sw_version="1.3.3",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity state attributes including staleness indicators.

        Per FR-005: All entities expose staleness metadata from coordinator.
        Attributes include:
        - last_update_age_seconds: Age in seconds since last successful update
        - data_is_stale: Boolean indicating if data is from cache (connection issues)
        - last_successful_update: ISO 8601 timestamp of last successful update
        """
        attrs: dict[str, Any] = {}

        # Get data age from coordinator
        age = self.coordinator.get_data_age_seconds()
        if age is not None:
            attrs["last_update_age_seconds"] = age
            attrs["data_is_stale"] = self.coordinator.is_data_stale()

        # Add timestamp if available
        if self.coordinator._last_successful_update:
            attrs["last_successful_update"] = datetime.fromtimestamp(
                self.coordinator._last_successful_update
            ).isoformat()

        return attrs
