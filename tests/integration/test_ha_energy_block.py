"""Integration tests for energy block switch."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import DOMAIN
from custom_components.buderus_wps.switch import (
    async_setup_platform,
    BuderusEnergyBlockSwitch,
)
from tests.conftest import MockBuderusData


class TestEnergyBlockSwitchDataFlow:
    """Test energy block switch data flow from coordinator."""

    @pytest.mark.asyncio
    async def test_only_energy_block_switch_created(
        self, mock_hass, mock_coordinator
    ):
        """Only energy block switch should be created (DHW extra is now a number)."""
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

        # Only 1 switch (energy block), DHW extra is now a NumberEntity
        assert len(entities_added) == 1
        assert isinstance(entities_added[0], BuderusEnergyBlockSwitch)

    @pytest.mark.asyncio
    async def test_no_switches_without_discovery_info(
        self, mock_hass, mock_coordinator
    ):
        """No switches created when discovery_info is None."""
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
    async def test_switch_reflects_coordinator_state(
        self, mock_hass, mock_coordinator
    ):
        """Energy block switch state must match coordinator data."""
        entities_added = []
        mock_coordinator.data.energy_blocked = True
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
    async def test_switch_updates_when_state_changes(
        self, mock_hass, mock_coordinator
    ):
        """Switch updates when coordinator data changes."""
        entities_added = []
        mock_coordinator.data.energy_blocked = False
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        assert switch.is_on is False

        # Simulate state change
        mock_coordinator.data = MockBuderusData(
            temperatures={
                "outdoor": 5.5,
                "supply": 35.0,
                "return_temp": 30.0,
                "dhw": 48.5,
                "brine_in": 8.0,
            },
            compressor_running=True,
            energy_blocked=True,
            dhw_extra_duration=0,
        )

        # Switch should reflect new state
        assert switch.is_on is True


class TestEnergyBlockCommands:
    """Test energy block switch commands."""

    @pytest.mark.asyncio
    async def test_turn_on_enables_blocking(
        self, mock_hass, mock_coordinator
    ):
        """Turning on switch should enable energy blocking."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        await switch.async_turn_on()

        mock_coordinator.async_set_energy_blocking.assert_called_with(True)

    @pytest.mark.asyncio
    async def test_turn_off_disables_blocking(
        self, mock_hass, mock_coordinator
    ):
        """Turning off switch should disable energy blocking."""
        entities_added = []
        mock_hass.data[DOMAIN] = {"coordinator": mock_coordinator}

        await async_setup_platform(
            mock_hass,
            {},
            lambda e: entities_added.extend(e),
            discovery_info={"platform": "buderus_wps"},
        )

        switch = entities_added[0]
        await switch.async_turn_off()

        mock_coordinator.async_set_energy_blocking.assert_called_with(False)
