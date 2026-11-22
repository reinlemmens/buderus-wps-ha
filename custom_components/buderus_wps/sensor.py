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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .buderus_wps.mixed_circuit import (
    MIXED_CIRCUITS,
    VALUE_ROOM_SENSOR,
    VALUE_ROOM_TEMP_USED,
    VALUE_SUPPLY_TARGET,
)
from .buderus_wps.room_thermostat import ROOM_SETPOINT_CIRCUITS
from .const import (
    DOMAIN,
    MIXED_CIRCUIT_CONTEXT,
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
    sensors.extend(
        BuderusRoomSetpointSensor(coordinator, circuit, entry)
        for circuit in sorted(ROOM_SETPOINT_CIRCUITS)
    )
    sensors.append(BuderusDHWStopTempActiveSensor(coordinator, entry))
    sensors.extend(
        BuderusMixedCircuitSensor(coordinator, circuit, key, entry)
        for circuit in sorted(MIXED_CIRCUITS)
        for key in MIXED_CIRCUIT_SENSORS
    )

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
    sensors.extend(
        BuderusRoomSetpointSensor(coordinator, circuit)
        for circuit in sorted(ROOM_SETPOINT_CIRCUITS)
    )
    sensors.append(BuderusDHWStopTempActiveSensor(coordinator))

    allowlist = coordinator.parameter_allowlist
    if allowlist:
        sensors.extend(
            BuderusParameterSensor(coordinator, param_key) for param_key in allowlist
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


class BuderusRoomSetpointSensor(BuderusEntity, SensorEntity):
    """Room setpoint a heating circuit currently runs on (read-only).

    Reads the pump's MV_T5_SETPOINT_ACTUAL_n copy, the same value the room
    setpoint number entity shows, so it follows both thermostat changes and
    HA writes. Created only for circuits in ROOM_SETPOINT_CIRCUITS, where
    that source is hardware-verified.

    Keeps the ``temp_setpoint_cN`` unique ID of the old broadcast-based
    sensor, which read idx 33 on bases 0x0060-0x0063. That value tracks room
    temperature + ~1.4 K and never followed the thermostat (#19).
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        circuit: int,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the room setpoint sensor for one circuit."""
        super().__init__(coordinator, f"temp_setpoint_c{circuit}", entry)
        self.circuit = circuit
        self._attr_name = f"Room Setpoint C{circuit}"

    @property
    def native_value(self) -> float | None:
        """Return the active room setpoint in °C."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.room_setpoint_active.get(self.circuit)


class BuderusDHWStopTempActiveSensor(BuderusEntity, SensorEntity):
    """Active DHW stop temperature (GT8, idx 444), read-only.

    The register the charge actually terminates on in DHW_PROGRAM_MODE=1
    ("Always On"). It carries no write bounds in the FHEM reference and is
    not writable, so it is exposed as a sensor: compare it against the
    "DHW Stop Temperature Limit" number (idx 440) to see where a charge
    will stop (issue #13).
    """

    _attr_name = "DHW Stop Temperature (Active)"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the active DHW stop temperature sensor."""
        super().__init__(coordinator, "dhw_stop_temp_active", entry)

    @property
    def native_value(self) -> float | None:
        """Return the active DHW stop temperature in °C."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.dhw_gt8_stop_temp


# value key -> (entity key prefix, display name prefix)
MIXED_CIRCUIT_SENSORS: dict[str, tuple[str, str]] = {
    VALUE_ROOM_TEMP_USED: ("room_temp_used", "Room Temperature Used By Pump"),
    VALUE_ROOM_SENSOR: ("room_sensor_value", "Room Sensor Value"),
    VALUE_SUPPLY_TARGET: ("supply_target", "Supply Temperature Target"),
}


class BuderusMixedCircuitSensor(BuderusEntity, SensorEntity):
    """Diagnostic temperature for one mixed circuit (C2-C4), off by default.

    - Room Temperature Used By Pump (MV_T5_ATTENUATED_n): stuck at exactly
      20.0 while the room thermostat reads otherwise means the pump is not
      using the room sensor (see the Room Sensor Acknowledged switch).
    - Room Sensor Value (MV_T5_ACTUAL_n): unavailable when the pump reports
      0xDEAD.
    - Supply Temperature Target (MV_T1_SETPOINT_n).

    The coordinator polls a parameter only while its entity is enabled (#22).
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: BuderusCoordinator,
        circuit: int,
        value_key: str,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the diagnostic sensor."""
        key_prefix, name_prefix = MIXED_CIRCUIT_SENSORS[value_key]
        super().__init__(
            coordinator,
            f"{key_prefix}_c{circuit}",
            entry,
            context=(MIXED_CIRCUIT_CONTEXT, circuit, value_key),
        )
        self.circuit = circuit
        self.value_key = value_key
        self._attr_name = f"{name_prefix} C{circuit}"

    def _value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.mixed_circuit_values.get(self.circuit, {}).get(
            self.value_key
        )

    @property
    def available(self) -> bool:
        """Room Sensor Value is unavailable while the pump reports 0xDEAD."""
        if self.value_key == VALUE_ROOM_SENSOR:
            data = self.coordinator.data
            if (
                data is not None
                and self.value_key in data.mixed_circuit_values.get(self.circuit, {})
                and self._value() is None
            ):
                return False
        return bool(super().available)

    @property
    def native_value(self) -> float | None:
        """Return the temperature in °C."""
        return self._value()


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
