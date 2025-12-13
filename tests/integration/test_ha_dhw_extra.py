"""Integration tests for DHW extra duration number entity."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import DOMAIN
from custom_components.buderus_wps.number import (
    async_setup_platform,
    BuderusDHWExtraDurationNumber,
)
from tests.conftest import MockBuderusData


class TestDHWExtraNumberDataFlow:
    """Test DHW extra number entity data flow from coordinator."""

    @pytest.mark.asyncio
    async def test_number_entity_created_from_coordinator(
        self, mock_hass, mock_coordinator
    ):
        """DHW extra number entity should be created from coordinator."""
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
        assert isinstance(entities_added[0], BuderusDHWExtraDurationNumber)

    @pytest.mark.asyncio
    async def test_no_entities_without_discovery_info(
        self, mock_hass, mock_coordinator
    ):
        """No entities created when discovery_info is None."""
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
    async def test_number_reflects_coordinator_state(
        self, mock_hass, mock_coordinator
    ):
        """Number value must match coordinator data."""
        entities_added = []
        mock_coordinator.data.dhw_extra_duration = 12
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 12

    @pytest.mark.asyncio
    async def test_number_updates_when_state_changes(
        self, mock_hass, mock_coordinator
    ):
        """Number updates when coordinator data changes."""
        entities_added = []
        mock_coordinator.data.dhw_extra_duration = 0
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        assert number.native_value == 0

        # Simulate state change - DHW extra activated with 8 hours
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
            dhw_extra_duration=8,
        )

        # Number should reflect new value
        assert number.native_value == 8


class TestDHWExtraCommands:
    """Test DHW extra number entity commands."""

    @pytest.mark.asyncio
    async def test_set_duration_starts_production(
        self, mock_hass, mock_coordinator
    ):
        """Setting duration should start DHW extra production."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        await number.async_set_native_value(6)

        mock_coordinator.async_set_dhw_extra_duration.assert_called_with(6)

    @pytest.mark.asyncio
    async def test_set_zero_stops_production(
        self, mock_hass, mock_coordinator
    ):
        """Setting 0 should stop DHW extra production."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        number = entities_added[0]
        await number.async_set_native_value(0)

        mock_coordinator.async_set_dhw_extra_duration.assert_called_with(0)
