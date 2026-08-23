"""Tests for the update-cycle timeout and stall watchdog (issue #10).

A hung serial read (or a stuck lock holder) used to block
_async_update_data forever: no logs, no reconnect, entities unavailable
until a config-entry reload. The coordinator now bounds every update
cycle with UPDATE_CYCLE_TIMEOUT and force-rebuilds the connection (with
a fresh lock object) after repeated timeouts or a prolonged stall.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.buderus_wps import coordinator as coordinator_module
from custom_components.buderus_wps.coordinator import (
    UPDATE_TIMEOUTS_BEFORE_RESET,
    BuderusCoordinator,
)


def _make_coordinator(mock_hass) -> BuderusCoordinator:
    coordinator = BuderusCoordinator(mock_hass, "/dev/ttyUSB0", 60)
    coordinator.hass = mock_hass  # Mock parent doesn't set this
    return coordinator


class TestUpdateCycleTimeout:
    """A wedged update cycle must surface instead of hanging forever."""

    @pytest.mark.asyncio
    async def test_timeout_returns_stale_data(self, mock_hass, monkeypatch):
        """A cycle exceeding the timeout returns cached data, not a hang."""
        monkeypatch.setattr(coordinator_module, "UPDATE_CYCLE_TIMEOUT", 0.05)
        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True

        stale = MagicMock(name="stale_data")
        coordinator._last_known_good_data = stale

        async def hang() -> None:
            await asyncio.sleep(5)

        coordinator._async_update_data_inner = hang  # type: ignore[assignment]

        result = await asyncio.wait_for(coordinator._async_update_data(), timeout=1.0)

        assert result is stale
        assert coordinator._consecutive_update_timeouts == 1
        assert coordinator._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_timeout_without_cache_raises_update_failed(
        self, mock_hass, monkeypatch
    ):
        """With no cached data, a timed-out cycle raises UpdateFailed."""
        UpdateFailed = coordinator_module.UpdateFailed

        monkeypatch.setattr(coordinator_module, "UPDATE_CYCLE_TIMEOUT", 0.05)
        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True

        async def hang() -> None:
            await asyncio.sleep(5)

        coordinator._async_update_data_inner = hang  # type: ignore[assignment]

        with pytest.raises(UpdateFailed):
            await asyncio.wait_for(coordinator._async_update_data(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_repeated_timeouts_force_reconnect(self, mock_hass, monkeypatch):
        """After UPDATE_TIMEOUTS_BEFORE_RESET timeouts the connection rebuilds."""
        monkeypatch.setattr(coordinator_module, "UPDATE_CYCLE_TIMEOUT", 0.05)
        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True
        coordinator._last_known_good_data = MagicMock(name="stale_data")
        old_lock = coordinator._lock

        async def hang() -> None:
            await asyncio.sleep(5)

        coordinator._async_update_data_inner = hang  # type: ignore[assignment]

        for _ in range(UPDATE_TIMEOUTS_BEFORE_RESET):
            await asyncio.wait_for(coordinator._async_update_data(), timeout=1.0)

        # Forced reconnect: disconnected, fresh lock, backoff task scheduled
        assert coordinator._connected is False
        assert coordinator._lock is not old_lock
        assert coordinator._consecutive_update_timeouts == 0
        mock_hass.async_create_background_task.assert_called()

    @pytest.mark.asyncio
    async def test_successful_update_resets_timeout_counter(self, mock_hass):
        """A completed cycle clears the consecutive-timeout counter."""
        coordinator = _make_coordinator(mock_hass)
        coordinator._consecutive_update_timeouts = 1
        fresh = MagicMock(name="fresh_data")

        async def ok() -> MagicMock:
            return fresh

        coordinator._async_update_data_inner = ok  # type: ignore[assignment]

        result = await coordinator._async_update_data()

        assert result is fresh
        assert coordinator._consecutive_update_timeouts == 0


class TestForceReconnect:
    """_async_force_reconnect must recover even from a poisoned lock."""

    @pytest.mark.asyncio
    async def test_force_reconnect_replaces_held_lock(self, mock_hass):
        """A lock held by a wedged task must not leak into the new session."""
        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True

        await coordinator._lock.acquire()  # Simulate a stuck holder
        old_lock = coordinator._lock

        await coordinator._async_force_reconnect()

        assert coordinator._lock is not old_lock
        assert not coordinator._lock.locked()
        assert coordinator._connected is False

    @pytest.mark.asyncio
    async def test_force_reconnect_survives_disconnect_error(self, mock_hass):
        """A failing serial close must not stop the rebuild."""
        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True
        mock_hass.async_add_executor_job = AsyncMock(side_effect=OSError("port gone"))

        await coordinator._async_force_reconnect()

        assert coordinator._connected is False
        mock_hass.async_create_background_task.assert_called()


class TestStallWatchdog:
    """The watchdog rebuilds the connection when updates stall silently."""

    @pytest.mark.asyncio
    async def test_watchdog_starts_on_setup(self, mock_hass):
        """async_setup starts the watchdog background task."""
        coordinator = _make_coordinator(mock_hass)
        coordinator._sync_connect = MagicMock()

        assert await coordinator.async_setup() is True

        assert coordinator._watchdog_task is not None
        # Close the un-awaited coroutine handed to the mocked task factory
        mock_hass.async_create_background_task.call_args[0][0].close()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_watchdog(self, mock_hass):
        """async_shutdown cancels the watchdog task."""
        coordinator = _make_coordinator(mock_hass)
        mock_task = MagicMock()
        coordinator._watchdog_task = mock_task
        mock_hass.async_add_executor_job = AsyncMock()

        await coordinator.async_shutdown()

        mock_task.cancel.assert_called_once()
        assert coordinator._watchdog_task is None

    @pytest.mark.asyncio
    async def test_watchdog_forces_rebuild_on_stall(self, mock_hass, monkeypatch):
        """No successful update for many intervals triggers a forced rebuild."""
        import time

        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True
        coordinator._last_successful_update = time.time() - 10_000

        forced = AsyncMock()
        coordinator._async_force_reconnect = forced  # type: ignore[assignment]

        real_sleep = asyncio.sleep

        async def one_check(delay: float) -> None:
            # Let one loop iteration run, then cancel
            if forced.await_count:
                raise asyncio.CancelledError
            await real_sleep(0)

        monkeypatch.setattr(coordinator_module.asyncio, "sleep", one_check)

        with pytest.raises(asyncio.CancelledError):
            await coordinator._watchdog_loop()

        forced.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_watchdog_skips_manual_disconnect(self, mock_hass, monkeypatch):
        """The watchdog never rebuilds while manually disconnected for CLI use."""
        import time

        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True
        coordinator._manually_disconnected = True
        coordinator._last_successful_update = time.time() - 10_000

        forced = AsyncMock()
        coordinator._async_force_reconnect = forced  # type: ignore[assignment]

        real_sleep = asyncio.sleep
        calls = {"n": 0}

        async def two_checks(delay: float) -> None:
            calls["n"] += 1
            if calls["n"] > 2:
                raise asyncio.CancelledError
            await real_sleep(0)

        monkeypatch.setattr(coordinator_module.asyncio, "sleep", two_checks)

        with pytest.raises(asyncio.CancelledError):
            await coordinator._watchdog_loop()

        forced.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_watchdog_covers_cold_start_stall(self, mock_hass, monkeypatch):
        """A coordinator that wedges on its very first poll still gets rescued."""
        import time

        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True
        coordinator._last_successful_update = None  # No update ever succeeded
        coordinator._watchdog_reference_time = time.time() - 10_000

        forced = AsyncMock()
        coordinator._async_force_reconnect = forced  # type: ignore[assignment]

        real_sleep = asyncio.sleep

        async def one_check(delay: float) -> None:
            if forced.await_count:
                raise asyncio.CancelledError
            await real_sleep(0)

        monkeypatch.setattr(coordinator_module.asyncio, "sleep", one_check)

        with pytest.raises(asyncio.CancelledError):
            await coordinator._watchdog_loop()

        forced.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_watchdog_survives_rebuild_failure(self, mock_hass, monkeypatch):
        """A raising rebuild must not kill the watchdog loop."""
        import time

        coordinator = _make_coordinator(mock_hass)
        coordinator._connected = True
        coordinator._last_successful_update = time.time() - 10_000

        forced = AsyncMock(side_effect=RuntimeError("rebuild exploded"))
        coordinator._async_force_reconnect = forced  # type: ignore[assignment]

        real_sleep = asyncio.sleep

        async def two_checks(delay: float) -> None:
            # Stop only after the loop survived one failing rebuild
            if forced.await_count >= 2:
                raise asyncio.CancelledError
            await real_sleep(0)

        monkeypatch.setattr(coordinator_module.asyncio, "sleep", two_checks)

        with pytest.raises(asyncio.CancelledError):
            await coordinator._watchdog_loop()

        assert forced.await_count >= 2
