"""
Unit tests for ScheduleCodec - T016.

Tests the schedule encoding/decoding functionality for sw1/sw2 formats.
"""

from datetime import time

import pytest

from buderus_wps.schedule_codec import ScheduleCodec, ScheduleSlot, WeeklySchedule
from buderus_wps.exceptions import ValidationError


class TestTimeToSlot:
    """Test ScheduleCodec.time_to_slot() conversion."""

    def test_midnight(self):
        """Slot 0 = 00:00."""
        assert ScheduleCodec.time_to_slot(time(0, 0)) == 0

    def test_half_past_midnight(self):
        """Slot 1 = 00:30."""
        assert ScheduleCodec.time_to_slot(time(0, 30)) == 1

    def test_one_am(self):
        """Slot 2 = 01:00."""
        assert ScheduleCodec.time_to_slot(time(1, 0)) == 2

    def test_noon(self):
        """Slot 24 = 12:00."""
        assert ScheduleCodec.time_to_slot(time(12, 0)) == 24

    def test_one_pm(self):
        """Slot 26 = 13:00."""
        assert ScheduleCodec.time_to_slot(time(13, 0)) == 26

    def test_three_pm(self):
        """Slot 30 = 15:00."""
        assert ScheduleCodec.time_to_slot(time(15, 0)) == 30

    def test_eleven_thirty_pm(self):
        """Slot 47 = 23:30."""
        assert ScheduleCodec.time_to_slot(time(23, 30)) == 47

    def test_invalid_time_not_on_boundary(self):
        """Raise ValidationError for non-30-minute boundary."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCodec.time_to_slot(time(13, 15))
        assert "30-minute boundary" in str(exc_info.value)

    def test_invalid_time_with_seconds(self):
        """Raise ValidationError for time with seconds."""
        with pytest.raises(ValidationError):
            ScheduleCodec.time_to_slot(time(13, 0, 30))


class TestSlotToTime:
    """Test ScheduleCodec.slot_to_time() conversion."""

    def test_slot_0(self):
        """Slot 0 = 00:00."""
        assert ScheduleCodec.slot_to_time(0) == time(0, 0)

    def test_slot_1(self):
        """Slot 1 = 00:30."""
        assert ScheduleCodec.slot_to_time(1) == time(0, 30)

    def test_slot_26(self):
        """Slot 26 = 13:00."""
        assert ScheduleCodec.slot_to_time(26) == time(13, 0)

    def test_slot_30(self):
        """Slot 30 = 15:00."""
        assert ScheduleCodec.slot_to_time(30) == time(15, 0)

    def test_slot_47(self):
        """Slot 47 = 23:30."""
        assert ScheduleCodec.slot_to_time(47) == time(23, 30)

    def test_invalid_slot_negative(self):
        """Raise ValueError for negative slot."""
        with pytest.raises(ValueError):
            ScheduleCodec.slot_to_time(-1)

    def test_invalid_slot_too_high(self):
        """Raise ValueError for slot > 47."""
        with pytest.raises(ValueError):
            ScheduleCodec.slot_to_time(48)


class TestEncode:
    """Test ScheduleCodec.encode() method."""

    def test_encode_morning_slot(self):
        """Encode 06:00-22:00."""
        slot = ScheduleSlot(time(6, 0), time(22, 0))
        encoded = ScheduleCodec.encode(slot)
        assert encoded == bytes([12, 44])  # start=12, end=44

    def test_encode_13_00_to_15_00(self):
        """Encode 13:00-15:00 (from hardware testing)."""
        slot = ScheduleSlot(time(13, 0), time(15, 0))
        encoded = ScheduleCodec.encode(slot)
        # start=26 (0x1A), end=30 (0x1E)
        assert encoded == bytes([26, 30])

    def test_encode_full_day(self):
        """Encode 00:00-23:30."""
        slot = ScheduleSlot(time(0, 0), time(23, 30))
        encoded = ScheduleCodec.encode(slot)
        assert encoded == bytes([0, 47])


class TestDecode:
    """Test ScheduleCodec.decode() method."""

    def test_decode_morning_slot(self):
        """Decode 06:00-22:00."""
        decoded = ScheduleCodec.decode(bytes([12, 44]))
        assert decoded.start_time == time(6, 0)
        assert decoded.end_time == time(22, 0)

    def test_decode_13_00_to_15_00(self):
        """Decode 0x1A1E (from hardware testing - 13:00-15:00)."""
        decoded = ScheduleCodec.decode(bytes([26, 30]))
        assert decoded.start_time == time(13, 0)
        assert decoded.end_time == time(15, 0)

    def test_decode_masks_upper_bits(self):
        """Decode ignores bits 6-7 (uses only bits 0-5)."""
        # 0xDA = 11011010 -> bits 0-5 = 011010 = 26
        # 0x9E = 10011110 -> bits 0-5 = 011110 = 30
        decoded = ScheduleCodec.decode(bytes([0xDA, 0x9E]))
        assert decoded.start_time == time(13, 0)  # slot 26
        assert decoded.end_time == time(15, 0)  # slot 30

    def test_decode_too_short_raises(self):
        """Raise ValueError for data shorter than 2 bytes."""
        with pytest.raises(ValueError):
            ScheduleCodec.decode(bytes([26]))


class TestGetSw2ReadIndex:
    """Test ScheduleCodec.get_sw2_read_index() for odd-index fix."""

    def test_dhw_monday_p1(self):
        """DHW Monday Program 1: documented 460 -> read 461."""
        assert ScheduleCodec.get_sw2_read_index(460) == 461

    def test_dhw_tuesday_p1(self):
        """DHW Tuesday Program 1: documented 462 -> read 463."""
        assert ScheduleCodec.get_sw2_read_index(462) == 463

    def test_dhw_sunday_p2(self):
        """DHW Sunday Program 2: documented 486 -> read 487."""
        assert ScheduleCodec.get_sw2_read_index(486) == 487


class TestScheduleSlot:
    """Test ScheduleSlot dataclass."""

    def test_is_active_within_slot(self):
        """Time within slot returns True."""
        slot = ScheduleSlot(time(6, 0), time(22, 0))
        assert slot.is_active(time(12, 0))
        assert slot.is_active(time(6, 0))  # Start is inclusive
        assert slot.is_active(time(21, 59))

    def test_is_active_outside_slot(self):
        """Time outside slot returns False."""
        slot = ScheduleSlot(time(6, 0), time(22, 0))
        assert not slot.is_active(time(5, 59))
        assert not slot.is_active(time(22, 0))  # End is exclusive
        assert not slot.is_active(time(23, 0))

    def test_validate_success(self):
        """Valid slot passes validation."""
        slot = ScheduleSlot(time(6, 0), time(22, 0))
        slot.validate()  # Should not raise

    def test_validate_bad_start_time(self):
        """Invalid start time raises ValidationError."""
        slot = ScheduleSlot(time(6, 15), time(22, 0))
        with pytest.raises(ValidationError) as exc_info:
            slot.validate()
        assert "start_time" in str(exc_info.value)

    def test_validate_bad_end_time(self):
        """Invalid end time raises ValidationError."""
        slot = ScheduleSlot(time(6, 0), time(22, 15))
        with pytest.raises(ValidationError) as exc_info:
            slot.validate()
        assert "end_time" in str(exc_info.value)

    def test_validate_start_after_end(self):
        """Start >= end raises ValidationError."""
        slot = ScheduleSlot(time(22, 0), time(6, 0))
        with pytest.raises(ValidationError) as exc_info:
            slot.validate()
        assert "before end_time" in str(exc_info.value)


class TestWeeklySchedule:
    """Test WeeklySchedule dataclass."""

    @pytest.fixture
    def sample_schedule(self):
        """Create a sample weekly schedule."""
        default_slot = ScheduleSlot(time(6, 0), time(22, 0))
        weekend_slot = ScheduleSlot(time(7, 30), time(23, 30))
        return WeeklySchedule(
            monday=default_slot,
            tuesday=default_slot,
            wednesday=default_slot,
            thursday=default_slot,
            friday=default_slot,
            saturday=weekend_slot,
            sunday=weekend_slot,
        )

    def test_get_day_monday(self, sample_schedule):
        """Get Monday (day 0)."""
        slot = sample_schedule.get_day(0)
        assert slot.start_time == time(6, 0)

    def test_get_day_sunday(self, sample_schedule):
        """Get Sunday (day 6)."""
        slot = sample_schedule.get_day(6)
        assert slot.start_time == time(7, 30)

    def test_get_day_invalid(self, sample_schedule):
        """Invalid day raises ValueError."""
        with pytest.raises(ValueError):
            sample_schedule.get_day(7)

    def test_set_day_creates_new_schedule(self, sample_schedule):
        """set_day returns new schedule without modifying original."""
        new_slot = ScheduleSlot(time(8, 0), time(20, 0))
        new_schedule = sample_schedule.set_day(0, new_slot)

        # New schedule has updated Monday
        assert new_schedule.monday.start_time == time(8, 0)

        # Original is unchanged
        assert sample_schedule.monday.start_time == time(6, 0)
