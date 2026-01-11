"""Unit tests for USB Connection Switch entity.

Tests the BuderusUSBConnectionSwitch entity that allows developers to
temporarily release the USB serial port for CLI debugging.
"""

from unittest.mock import MagicMock

import pytest

# Import after conftest sets up mocks
from custom_components.buderus_wps.switch import BuderusUSBConnectionSwitch


class TestUSBConnectionSwitch:
    """Test USB connection switch properties and state."""

    def test_switch_has_correct_name(self, mock_coordinator: MagicMock) -> None:
        """Test switch has the correct display name."""
        mock_entry = MagicMock()
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        assert switch._attr_name == "USB Connection"

    def test_switch_has_correct_icon(self, mock_coordinator: MagicMock) -> None:
        """Test switch has the correct icon."""
        mock_entry = MagicMock()
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        assert switch._attr_icon == "mdi:usb-port"

    def test_switch_has_correct_entity_key(self, mock_coordinator: MagicMock) -> None:
        """Test switch uses correct entity key for unique ID."""
        mock_entry = MagicMock()
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        # entity_key is used by BuderusEntity base class to build unique_id
        assert switch.entity_key == "usb_connection"

    def test_switch_returns_true_when_connected(
        self, mock_coordinator: MagicMock
    ) -> None:
        """Test is_on returns True when not manually disconnected."""
        mock_entry = MagicMock()
        mock_coordinator._manually_disconnected = False
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        assert switch.is_on is True

    def test_switch_returns_false_when_manually_disconnected(
        self, mock_coordinator: MagicMock
    ) -> None:
        """Test is_on returns False when manually disconnected."""
        mock_entry = MagicMock()
        mock_coordinator._manually_disconnected = True
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        assert switch.is_on is False


class TestUSBConnectionSwitchActions:
    """Test USB connection switch turn_on/turn_off actions."""

    @pytest.mark.asyncio
    async def test_turn_off_calls_manual_disconnect(
        self, mock_coordinator: MagicMock
    ) -> None:
        """Test async_turn_off calls coordinator.async_manual_disconnect."""
        mock_entry = MagicMock()
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        await switch.async_turn_off()

        mock_coordinator.async_manual_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_calls_manual_connect(
        self, mock_coordinator: MagicMock
    ) -> None:
        """Test async_turn_on calls coordinator.async_manual_connect."""
        mock_entry = MagicMock()
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        await switch.async_turn_on()

        mock_coordinator.async_manual_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_handles_port_in_use_error(
        self, mock_coordinator: MagicMock
    ) -> None:
        """Test async_turn_on raises HomeAssistantError when port is busy.

        When the CLI tool has the USB port open, async_manual_connect will raise
        a DeviceNotFoundError. The switch should catch this and raise a
        HomeAssistantError that will be shown to the user in the HA UI.
        """
        # Import DeviceNotFoundError from main library (bundled copy not available in tests)
        from buderus_wps.exceptions import (
            DeviceNotFoundError,
        )

        mock_entry = MagicMock()
        # Mock coordinator.async_manual_connect to raise DeviceNotFoundError
        mock_coordinator.async_manual_connect.side_effect = DeviceNotFoundError(
            "Could not find USB device"
        )
        switch = BuderusUSBConnectionSwitch(mock_coordinator, mock_entry)

        # Should raise an exception with "USB port in use" message
        # Use Exception base class to avoid class identity issues with mocked modules
        with pytest.raises(Exception) as exc_info:
            await switch.async_turn_on()

        # Verify the exception message contains expected text
        assert "USB port in use" in str(exc_info.value)
        # Verify it's a HomeAssistantError (by class name, not identity)
        assert "HomeAssistantError" in type(exc_info.value).__name__
