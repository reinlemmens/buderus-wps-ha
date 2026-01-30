"""Unit tests for Compressor Block Switch entity."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.buderus_wps.buderus_wps.energy_blocking import BlockingResult
from custom_components.buderus_wps.switch import BuderusCompressorBlockSwitch


class TestCompressorBlockSwitch:
    """Test compressor block switch properties and state."""

    def test_switch_properties(self, mock_coordinator: MagicMock) -> None:
        """Test switch has correct name, icon, and unique ID."""
        mock_entry = MagicMock()
        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)

        assert switch._attr_name == "Compressor Block"
        assert switch._attr_icon == "mdi:power-plug-off"
        assert switch.entity_key == "compressor_block"

    def test_switch_is_on_when_blocked(self, mock_coordinator: MagicMock) -> None:
        """Test is_on returns True when compressor_blocked is True."""
        mock_entry = MagicMock()
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.compressor_blocked = True

        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        assert switch.is_on is True

    def test_switch_is_off_when_unblocked(self, mock_coordinator: MagicMock) -> None:
        """Test is_on returns False when compressor_blocked is False."""
        mock_entry = MagicMock()
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.compressor_blocked = False

        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        assert switch.is_on is False

    def test_switch_state_is_none_when_data_missing(self, mock_coordinator: MagicMock) -> None:
        """Test is_on returns None when data is unavailable."""
        mock_entry = MagicMock()
        mock_coordinator.data = None

        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        assert switch.is_on is None

        # Test when data exists but field is None
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.compressor_blocked = None
        assert switch.is_on is None


class TestCompressorBlockSwitchActions:
    """Test switch turn_on/turn_off actions."""

    @pytest.mark.asyncio
    async def test_turn_on_success(self, mock_coordinator: MagicMock) -> None:
        """Test async_turn_on calls block_compressor."""
        mock_entry = MagicMock()
        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        switch.hass = AsyncMock()

        # Mock energy_blocking helper
        mock_coordinator.energy_blocking = MagicMock()
        mock_coordinator.energy_blocking.block_compressor.return_value = BlockingResult(
            success=True, component="compressor", action="block", message="Success"
        )

        # Mock async_add_executor_job to return the result immediately
        switch.hass.async_add_executor_job.side_effect = lambda f, *args: f(*args)

        await switch.async_turn_on()

        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_success(self, mock_coordinator: MagicMock) -> None:
        """Test async_turn_off calls unblock_compressor."""
        mock_entry = MagicMock()
        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        switch.hass = AsyncMock()

        mock_coordinator.energy_blocking = MagicMock()
        mock_coordinator.energy_blocking.unblock_compressor.return_value = BlockingResult(
            success=True, component="compressor", action="unblock", message="Success"
        )

        switch.hass.async_add_executor_job.side_effect = lambda f, *args: f(*args)

        await switch.async_turn_off()

        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_failure(self, mock_coordinator: MagicMock) -> None:
        """Test async_turn_on raises error on failure."""
        mock_entry = MagicMock()
        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        switch.hass = AsyncMock()

        mock_coordinator.energy_blocking = MagicMock()
        mock_coordinator.energy_blocking.block_compressor.return_value = BlockingResult(
            success=False,
            component="compressor",
            action="block",
            message="Failed",
            error="CAN Error"
        )

        switch.hass.async_add_executor_job.side_effect = lambda f, *args: f(*args)

        with pytest.raises(HomeAssistantError, match=r"Failed to block compressor: Failed \(Error: CAN Error\)"):
            await switch.async_turn_on()

    @pytest.mark.asyncio
    async def test_turn_off_failure(self, mock_coordinator: MagicMock) -> None:
        """Test async_turn_off raises error on failure."""
        mock_entry = MagicMock()
        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        switch.hass = AsyncMock()

        mock_coordinator.energy_blocking = MagicMock()
        mock_coordinator.energy_blocking.unblock_compressor.return_value = BlockingResult(
            success=False,
            component="compressor",
            action="unblock",
            message="Failed",
            error="Timeout"
        )

        switch.hass.async_add_executor_job.side_effect = lambda f, *args: f(*args)

        with pytest.raises(HomeAssistantError, match=r"Failed to unblock compressor: Failed \(Error: Timeout\)"):
            await switch.async_turn_off()

    @pytest.mark.asyncio
    async def test_action_raises_if_not_initialized(self, mock_coordinator: MagicMock) -> None:
        """Test actions raise if energy blocking not initialized."""
        mock_entry = MagicMock()
        switch = BuderusCompressorBlockSwitch(mock_coordinator, mock_entry)
        switch.hass = AsyncMock()

        mock_coordinator.energy_blocking = None

        with pytest.raises(HomeAssistantError, match="Energy blocking control not initialized"):
            await switch.async_turn_on()
