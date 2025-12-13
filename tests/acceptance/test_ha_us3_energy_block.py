"""Acceptance tests for User Story 3: Control Energy Blocking.

User Story:
As a homeowner, I want to enable/disable energy blocking during peak electricity hours
so that I can reduce costs while maintaining comfort when rates are lower.

Acceptance Scenarios:
1. Given blocking is disabled, When I turn on the switch, Then heat pump stops heating
2. Given blocking is enabled, When I turn off the switch, Then heat pump resumes heating
3. Given I restart Home Assistant, When I view switch, Then it shows current state
"""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import DOMAIN
from custom_components.buderus_wps.switch import (
    async_setup_platform,
    BuderusEnergyBlockSwitch,
)


class TestUS3Scenario1TurnOnEnablesBlocking:
    """Scenario 1: Turning on switch enables energy blocking."""

    @pytest.mark.asyncio
    async def test_turn_on_enables_blocking(
        self, mock_hass, mock_coordinator
    ):
        """
        Given energy blocking is disabled
        When I turn on the Energy Block switch
        Then the heat pump stops heating (blocking enabled)
        """
        mock_coordinator.data.energy_blocked = False
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch.is_on is False  # Initially disabled

        await switch.async_turn_on()

        # Coordinator method should be called to enable blocking
        mock_coordinator.async_set_energy_blocking.assert_called_with(True)
        mock_coordinator.async_request_refresh.assert_called()


class TestUS3Scenario2TurnOffDisablesBlocking:
    """Scenario 2: Turning off switch disables energy blocking."""

    @pytest.mark.asyncio
    async def test_turn_off_disables_blocking(
        self, mock_hass, mock_coordinator
    ):
        """
        Given energy blocking is enabled
        When I turn off the Energy Block switch
        Then the heat pump resumes heating (blocking disabled)
        """
        mock_coordinator.data.energy_blocked = True
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch.is_on is True  # Initially enabled

        await switch.async_turn_off()

        # Coordinator method should be called to disable blocking
        mock_coordinator.async_set_energy_blocking.assert_called_with(False)
        mock_coordinator.async_request_refresh.assert_called()


class TestUS3Scenario3StateReflectsOnLoad:
    """Scenario 3: Switch reflects current state on load."""

    @pytest.mark.asyncio
    async def test_switch_shows_enabled_state_on_load(
        self, mock_hass, mock_coordinator
    ):
        """
        Given energy blocking was enabled
        When Home Assistant starts
        Then the switch shows ON state
        """
        mock_coordinator.data.energy_blocked = True
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch.is_on is True

    @pytest.mark.asyncio
    async def test_switch_shows_disabled_state_on_load(
        self, mock_hass, mock_coordinator
    ):
        """
        Given energy blocking was disabled
        When Home Assistant starts
        Then the switch shows OFF state
        """
        mock_coordinator.data.energy_blocked = False
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch.is_on is False

    @pytest.mark.asyncio
    async def test_switch_shows_unavailable_when_disconnected(
        self, mock_hass, mock_coordinator_disconnected
    ):
        """
        Given the heat pump is disconnected
        When Home Assistant starts
        Then the switch shows unavailable
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator_disconnected}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch.is_on is None


class TestUS3SwitchProperties:
    """Test energy block switch properties."""

    @pytest.mark.asyncio
    async def test_switch_has_correct_name(
        self, mock_hass, mock_coordinator
    ):
        """Switch should be named 'Energy Block'."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch._attr_name == "Energy Block"

    @pytest.mark.asyncio
    async def test_switch_has_correct_icon(
        self, mock_hass, mock_coordinator
    ):
        """Switch should have power-plug-off icon."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch._attr_icon == "mdi:power-plug-off"
