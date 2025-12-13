"""Acceptance tests for User Story 1: Monitor Heat Pump Temperatures.

User Story:
As a homeowner, I want to see my heat pump's temperature readings in Home Assistant
so that I can monitor system performance and detect issues without leaving my dashboard.

Acceptance Scenarios:
1. Given the integration is configured, When HA starts, Then 5 temperature sensors appear
2. Given the heat pump is operating, When I view sensors, Then I see Celsius values
3. Given the serial connection is lost, When HA polls, Then sensors show unavailable
"""

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


class TestUS1Scenario1FiveSensorsAppear:
    """Scenario 1: 5 temperature sensors appear on startup."""

    @pytest.mark.asyncio
    async def test_five_temperature_sensors_created(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the integration is configured with the correct serial port
        When Home Assistant starts
        Then five temperature sensors appear: Outdoor, Supply, Return, DHW, Brine Inlet
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        # Exactly 5 sensors
        assert len(entities_added) == 5, (
            f"Expected 5 temperature sensors, got {len(entities_added)}"
        )

        # All expected sensor types present
        sensor_types = {s._sensor_type for s in entities_added}
        expected_types = {
            SENSOR_OUTDOOR,
            SENSOR_SUPPLY,
            SENSOR_RETURN,
            SENSOR_DHW,
            SENSOR_BRINE_IN,
        }
        assert sensor_types == expected_types

    @pytest.mark.asyncio
    async def test_sensors_have_correct_names(
        self, mock_hass, mock_coordinator
    ):
        """
        Sensors must have descriptive names with Heat Pump prefix:
        - Heat Pump Outdoor Temperature
        - Heat Pump Supply Temperature
        - Heat Pump Return Temperature
        - Heat Pump Hot Water Temperature
        - Heat Pump Brine Inlet Temperature
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        expected_names = {
            "Heat Pump Outdoor Temperature",
            "Heat Pump Supply Temperature",
            "Heat Pump Return Temperature",
            "Heat Pump Hot Water Temperature",
            "Heat Pump Brine Inlet Temperature",
        }

        actual_names = {s.name for s in entities_added}
        assert actual_names == expected_names, (
            f"Expected names: {expected_names}\n"
            f"Actual names: {actual_names}"
        )


class TestUS1Scenario2CelsiusValues:
    """Scenario 2: Sensors show temperature values in Celsius."""

    @pytest.mark.asyncio
    async def test_sensors_have_temperature_device_class(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the heat pump is operating normally
        When I view the sensors in Home Assistant
        Then sensors have correct device_class for temperature
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        for sensor in entities_added:
            assert sensor._attr_device_class == "temperature"

    @pytest.mark.asyncio
    async def test_sensors_use_celsius_unit(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the heat pump is operating normally
        When I view the sensors
        Then I see temperature values in Celsius
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        for sensor in entities_added:
            assert sensor._attr_native_unit_of_measurement == "°C"

    @pytest.mark.asyncio
    async def test_sensors_have_measurement_state_class(
        self, mock_hass, mock_coordinator
    ):
        """Sensors should have MEASUREMENT state class for HA statistics."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        for sensor in entities_added:
            assert sensor._attr_state_class == "measurement"

    @pytest.mark.asyncio
    async def test_sensors_show_actual_temperature_values(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the heat pump is operating normally
        When I view the sensors
        Then each sensor shows its actual temperature value
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        # Get expected values from mock
        expected = mock_coordinator.data.temperatures

        for sensor in entities_added:
            actual_value = sensor.native_value
            expected_value = expected[sensor._sensor_type]

            assert actual_value == expected_value, (
                f"Sensor {sensor._sensor_type}: "
                f"expected {expected_value}, got {actual_value}"
            )

            # Values should be floats (temperature readings)
            assert isinstance(actual_value, (int, float))


class TestUS1Scenario3UnavailableOnDisconnect:
    """Scenario 3: Sensors show unavailable when connection is lost."""

    @pytest.mark.asyncio
    async def test_sensors_return_none_when_disconnected(
        self, mock_hass, mock_coordinator_disconnected
    ):
        """
        Given the serial connection is lost
        When Home Assistant polls for data
        Then sensors return None (shown as unavailable in HA)
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator_disconnected}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        for sensor in entities_added:
            assert sensor.native_value is None, (
                f"Sensor {sensor._sensor_type} should return None when disconnected"
            )

    @pytest.mark.asyncio
    async def test_sensors_become_unavailable_on_data_loss(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the heat pump was connected
        When the serial connection is lost (coordinator.data becomes None)
        Then sensors show unavailable status
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        # Initially sensors have values
        outdoor_sensor = next(
            s for s in entities_added if s._sensor_type == SENSOR_OUTDOOR
        )
        assert outdoor_sensor.native_value is not None

        # Simulate connection loss
        mock_coordinator.data = None
        mock_coordinator.last_update_success = False

        # Sensors should now return None
        assert outdoor_sensor.native_value is None
