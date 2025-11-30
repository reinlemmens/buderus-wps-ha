"""
Contract tests for schedule encoding - T015.

These tests verify protocol fidelity for sw1/sw2 schedule encoding formats
as discovered through hardware testing.
"""

from datetime import time

import pytest

from buderus_wps.schedule_codec import ScheduleCodec, ScheduleSlot


class TestSw2ProtocolContract:
    """
    Contract tests for sw2 (DHW schedule) encoding.

    PROTOCOL: sw2 format stores schedules at odd indices (+1 from documented).
    Reference: Hardware testing 2025-11-28, research.md
    """

    def test_sw2_odd_index_returns_full_schedule(self):
        """
        PROTOCOL: Reading odd index (+1) returns 2 bytes with start AND end times.

        Hardware evidence:
        - Index 460 (documented): returns 1 byte (end time only)
        - Index 461 (odd/+1): returns 2 bytes (start AND end)
        """
        # The get_sw2_read_index() function applies the +1 offset
        assert ScheduleCodec.get_sw2_read_index(460) == 461
        assert ScheduleCodec.get_sw2_read_index(462) == 463

    def test_sw2_encoding_matches_hardware(self):
        """
        PROTOCOL: Encoding must match observed hardware values.

        Hardware evidence:
        - Index 461 returned 0x5A1E for schedule 13:00-15:00
        - 0x5A = 90 decimal, but we use only bits 0-5 = 26 (13:00 in 30-min slots)
        - 0x1E = 30 = 15:00 in 30-min slots

        Note: The high bits (6-7) may contain other flags; we mask to bits 0-5.
        """
        slot = ScheduleSlot(time(13, 0), time(15, 0))
        encoded = ScheduleCodec.encode(slot)

        # Our encoding produces clean slot values
        assert encoded[0] == 26  # 13:00 = slot 26
        assert encoded[1] == 30  # 15:00 = slot 30

    def test_sw2_decoding_masks_upper_bits(self):
        """
        PROTOCOL: Decoding must mask upper bits (6-7) to extract slot values.

        Some hardware returns values like 0x5A (90) where:
        - bits 0-5 = 011010 = 26 (the actual slot)
        - bits 6-7 = 01 (flags, ignored)
        """
        # Raw bytes as might come from hardware
        raw_with_flags = bytes([0x5A, 0x1E])  # 0x5A = 01011010, 0x1E = 00011110

        decoded = ScheduleCodec.decode(raw_with_flags)
        assert decoded.start_time == time(13, 0)
        assert decoded.end_time == time(15, 0)

    def test_dhw_schedule_parameter_indices(self):
        """
        PROTOCOL: DHW schedule parameters are at specific indices.

        Reference: FHEM 26_KM273v018.pm
        - DHW Program 1: Mon=460, Tue=462, Wed=464, Thu=466, Fri=468, Sat=470, Sun=472
        - DHW Program 2: Mon=474, Tue=476, Wed=478, Thu=480, Fri=482, Sat=484, Sun=486

        For reading full schedules, use odd index (+1).
        """
        # Program 1 indices
        p1_indices = [460, 462, 464, 466, 468, 470, 472]
        for idx in p1_indices:
            read_idx = ScheduleCodec.get_sw2_read_index(idx)
            assert read_idx == idx + 1

        # Program 2 indices
        p2_indices = [474, 476, 478, 480, 482, 484, 486]
        for idx in p2_indices:
            read_idx = ScheduleCodec.get_sw2_read_index(idx)
            assert read_idx == idx + 1


class TestSw1ProtocolContract:
    """
    Contract tests for sw1 (room schedule) encoding.

    PROTOCOL: sw1 format uses documented indices directly (no +1 offset needed).
    """

    def test_sw1_uses_documented_indices(self):
        """
        PROTOCOL: sw1 (room schedules) work at documented indices.

        Unlike sw2, room schedule parameters return 2-byte values
        at their documented indices.
        """
        # This is a placeholder - actual indices would come from FHEM reference
        # The key difference is sw1 doesn't need the +1 offset that sw2 needs
        pass


class TestScheduleSlotResolution:
    """Contract tests for schedule time resolution."""

    def test_dhw_requires_30_minute_resolution(self):
        """PROTOCOL: DHW schedules must be on 30-minute boundaries."""
        # Valid times
        valid_times = [
            time(0, 0),
            time(0, 30),
            time(6, 0),
            time(12, 30),
            time(23, 30),
        ]
        for t in valid_times:
            slot_num = ScheduleCodec.time_to_slot(t)
            assert 0 <= slot_num <= 47

    def test_dhw_rejects_15_minute_times(self):
        """PROTOCOL: DHW schedules cannot use 15-minute intervals."""
        invalid_times = [time(6, 15), time(12, 45), time(18, 15)]
        for t in invalid_times:
            with pytest.raises(Exception):  # ValidationError
                ScheduleCodec.time_to_slot(t)


class TestRoundTripEncoding:
    """Verify encode/decode round-trip preserves data."""

    @pytest.mark.parametrize(
        "start,end",
        [
            (time(0, 0), time(6, 0)),
            (time(6, 0), time(22, 0)),
            (time(13, 0), time(15, 0)),
            (time(0, 30), time(23, 30)),
        ],
    )
    def test_round_trip(self, start, end):
        """Encode then decode should return original values."""
        original = ScheduleSlot(start, end)
        encoded = ScheduleCodec.encode(original)
        decoded = ScheduleCodec.decode(encoded)

        assert decoded.start_time == original.start_time
        assert decoded.end_time == original.end_time
