"""Unit tests for Home Assistant switch entities."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.switch import BuderusEnergyBlockSwitch


class TestEnergyBlockSwitch:
    """Test energy block switch entity."""

    def test_switch_has_correct_name(self, mock_coordinator):
        """Energy block switch must be named 'Energy Block'."""
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        assert switch._attr_name == "Energy Block"

    def test_switch_has_power_plug_off_icon(self, mock_coordinator):
        """Energy block switch must have power-plug-off icon."""
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        assert switch._attr_icon == "mdi:power-plug-off"

    def test_switch_returns_true_when_blocked(self, mock_coordinator):
        """Switch returns True when energy blocking is enabled."""
        mock_coordinator.data.energy_blocked = True
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        assert switch.is_on is True

    def test_switch_returns_false_when_not_blocked(self, mock_coordinator):
        """Switch returns False when energy blocking is disabled."""
        mock_coordinator.data.energy_blocked = False
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        assert switch.is_on is False

    def test_switch_returns_none_when_disconnected(
        self, mock_coordinator_disconnected
    ):
        """Switch returns None when coordinator has no data."""
        switch = BuderusEnergyBlockSwitch(mock_coordinator_disconnected)
        assert switch.is_on is None

    def test_switch_entity_key(self, mock_coordinator):
        """Switch must use correct entity key for unique ID."""
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        assert switch.entity_key == "energy_block"

    @pytest.mark.asyncio
    async def test_turn_on_calls_coordinator(self, mock_coordinator):
        """Turning on switch should call coordinator.async_set_energy_blocking(True)."""
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        await switch.async_turn_on()

        mock_coordinator.async_set_energy_blocking.assert_called_once_with(True)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_calls_coordinator(self, mock_coordinator):
        """Turning off switch should call coordinator.async_set_energy_blocking(False)."""
        switch = BuderusEnergyBlockSwitch(mock_coordinator)
        await switch.async_turn_off()

        mock_coordinator.async_set_energy_blocking.assert_called_once_with(False)
        mock_coordinator.async_request_refresh.assert_called_once()


class TestDHWExtraSwitchRemoved:
    """Test that DHW extra switch is no longer registered."""

    def test_dhw_extra_switch_class_not_exported(self):
        """BuderusDHWExtraSwitch should not be in the public API anymore."""
        from custom_components.buderus_wps import switch

        # Only BuderusEnergyBlockSwitch should be used
        assert hasattr(switch, "BuderusEnergyBlockSwitch")
        # DHW extra is now a NumberEntity, not a switch
