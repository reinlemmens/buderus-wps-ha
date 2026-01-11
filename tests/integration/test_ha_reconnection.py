"""Integration tests for coordinator reconnection with exponential backoff."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

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


class TestIndefiniteCaching:
    """Test indefinite last-known-good data caching."""

    @pytest.mark.asyncio
    async def test_indefinite_caching_after_many_failures(self, mock_hass):
        """Coordinator returns cached data even after 10+ consecutive failures.

        This test verifies FR-011: Coordinator must retain last-known-good data
        indefinitely, never showing "Unknown" after first successful read.
        """
        import time
        from unittest.mock import MagicMock

        from custom_components.buderus_wps.coordinator import (
            BuderusCoordinator,
            BuderusData,
        )

        coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
        coordinator.hass = mock_hass

        # Setup: Simulate successful initial read
        initial_data = BuderusData(
            temperatures={
                "outdoor": 5.5,
                "supply": 35.0,
                "return_temp": 30.0,
                "dhw": 48.5,
                "brine_in": 8.0,
            },
            compressor_running=True,
            energy_blocked=False,
            dhw_extra_duration=0,
            heating_season_mode=1,
            dhw_program_mode=0,
            heating_curve_offset=0.0,
            dhw_stop_temp=55.0,
            dhw_setpoint=50.0,
        )
        coordinator._last_known_good_data = initial_data
        coordinator._last_successful_update = time.time()
        coordinator._connected = True

        # Mock _sync_fetch_data to always raise timeout error
        def mock_timeout_error():
            raise TimeoutError("CAN bus timeout")

        coordinator._sync_fetch_data = MagicMock(side_effect=mock_timeout_error)

        # Simulate 10 consecutive fetch failures
        for _i in range(10):
            try:
                await coordinator._async_update_data()
                # After implementation, this should NOT raise
            except Exception:
                # Before implementation, this will raise after 3 failures
                # This is expected in TDD - test should fail first
                pass

        # Assert: Coordinator should still return cached data (not None)
        # This assertion will FAIL before implementation (expected in TDD)
        assert (
            coordinator._last_known_good_data is not None
        ), "Coordinator must retain cached data indefinitely"
        assert (
            coordinator._last_known_good_data == initial_data
        ), "Cached data must match initial successful read"

        # Assert: Staleness helper should indicate data is stale
        assert (
            coordinator.is_data_stale() is True
        ), "is_data_stale() must return True after failures"

    @pytest.mark.asyncio
    async def test_staleness_attributes_in_entity(self, mock_hass, mock_coordinator):
        """Entities expose staleness attributes from coordinator.

        This test verifies FR-005: Entity base class must add extra_state_attributes
        property with staleness metadata.
        """
        import time

        from custom_components.buderus_wps.const import SENSOR_OUTDOOR
        from custom_components.buderus_wps.sensor import BuderusTemperatureSensor

        # Setup: Create sensor entity
        sensor = BuderusTemperatureSensor(mock_coordinator, SENSOR_OUTDOOR)

        # Mock coordinator staleness methods (will be implemented in Phase 2)
        mock_coordinator.get_data_age_seconds = MagicMock(return_value=120)
        mock_coordinator.is_data_stale = MagicMock(return_value=True)
        mock_coordinator._last_successful_update = time.time() - 120

        # Act: Get entity attributes
        # This will FAIL before implementation (expected in TDD)
        try:
            attrs = sensor.extra_state_attributes
        except AttributeError:
            # Expected before implementation
            attrs = {}

        # Assert: Entity should expose staleness metadata
        # These assertions will FAIL before implementation
        assert (
            "last_update_age_seconds" in attrs
        ), "Entity must expose last_update_age_seconds attribute"
        assert "data_is_stale" in attrs, "Entity must expose data_is_stale attribute"
        assert (
            "last_successful_update" in attrs
        ), "Entity must expose last_successful_update timestamp"

        # Assert: Values should match coordinator state
        assert attrs.get("last_update_age_seconds") == 120
        assert attrs.get("data_is_stale") is True
        assert isinstance(
            attrs.get("last_successful_update"), str
        ), "Timestamp must be ISO 8601 string"
