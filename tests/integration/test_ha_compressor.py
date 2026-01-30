"""Integration tests for compressor binary sensor."""

from __future__ import annotations

import pytest

from custom_components.buderus_wps.binary_sensor import (
    BuderusCompressorSensor,
    async_setup_platform,
)

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import DOMAIN
from tests.conftest import MockBuderusData


class TestCompressorSensorDataFlow:
    """Test compressor state data flow from coordinator."""

    @pytest.mark.asyncio
    async def test_compressor_sensor_created_from_coordinator(
        self, mock_hass, mock_coordinator
    ):
        """Compressor sensor should be created from coordinator."""
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

        assert len(entities_added) == 1
        assert isinstance(entities_added[0], BuderusCompressorSensor)

    @pytest.mark.asyncio
    async def test_no_sensors_without_discovery_info(self, mock_hass, mock_coordinator):
        """No sensors created when discovery_info is None."""
        entities_added = []

        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info=None,
        )

        assert len(entities_added) == 0

    @pytest.mark.asyncio
    async def test_compressor_reflects_coordinator_state(
        self, mock_hass, mock_coordinator
    ):
        """Compressor sensor state must match coordinator data."""
        entities_added = []
        mock_coordinator.data.compressor_running = True
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert compressor.is_on is True

    @pytest.mark.asyncio
    async def test_compressor_updates_when_state_changes(
        self, mock_hass, mock_coordinator
    ):
        """Compressor sensor updates when coordinator data changes."""
        entities_added = []
        mock_coordinator.data.compressor_running = True
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert compressor.is_on is True

        # Simulate state change
        mock_coordinator.data = MockBuderusData(
            temperatures={
                "outdoor": 5.5,
                "supply": 35.0,
                "return_temp": 30.0,
                "dhw": 48.5,
                "brine_in": 8.0,
            },
            compressor_running=False,
            energy_blocked=False,
            dhw_active=False,
            g1_active=False,
            dhw_extra_duration=0,
        )

        # Sensor should reflect new state
        assert compressor.is_on is False
