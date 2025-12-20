"""Integration tests for coordinator manual disconnect/connect behavior.

Tests the interaction between manual disconnect/connect and auto-reconnection
to ensure the state machine works correctly.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.buderus_wps.const import BACKOFF_INITIAL, DEFAULT_SCAN_INTERVAL

# Import after conftest sets up mocks
from custom_components.buderus_wps.coordinator import BuderusCoordinator


class TestCoordinatorManualDisconnect:
    """Test manual disconnect/connect state machine behavior."""

    @pytest.mark.asyncio
    async def test_manual_disconnect_stops_auto_reconnect(
        self, mock_hass: MagicMock
    ) -> None:
        """Test that manual disconnect cancels any pending auto-reconnection task.

        When auto-reconnection is in progress and user manually disconnects,
        the reconnection task should be cancelled immediately.
        """
        coordinator = BuderusCoordinator(
            mock_hass, "/dev/ttyACM0", DEFAULT_SCAN_INTERVAL
        )
        coordinator.hass = (
            mock_hass  # Ensure hass is available for async_add_executor_job
        )

        # Simulate an active reconnection task
        mock_reconnect_task = AsyncMock()
        coordinator._reconnect_task = mock_reconnect_task
        coordinator._connected = True

        # Manually disconnect
        await coordinator.async_manual_disconnect()

        # Verify reconnection task was cancelled
        mock_reconnect_task.cancel.assert_called_once()
        assert coordinator._reconnect_task is None
        assert coordinator._manually_disconnected is True
        assert coordinator._connected is False

    @pytest.mark.asyncio
    async def test_manual_connect_restarts_connection(
        self, mock_hass: MagicMock
    ) -> None:
        """Test that manual connect clears flag, resets backoff, and connects.

        After manual connect:
        - _manually_disconnected should be False
        - _backoff_delay should be reset to BACKOFF_INITIAL
        - _connected should be True
        - Connection should be established
        """
        coordinator = BuderusCoordinator(
            mock_hass, "/dev/ttyACM0", DEFAULT_SCAN_INTERVAL
        )
        coordinator.hass = (
            mock_hass  # Ensure hass is available for async_add_executor_job
        )

        # Set up manual disconnect state with high backoff
        coordinator._manually_disconnected = True
        coordinator._backoff_delay = 120  # Maximum backoff
        coordinator._connected = False

        # Add async_request_refresh method (inherited from base class in real usage)
        coordinator.async_request_refresh = AsyncMock()

        # Mock _sync_connect to succeed
        with patch.object(coordinator, "_sync_connect"):
            # Manually reconnect
            await coordinator.async_manual_connect()

            # Verify state reset
            assert coordinator._manually_disconnected is False
            assert coordinator._backoff_delay == BACKOFF_INITIAL
            assert coordinator._connected is True

            # Verify refresh was called
            coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_disconnect_preserves_stale_data(
        self, mock_hass: MagicMock
    ) -> None:
        """Test that manual disconnect preserves last-known-good data.

        When user manually disconnects, the coordinator should keep
        the last-known-good data available for graceful degradation.
        """
        coordinator = BuderusCoordinator(
            mock_hass, "/dev/ttyACM0", DEFAULT_SCAN_INTERVAL
        )
        coordinator.hass = (
            mock_hass  # Ensure hass is available for async_add_executor_job
        )

        # Set up some last-known-good data
        mock_data = MagicMock()
        coordinator._last_known_good_data = mock_data
        coordinator._connected = True

        # Manually disconnect
        await coordinator.async_manual_disconnect()

        # Verify data preserved
        assert coordinator._last_known_good_data is mock_data
        assert coordinator._manually_disconnected is True

    @pytest.mark.asyncio
    async def test_reconnect_loop_exits_on_manual_disconnect(
        self, mock_hass: MagicMock
    ) -> None:
        """Test that _reconnect_with_backoff exits when manually disconnected.

        The auto-reconnection loop should check _manually_disconnected at the
        start of each iteration and exit immediately if True.
        """
        coordinator = BuderusCoordinator(
            mock_hass, "/dev/ttyACM0", DEFAULT_SCAN_INTERVAL
        )
        coordinator.hass = (
            mock_hass  # Ensure hass is available for async_add_executor_job
        )

        # Set up disconnected state
        coordinator._connected = False
        coordinator._manually_disconnected = False

        # Mock _sync_connect to track if it's called
        with patch.object(coordinator, "_sync_connect") as mock_sync_connect:
            # Start reconnection task
            reconnect_task = asyncio.create_task(coordinator._reconnect_with_backoff())

            # Give it a moment to start
            await asyncio.sleep(0.1)

            # Now manually disconnect - this should cause the loop to exit
            coordinator._manually_disconnected = True

            # Wait for task to complete (allow time for sleep to complete + check)
            try:
                await asyncio.wait_for(reconnect_task, timeout=6.0)
            except asyncio.TimeoutError:
                pytest.fail("Reconnection loop did not exit on manual disconnect")

            # Verify the task cleaned up properly
            assert coordinator._reconnect_task is None

    @pytest.mark.asyncio
    async def test_manual_disconnect_while_connected(
        self, mock_hass: MagicMock
    ) -> None:
        """Test manual disconnect when already connected.

        Should disconnect cleanly and set manual disconnect flag.
        """
        coordinator = BuderusCoordinator(
            mock_hass, "/dev/ttyACM0", DEFAULT_SCAN_INTERVAL
        )
        coordinator.hass = (
            mock_hass  # Ensure hass is available for async_add_executor_job
        )

        # Set up connected state
        coordinator._connected = True
        coordinator._manually_disconnected = False

        # Mock _sync_disconnect
        with patch.object(coordinator, "_sync_disconnect") as mock_sync_disconnect:
            await coordinator.async_manual_disconnect()

            # Verify disconnect was called
            mock_sync_disconnect.assert_called_once()
            assert coordinator._connected is False
            assert coordinator._manually_disconnected is True
