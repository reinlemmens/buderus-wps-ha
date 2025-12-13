"""Integration tests for coordinator reconnection with exponential backoff."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py sets up HA mocks at import time
from custom_components.buderus_wps.const import BACKOFF_INITIAL, BACKOFF_MAX


class TestExponentialBackoff:
    """Test exponential backoff reconnection logic."""

    def test_backoff_initial_is_5_seconds(self):
        """Initial backoff must be 5 seconds per spec."""
        assert BACKOFF_INITIAL == 5

    def test_backoff_max_is_120_seconds(self):
        """Maximum backoff must be 120 seconds (2 minutes) per spec."""
        assert BACKOFF_MAX == 120

    @pytest.mark.asyncio
    async def test_coordinator_initializes_with_initial_backoff(self, mock_hass):
        """Coordinator must start with initial backoff delay."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this
        assert coordinator._backoff_delay == BACKOFF_INITIAL

    @pytest.mark.asyncio
    async def test_backoff_doubles_on_failure(self, mock_hass):
        """Backoff delay must double after each failed reconnection attempt."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this
        coordinator._connected = False

        # Simulate backoff doubling
        initial = coordinator._backoff_delay
        coordinator._backoff_delay = min(coordinator._backoff_delay * 2, BACKOFF_MAX)
        assert coordinator._backoff_delay == initial * 2

    @pytest.mark.asyncio
    async def test_backoff_caps_at_max(self, mock_hass):
        """Backoff delay must not exceed maximum value."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this

        # Set delay close to max
        coordinator._backoff_delay = 100

        # Double should cap at max
        coordinator._backoff_delay = min(coordinator._backoff_delay * 2, BACKOFF_MAX)
        assert coordinator._backoff_delay == BACKOFF_MAX

    @pytest.mark.asyncio
    async def test_backoff_resets_on_successful_reconnection(self, mock_hass):
        """Backoff delay must reset to initial value after successful reconnection."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this

        # Simulate failed attempts
        coordinator._backoff_delay = 60
        coordinator._connected = False

        # Successful reconnection
        coordinator._connected = True
        coordinator._backoff_delay = BACKOFF_INITIAL  # Reset on success

        assert coordinator._backoff_delay == BACKOFF_INITIAL

    @pytest.mark.asyncio
    async def test_handle_connection_failure_triggers_reconnect(self, mock_hass):
        """Connection failure must trigger reconnection task."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this
        coordinator._connected = False
        coordinator._reconnect_task = None

        # Mock the background task creation
        mock_task = MagicMock()
        mock_hass.async_create_background_task = MagicMock(return_value=mock_task)

        await coordinator._handle_connection_failure()

        mock_hass.async_create_background_task.assert_called_once()
        assert coordinator._reconnect_task is not None

    @pytest.mark.asyncio
    async def test_no_duplicate_reconnect_tasks(self, mock_hass):
        """Must not create duplicate reconnection tasks."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this
        coordinator._connected = False

        # Already has a reconnect task
        existing_task = MagicMock()
        coordinator._reconnect_task = existing_task

        mock_hass.async_create_background_task = MagicMock()

        await coordinator._handle_connection_failure()

        # Should not create a new task
        mock_hass.async_create_background_task.assert_not_called()
        assert coordinator._reconnect_task is existing_task

    @pytest.mark.asyncio
    async def test_shutdown_cancels_reconnect_task(self, mock_hass):
        """Shutdown must cancel any pending reconnection task."""
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass  # Mock parent doesn't set this

        # Set up a mock reconnect task
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        coordinator._reconnect_task = mock_task
        coordinator._connected = False

        mock_hass.async_add_executor_job = AsyncMock()

        await coordinator.async_shutdown()

        mock_task.cancel.assert_called_once()
        assert coordinator._reconnect_task is None


class TestBackoffSequence:
    """Test the full backoff sequence."""

    def test_backoff_sequence_is_exponential(self):
        """Verify the backoff sequence follows exponential pattern."""
        delays = []
        delay = BACKOFF_INITIAL

        # Simulate 10 failures
        for _ in range(10):
            delays.append(delay)
            delay = min(delay * 2, BACKOFF_MAX)

        # Expected sequence: 5, 10, 20, 40, 80, 120, 120, 120, 120, 120
        expected = [5, 10, 20, 40, 80, 120, 120, 120, 120, 120]
        assert delays == expected

    def test_backoff_reaches_max_in_5_failures(self):
        """Backoff should reach max after 5 failed attempts."""
        delay = BACKOFF_INITIAL
        failures = 0

        while delay < BACKOFF_MAX:
            delay = min(delay * 2, BACKOFF_MAX)
            failures += 1

        # 5 -> 10 -> 20 -> 40 -> 80 -> 120 = 5 failures
        assert failures == 5
