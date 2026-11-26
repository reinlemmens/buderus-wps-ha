"""Binary sensors for Buderus WPS Heat Pump."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .buderus_wps.alarm_status import alarm_pending
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

    async_add_entities(
        [
            BuderusCompressorSensor(coordinator, entry),
            BuderusDHWActiveSensor(coordinator, entry),
            BuderusHeatingActiveSensor(coordinator, entry),
            BuderusAlarmPendingSensor(coordinator, entry),
        ]
    )


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
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes including debug compressor signals."""
        attrs = super().extra_state_attributes
        if self.coordinator.data is None:
            return attrs
        attrs["compressor_state"] = self.coordinator.data.compressor_state
        attrs["compressor_frequency_hz"] = self.coordinator.data.compressor_frequency
        return attrs

    @property
    def is_on(self) -> bool | None:
        """Return true if the compressor is running."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.compressor_running


class BuderusDHWActiveSensor(BuderusEntity, BinarySensorEntity):
    """Binary sensor for DHW generation status (Pump DHW)."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_name = "DHW Active"
    _attr_icon = "mdi:water-boiler"

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "dhw_active", entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if DHW pump is running."""
        if self.coordinator.data is None or not hasattr(
            self.coordinator.data, "dhw_active"
        ):
            return None
        return self.coordinator.data.dhw_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {
            "description": "Indicates if the DHW charging pump is active (heating hot water)."
        }


class BuderusHeatingActiveSensor(BuderusEntity, BinarySensorEntity):
    """Binary sensor for Heating Circuit 1 status (Pump G1)."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_name = "Heating Active"
    _attr_icon = "mdi:radiator"

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "heating_active", entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if G1 pump is running (heating)."""
        if self.coordinator.data is None or not hasattr(
            self.coordinator.data, "g1_active"
        ):
            return None
        return self.coordinator.data.g1_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {"description": "Indicates if the main heating pump (G1) is active."}


class BuderusAlarmPendingSensor(BuderusEntity, BinarySensorEntity):
    """On while the heat pump has unconfirmed alarms on its panel (issue #25).

    The pump does not put the alarm text or time on the CAN bus; it only
    reports whether unconfirmed alarm popups exist (RTU800B_SYSTEM_STATUS = 4).
    A status value of unknown meaning shows as unknown rather than as a guess.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Alarm Pending"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "alarm_pending", entry)

    @property
    def is_on(self) -> bool | None:
        """Return true if an unconfirmed alarm is pending."""
        if self.coordinator.data is None:
            return None
        return alarm_pending(self.coordinator.data.system_status)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw status value next to the staleness attributes."""
        attrs = super().extra_state_attributes
        if self.coordinator.data is not None:
            attrs["system_status"] = self.coordinator.data.system_status
        return attrs
