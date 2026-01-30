"""Integration tests for temperature sensor data flow."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import (
    DOMAIN,
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
from custom_components.buderus_wps.sensor import (
    async_setup_platform,
)
from tests.conftest import MockBuderusData


class TestTemperatureSensorDataFlow:
    """Test temperature data flows correctly from coordinator to sensors."""

    @pytest.mark.asyncio
    async def test_sensors_created_from_coordinator(self, mock_hass, mock_coordinator):
        """All 14 temperature sensors should be created from coordinator data."""
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

        # 14 sensors: 6 core + 4 room + 4 setpoint
        assert len(entities_added) == 14
        sensor_types = {s._sensor_type for s in entities_added}
        assert sensor_types == {
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
            assert (
                sensor.native_value == expected_temps[sensor_type]
            ), f"Sensor {sensor_type} value mismatch"

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
                "brine_out": 5.5,
                "room_c1": 21.0,
                "room_c2": 20.5,
                "room_c3": 19.0,
                "room_c4": 22.0,
                "setpoint_c1": 21.0,
                "setpoint_c2": 21.0,
                "setpoint_c3": 20.0,
                "setpoint_c4": 22.0,
            },
            compressor_running=True,
            energy_blocked=False,
            dhw_active=False,
            g1_active=False,
            dhw_extra_duration=0,
            heating_curve_offset=0.0,
            dhw_stop_temp=55.0,
            dhw_setpoint=50.0,
        )

        # Sensor should now reflect new value
        assert outdoor_sensor.native_value == 10.0


class TestTemperatureSensorNames:
    """Test temperature sensors have entity-only names per HACS guidelines."""

    @pytest.mark.asyncio
    async def test_all_sensors_have_entity_only_names(
        self, mock_hass, mock_coordinator
    ):
        """All temperature sensors use entity-only names (no device prefix)."""
        # With has_entity_name=True, entity names should NOT include device name
        # Home Assistant prepends "Heat Pump" device name automatically in UI
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        for sensor in entities_added:
            # Entity names should not start with "Heat Pump" prefix
            assert not sensor.name.startswith("Heat Pump "), (
                f"Sensor name '{sensor.name}' should be entity-only (without 'Heat Pump' prefix). "
                f"HA prepends device name automatically when has_entity_name=True."
            )

    @pytest.mark.asyncio
    async def test_sensors_have_expected_entity_names(
        self, mock_hass, mock_coordinator
    ):
        """Sensors must have expected entity-only names."""
        # Entity names without device prefix (HA adds "Heat Pump" prefix in UI)
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        # Use SENSOR_NAMES from const.py as the expected names
        for sensor in entities_added:
            expected = SENSOR_NAMES[sensor._sensor_type]
            assert sensor.name == expected, (
                f"Sensor {sensor._sensor_type} name should be '{expected}' (entity-only), "
                f"got '{sensor.name}'"
            )
