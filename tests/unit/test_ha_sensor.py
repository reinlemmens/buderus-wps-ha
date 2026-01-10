"""Unit tests for Home Assistant temperature sensor entities."""

from __future__ import annotations

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.const import (
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


class TestSensorConstants:
    """Test sensor constant definitions."""

    def test_sensor_names_have_descriptive_values(self):
        """All sensor names are descriptive entity-only names."""
        # With has_entity_name=True, these are entity names (not full display names)
        # Home Assistant automatically prepends device name "Heat Pump" in UI
        for sensor_type, name in SENSOR_NAMES.items():
            assert (
                len(name) > 0
            ), f"Sensor name for type '{sensor_type}' must not be empty"
            assert isinstance(
                name, str
            ), f"Sensor name for type '{sensor_type}' must be a string"

    def test_all_sensors_defined(self):
        """Must have all temperature sensors defined (6 core + 4 room + 4 setpoint)."""
        expected_sensors = {
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
        }
        assert set(SENSOR_NAMES.keys()) == expected_sensors

    def test_outdoor_sensor_name(self):
        """Outdoor sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_OUTDOOR] == "Outdoor Temperature"

    def test_supply_sensor_name(self):
        """Supply sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_SUPPLY] == "Supply Temperature"

    def test_return_sensor_name(self):
        """Return sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_RETURN] == "Return Temperature"

    def test_dhw_sensor_name(self):
        """DHW sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_DHW] == "Hot Water Temperature"

    def test_brine_in_sensor_name(self):
        """Brine inlet sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_BRINE_IN] == "GT10 Brine Inlet"

    def test_brine_out_sensor_name(self):
        """Brine outlet sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_BRINE_OUT] == "GT11 Brine Outlet"
