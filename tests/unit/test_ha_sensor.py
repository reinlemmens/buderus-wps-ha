"""Unit tests for Home Assistant temperature sensor entities."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.const import (
    SENSOR_OUTDOOR,
    SENSOR_SUPPLY,
    SENSOR_RETURN,
    SENSOR_DHW,
    SENSOR_BRINE_IN,
    SENSOR_NAMES,
)


class TestSensorConstants:
    """Test sensor constant definitions."""

    def test_sensor_names_have_heat_pump_prefix(self):
        """All sensor names must be prefixed with 'Heat Pump'."""
        for sensor_type, name in SENSOR_NAMES.items():
            assert name.startswith("Heat Pump "), (
                f"Sensor name '{name}' for type '{sensor_type}' "
                "must start with 'Heat Pump '"
            )

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
        """Outdoor sensor must have correct prefixed name."""
        assert SENSOR_NAMES[SENSOR_OUTDOOR] == "Heat Pump Outdoor Temperature"

    def test_supply_sensor_name(self):
        """Supply sensor must have correct prefixed name."""
        assert SENSOR_NAMES[SENSOR_SUPPLY] == "Heat Pump Supply Temperature"

    def test_return_sensor_name(self):
        """Return sensor must have correct prefixed name."""
        assert SENSOR_NAMES[SENSOR_RETURN] == "Heat Pump Return Temperature"

    def test_dhw_sensor_name(self):
        """DHW sensor must have correct prefixed name."""
        assert SENSOR_NAMES[SENSOR_DHW] == "Heat Pump Hot Water Temperature"

    def test_brine_sensor_name(self):
        """Brine inlet sensor must have correct prefixed name."""
        assert SENSOR_NAMES[SENSOR_BRINE_IN] == "Heat Pump Brine Inlet Temperature"
