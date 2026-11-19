"""Unit tests for room setpoint control via the room thermostat CAN frame."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from custom_components.buderus_wps.buderus_wps.room_thermostat import (
    ROOM_SETPOINT_CIRCUITS,
    WriteRateLimiter,
    build_room_setpoint_frame,
    decode_active_setpoint,
    thermostat_setpoint_can_id,
    validate_room_setpoint,
)


class TestThermostatFrame:
    """The frame must match what the real thermostats send (captured 2026-11-19)."""

    def test_c4_can_id_matches_captured_thermostat_frame(self):
        assert thermostat_setpoint_can_id(4) == 0x0C048063

    def test_c3_can_id_matches_verified_frame(self):
        assert thermostat_setpoint_can_id(3) == 0x0C048062

    def test_frame_payload_is_big_endian_tenths(self):
        frame = build_room_setpoint_frame(4, 20.5)
        assert frame.arbitration_id == 0x0C048063
        assert frame.data == bytes.fromhex("00cd")
        assert frame.is_extended_id is True
        assert not frame.is_remote_frame

    def test_c3_23_degrees(self):
        assert build_room_setpoint_frame(3, 23.0).data == bytes.fromhex("00e6")

    def test_only_verified_circuits_supported(self):
        assert sorted(ROOM_SETPOINT_CIRCUITS) == [3, 4]


class TestValidation:
    @pytest.mark.parametrize("circuit", [0, 1, 2, 5])
    def test_rejects_unverified_circuits(self, circuit):
        with pytest.raises(ValueError, match="not supported"):
            validate_room_setpoint(circuit, 20.0)

    @pytest.mark.parametrize("temp", [14.5, 25.5, -1.0, 99.0])
    def test_rejects_out_of_range(self, temp):
        with pytest.raises(ValueError, match="between"):
            validate_room_setpoint(3, temp)

    def test_rejects_non_half_degree(self):
        with pytest.raises(ValueError, match="multiple of 0.5"):
            validate_room_setpoint(3, 21.3)

    @pytest.mark.parametrize("temp,raw", [(15.0, 150), (21.5, 215), (25.0, 250)])
    def test_accepts_valid(self, temp, raw):
        assert validate_room_setpoint(4, temp) == raw


class TestDecodeActive:
    @pytest.mark.parametrize("raw,expected", [(225, 22.5), (205, 20.5), ("230", 23.0)])
    def test_decodes_tenths(self, raw, expected):
        assert decode_active_setpoint(raw) == expected

    @pytest.mark.parametrize("raw", [None, "abc", True, -21555, 0xDEAD, 0])
    def test_rejects_missing_and_sentinels(self, raw):
        assert decode_active_setpoint(raw) is None


class TestWriteRateLimiter:
    def test_allows_up_to_max_then_blocks(self):
        lim = WriteRateLimiter(max_writes=2, window_s=100)
        assert lim.allowed(3, now=0)
        lim.record(3, now=0)
        lim.record(3, now=10)
        assert not lim.allowed(3, now=20)
        assert lim.retry_after(3, now=20) == pytest.approx(80)

    def test_window_expires(self):
        lim = WriteRateLimiter(max_writes=1, window_s=100)
        lim.record(3, now=0)
        assert not lim.allowed(3, now=99)
        assert lim.allowed(3, now=100)
        assert lim.retry_after(3, now=100) == 0.0

    def test_circuits_are_independent(self):
        lim = WriteRateLimiter(max_writes=1, window_s=100)
        lim.record(3, now=0)
        assert lim.allowed(4, now=1)


class TestCoordinatorRoomSetpoint:
    @pytest.fixture
    def coordinator(self, mock_hass):
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coord = BuderusCoordinator(mock_hass, "/dev/ttyACM0", 60)
        coord.hass = mock_hass
        coord._adapter = MagicMock()
        coord._connected = True
        coord._client = MagicMock()
        return coord

    @pytest.mark.asyncio
    async def test_set_sends_thermostat_frame(self, coordinator):
        await coordinator.async_set_room_setpoint(4, 21.0)
        coordinator._adapter.send_frame_nowait.assert_called_once()
        frame = coordinator._adapter.send_frame_nowait.call_args[0][0]
        assert frame.arbitration_id == 0x0C048063
        assert frame.data == bytes.fromhex("00d2")

    @pytest.mark.asyncio
    async def test_never_writes_pump_parameters(self, coordinator):
        await coordinator.async_set_room_setpoint(3, 22.0)
        coordinator._client.write_value.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_value_sends_nothing(self, coordinator):
        with pytest.raises(ValueError):
            await coordinator.async_set_room_setpoint(3, 30.0)
        coordinator._adapter.send_frame_nowait.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_and_sends_nothing(self, coordinator):
        from custom_components.buderus_wps.coordinator import HomeAssistantError

        coordinator._room_setpoint_limiter = WriteRateLimiter(
            max_writes=1, window_s=3600
        )
        await coordinator.async_set_room_setpoint(3, 22.0)
        with pytest.raises(HomeAssistantError, match="too often"):
            await coordinator.async_set_room_setpoint(3, 22.5)
        assert coordinator._adapter.send_frame_nowait.call_count == 1
        # Other circuit unaffected
        await coordinator.async_set_room_setpoint(4, 20.0)
        assert coordinator._adapter.send_frame_nowait.call_count == 2

    @pytest.mark.asyncio
    async def test_failed_send_does_not_use_quota(self, coordinator):
        coordinator._room_setpoint_limiter = WriteRateLimiter(
            max_writes=1, window_s=3600
        )
        coordinator._adapter.send_frame_nowait.side_effect = OSError("serial")
        with pytest.raises(OSError):
            await coordinator.async_set_room_setpoint(3, 22.0)
        coordinator._adapter.send_frame_nowait.side_effect = None
        await coordinator.async_set_room_setpoint(3, 22.0)

    @pytest.mark.asyncio
    async def test_not_connected_raises(self, coordinator):
        from custom_components.buderus_wps.coordinator import HomeAssistantError

        coordinator._connected = False
        with pytest.raises(HomeAssistantError, match="Not connected"):
            await coordinator.async_set_room_setpoint(3, 22.0)

    @pytest.mark.asyncio
    async def test_busy_lock_times_out_and_sends_nothing(
        self, coordinator, monkeypatch
    ):
        from custom_components.buderus_wps import coordinator as coord_mod
        from custom_components.buderus_wps.coordinator import HomeAssistantError

        monkeypatch.setattr(coord_mod, "LOCK_ACQUIRE_TIMEOUT", 0.05)
        # Python 3.9 binds a Lock to the loop current at creation; make it here.
        coordinator._lock = asyncio.Lock()
        await coordinator._lock.acquire()
        try:
            with pytest.raises(HomeAssistantError, match="Timeout"):
                await coordinator.async_set_room_setpoint(3, 22.0)
        finally:
            coordinator._lock.release()
        coordinator._adapter.send_frame_nowait.assert_not_called()
        # The failed attempt must not consume the rate-limit quota or the lock
        await coordinator.async_set_room_setpoint(3, 22.0)
        assert not coordinator._lock.locked()

    def test_read_room_setpoints(self, coordinator):
        coordinator._last_known_good_data = None
        reads = {"MV_T5_SETPOINT_ACTUAL_2": 225, "MV_T5_SETPOINT_ACTUAL_3": 205}
        coordinator._client.read_parameter.side_effect = lambda n: {"decoded": reads[n]}
        assert coordinator._sync_read_room_setpoints() == {3: 22.5, 4: 20.5}

    def test_read_failure_keeps_last_known_value(self, coordinator):
        prev = MagicMock()
        prev.room_setpoint_active = {3: 22.5, 4: 20.5}
        coordinator._last_known_good_data = prev

        def read(name):
            if name == "MV_T5_SETPOINT_ACTUAL_3":
                raise TimeoutError("no answer")
            return {"decoded": 230}

        coordinator._client.read_parameter.side_effect = read
        assert coordinator._sync_read_room_setpoints() == {3: 23.0, 4: 20.5}
