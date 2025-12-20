"""Unit tests for Home Assistant temperature sensor entities."""

from __future__ import annotations

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.const import (
    SENSOR_BRINE_IN,
    SENSOR_DHW,
    SENSOR_NAMES,
    SENSOR_OUTDOOR,
    SENSOR_RETURN,
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

    def test_five_sensors_defined(self):
        """Must have exactly 5 temperature sensors defined."""
        expected_sensors = {
            SENSOR_OUTDOOR,
            SENSOR_SUPPLY,
            SENSOR_RETURN,
            SENSOR_DHW,
            SENSOR_BRINE_IN,
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

    def test_brine_sensor_name(self):
        """Brine inlet sensor must have correct entity name."""
        assert SENSOR_NAMES[SENSOR_BRINE_IN] == "Brine Inlet Temperature"
