"""Integration tests for temperature sensor data flow."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import (
    DOMAIN,
    SENSOR_OUTDOOR,
    SENSOR_SUPPLY,
    SENSOR_RETURN,
    SENSOR_DHW,
    SENSOR_BRINE_IN,
    SENSOR_NAMES,
)
from custom_components.buderus_wps.sensor import (
    async_setup_platform,
    BuderusTemperatureSensor,
)
from tests.conftest import MockBuderusData


class TestTemperatureSensorDataFlow:
    """Test temperature data flows correctly from coordinator to sensors."""

    @pytest.mark.asyncio
    async def test_sensors_created_from_coordinator(self, mock_hass, mock_coordinator):
        """All 5 temperature sensors should be created from coordinator data."""
        entities_added = []

        def capture_entities(entities):
            entities_added.extend(entities)

        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            capture_entities,
            discovery_info={"platform": "buderus_wps"},
        )

        assert len(entities_added) == 5
        sensor_types = {s._sensor_type for s in entities_added}
        assert sensor_types == {
            SENSOR_OUTDOOR,
            SENSOR_SUPPLY,
            SENSOR_RETURN,
            SENSOR_DHW,
            SENSOR_BRINE_IN,
        }

    @pytest.mark.asyncio
    async def test_no_sensors_without_discovery_info(self, mock_hass, mock_coordinator):
        """No sensors created when discovery_info is None."""
        entities_added = []

        def capture_entities(entities):
            entities_added.extend(entities)

        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            capture_entities,
            discovery_info=None,
        )

        assert len(entities_added) == 0

    @pytest.mark.asyncio
    async def test_sensor_values_reflect_coordinator_data(
        self, mock_hass, mock_coordinator
    ):
        """Sensor values must match coordinator temperature data."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        expected_temps = mock_coordinator.data.temperatures

        for sensor in entities_added:
            sensor_type = sensor._sensor_type
            assert sensor.native_value == expected_temps[sensor_type], (
                f"Sensor {sensor_type} value mismatch"
            )

    @pytest.mark.asyncio
    async def test_sensor_updates_when_coordinator_data_changes(
        self, mock_hass, mock_coordinator
    ):
        """Sensors must reflect updated coordinator data."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        # Get outdoor sensor
        outdoor_sensor = next(
            s for s in entities_added if s._sensor_type == SENSOR_OUTDOOR
        )

        # Initial value
        assert outdoor_sensor.native_value == 5.5

        # Simulate coordinator data update
        mock_coordinator.data = MockBuderusData(
            temperatures={
                "outdoor": 10.0,
                "supply": 35.0,
                "return_temp": 30.0,
                "dhw": 48.5,
                "brine_in": 8.0,
            },
            compressor_running=True,
            energy_blocked=False,
            dhw_extra_duration=0,
        )

        # Sensor should now reflect new value
        assert outdoor_sensor.native_value == 10.0


class TestTemperatureSensorNames:
    """Test temperature sensors have correct prefixed names."""

    @pytest.mark.asyncio
    async def test_all_sensors_have_heat_pump_prefix(
        self, mock_hass, mock_coordinator
    ):
        """All temperature sensors must have 'Heat Pump' prefix in name."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        for sensor in entities_added:
            assert sensor.name.startswith("Heat Pump "), (
                f"Sensor name '{sensor.name}' must start with 'Heat Pump '"
            )

    @pytest.mark.asyncio
    async def test_sensors_have_expected_full_names(
        self, mock_hass, mock_coordinator
    ):
        """Sensors must have expected full names with Heat Pump prefix."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        expected_names = {
            SENSOR_OUTDOOR: "Heat Pump Outdoor Temperature",
            SENSOR_SUPPLY: "Heat Pump Supply Temperature",
            SENSOR_RETURN: "Heat Pump Return Temperature",
            SENSOR_DHW: "Heat Pump Hot Water Temperature",
            SENSOR_BRINE_IN: "Heat Pump Brine Inlet Temperature",
        }

        for sensor in entities_added:
            expected = expected_names[sensor._sensor_type]
            assert sensor.name == expected, (
                f"Sensor {sensor._sensor_type} name should be '{expected}', "
                f"got '{sensor.name}'"
            )
