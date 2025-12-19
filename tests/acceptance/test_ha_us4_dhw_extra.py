"""Acceptance tests for User Story 4: Control DHW Extra Production.

User Story:
As a homeowner, I want to activate extra hot water production for a specified duration
so that I can ensure sufficient hot water availability before guests arrive.

Acceptance Scenarios:
1. Given DHW extra is not active, When I set duration (1-24h), Then production starts
2. Given DHW extra is active, When I set 0, Then production stops
3. Given DHW extra is active (3h remaining), When I view, Then number input shows 3
"""

from __future__ import annotations

import pytest
from homeassistant.components.number import NumberMode

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import DOMAIN
from custom_components.buderus_wps.number import (
    async_setup_platform,
    BuderusDHWExtraDurationNumber,
)
from tests.conftest import MockBuderusData


class TestUS4Scenario1SettingDurationStartsProduction:
    """Scenario 1: Setting duration starts DHW extra production."""

    @pytest.mark.asyncio
    async def test_setting_duration_starts_production(
        self, mock_hass, mock_coordinator
    ):
        """
        Given DHW extra is not active (duration = 0)
        When I set the slider to 8 hours
        Then DHW extra production starts for 8 hours
        """
        mock_coordinator.data.dhw_extra_duration = 0
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 0  # Initially not active

        await number.async_set_native_value(8)

        # Coordinator method should be called to set duration
        mock_coordinator.async_set_dhw_extra_duration.assert_called_with(8)
        mock_coordinator.async_request_refresh.assert_called()

    @pytest.mark.asyncio
    async def test_number_box_has_correct_range(
        self, mock_hass, mock_coordinator
    ):
        """
        The number input box should have range 0-24 hours with step 1.
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number._attr_native_min_value == 0
        assert number._attr_native_max_value == 24
        assert number._attr_native_step == 1
        assert number._attr_mode == NumberMode.BOX


class TestUS4Scenario2SettingZeroStopsProduction:
    """Scenario 2: Setting 0 stops DHW extra production."""

    @pytest.mark.asyncio
    async def test_setting_zero_stops_production(
        self, mock_hass, mock_coordinator
    ):
        """
        Given DHW extra is active (duration > 0)
        When I set the slider to 0
        Then DHW extra production stops immediately
        """
        mock_coordinator.data.dhw_extra_duration = 5
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 5  # Initially active

        await number.async_set_native_value(0)

        # Coordinator method should be called to stop (set 0)
        mock_coordinator.async_set_dhw_extra_duration.assert_called_with(0)


class TestUS4Scenario3SliderShowsRemainingDuration:
    """Scenario 3: Slider shows remaining duration."""

    @pytest.mark.asyncio
    async def test_slider_shows_remaining_hours(
        self, mock_hass, mock_coordinator
    ):
        """
        Given DHW extra was activated for 8 hours, 3 hours remaining
        When I view the slider
        Then it shows 3
        """
        mock_coordinator.data.dhw_extra_duration = 3
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 3

    @pytest.mark.asyncio
    async def test_slider_updates_as_duration_decreases(
        self, mock_hass, mock_coordinator
    ):
        """
        Given DHW extra is active
        When time passes and remaining duration decreases
        Then the slider value updates accordingly
        """
        mock_coordinator.data.dhw_extra_duration = 5
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 5

        # Simulate time passing (coordinator update)
        mock_coordinator.data = MockBuderusData(
            temperatures={
                "outdoor": 5.5,
                "supply": 35.0,
                "return_temp": 30.0,
                "dhw": 48.5,
                "brine_in": 8.0,
            },
            compressor_running=True,
            energy_blocked=False,
            dhw_extra_duration=4,  # Decreased by 1 hour
        )

        # Slider should now show 4
        assert number.native_value == 4

    @pytest.mark.asyncio
    async def test_slider_shows_zero_when_not_active(
        self, mock_hass, mock_coordinator
    ):
        """
        Given DHW extra is not active
        When I view the slider
        Then it shows 0
        """
        mock_coordinator.data.dhw_extra_duration = 0
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 0

    @pytest.mark.asyncio
    async def test_slider_unavailable_when_disconnected(
        self, mock_hass, mock_coordinator_disconnected
    ):
        """
        Given the heat pump is disconnected
        When I view the slider
        Then it shows unavailable (None)
        """
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator_disconnected}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value is None


class TestUS4NumberProperties:
    """Test DHW extra duration number properties."""

    @pytest.mark.asyncio
    async def test_number_has_correct_name(
        self, mock_hass, mock_coordinator
    ):
        """Number should be named 'DHW Extra Duration'."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number._attr_name == "DHW Extra Duration"

    @pytest.mark.asyncio
    async def test_number_has_correct_unit(
        self, mock_hass, mock_coordinator
    ):
        """Number should use hours unit."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number._attr_native_unit_of_measurement == "h"
