"""Acceptance tests for User Story 2: View Compressor Status.

User Story:
As a homeowner, I want to see if my heat pump compressor is running
so that I can verify the system is actively heating when needed.

Acceptance Scenarios:
1. Given the compressor is running, When I view HA, Then I see "Running"
2. Given the compressor is stopped, When I view HA, Then I see "Stopped"
3. Given connection is lost, When I view HA, Then compressor shows unavailable
"""

from __future__ import annotations

import pytest

from custom_components.buderus_wps.binary_sensor import (
    async_setup_platform,
)

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import DOMAIN


class TestUS2Scenario1CompressorRunning:
    """Scenario 1: Compressor shows Running when active."""

    @pytest.mark.asyncio
    async def test_compressor_shows_running_when_active(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the compressor is running
        When I view Home Assistant
        Then I see the compressor status as "Running" (is_on=True)
        """
        mock_coordinator.data.compressor_running = True
        entities_added = []
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
    async def test_compressor_has_running_device_class(
        self, mock_hass, mock_coordinator
    ):
        """
        The compressor sensor should have RUNNING device class
        so HA displays it appropriately.
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert compressor._attr_device_class == "running"

    @pytest.mark.asyncio
    async def test_compressor_has_correct_name(self, mock_hass, mock_coordinator):
        """
        The compressor sensor should be named "Compressor"
        (device info adds "Heat Pump" prefix).
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert compressor._attr_name == "Compressor"


class TestUS2Scenario2CompressorStopped:
    """Scenario 2: Compressor shows Stopped when inactive."""

    @pytest.mark.asyncio
    async def test_compressor_shows_stopped_when_inactive(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the compressor is stopped
        When I view Home Assistant
        Then I see the compressor status as "Stopped" (is_on=False)
        """
        mock_coordinator.data.compressor_running = False
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert compressor.is_on is False


class TestUS2Scenario3UnavailableOnDisconnect:
    """Scenario 3: Compressor shows unavailable when disconnected."""

    @pytest.mark.asyncio
    async def test_compressor_unavailable_when_disconnected(
        self, mock_hass, mock_coordinator_disconnected
    ):
        """
        Given the serial connection is lost
        When I view Home Assistant
        Then the compressor status shows unavailable (is_on=None)
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator_disconnected}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert (
            compressor.is_on is None
        ), "Compressor should return None when disconnected"

    @pytest.mark.asyncio
    async def test_compressor_becomes_unavailable_on_data_loss(
        self, mock_hass, mock_coordinator
    ):
        """
        Given the heat pump was connected
        When the serial connection is lost
        Then the compressor status becomes unavailable
        """
        mock_coordinator.data.compressor_running = True
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        compressor = entities_added[0]
        assert compressor.is_on is True

        # Simulate connection loss
        mock_coordinator.data = None

        # Compressor should now return None
        assert compressor.is_on is None
