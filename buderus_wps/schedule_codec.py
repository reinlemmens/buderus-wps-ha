"""
Schedule encoding/decoding for Heat Pump Menu API.

This module handles conversion between human-readable time formats
and the heat pump's internal schedule representation.

Schedule Encoding (sw1/sw2 format):
- High byte bits 0-5: Start time slot (30-minute increments)
- Low byte bits 0-5: End time slot (30-minute increments)
- Slot 0 = 00:00, Slot 1 = 00:30, ..., Slot 47 = 23:30

sw2 Format Discovery:
- Documented indices (460, 462, etc.) return only 1 byte (end time)
- Odd indices (+1: 461, 463, etc.) return 2 bytes with both start and end
- Use get_sw2_read_index() to get correct index for full schedule data
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

from .exceptions import ValidationError


@dataclass(frozen=True)
class ScheduleSlot:
    """
    A time period within a daily schedule.

    Attributes:
        start_time: Start of active period (HH:MM)
        end_time: End of active period (HH:MM)
    """

    start_time: time
    end_time: time

    def is_active(self, at: time) -> bool:
        """Check if the given time falls within this slot."""
        return self.start_time <= at < self.end_time

    def validate(self, resolution_minutes: int = 30) -> None:
        """
        Validate time boundaries against resolution.

        Args:
            resolution_minutes: Required time resolution (default 30 for DHW)

        Raises:
            ValidationError: If times don't align with resolution
        """
        for t, name in [(self.start_time, "start_time"), (self.end_time, "end_time")]:
            if t.minute % resolution_minutes != 0 or t.second != 0:
                raise ValidationError(
                    field=name,
                    value=t.strftime("%H:%M"),
                    constraint=f"must be on {resolution_minutes}-minute boundary",
                )

        if self.start_time >= self.end_time:
            raise ValidationError(
                field="schedule",
                value=f"{self.start_time}-{self.end_time}",
                constraint="start_time must be before end_time",
            )


@dataclass
class WeeklySchedule:
    """A complete weekly schedule with slots for each day."""

    monday: ScheduleSlot
    tuesday: ScheduleSlot
    wednesday: ScheduleSlot
    thursday: ScheduleSlot
    friday: ScheduleSlot
    saturday: ScheduleSlot
    sunday: ScheduleSlot

    def get_day(self, day: int) -> ScheduleSlot:
        """
        Get schedule for day.

        Args:
            day: Day index (0=Monday, 6=Sunday)

        Returns:
            ScheduleSlot for the specified day
        """
        days = [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ]
        if not 0 <= day <= 6:
            raise ValueError(f"Day must be 0-6, got {day}")
        return days[day]

    def set_day(self, day: int, slot: ScheduleSlot) -> "WeeklySchedule":
        """
        Create a new WeeklySchedule with one day modified.

        Args:
            day: Day index (0=Monday, 6=Sunday)
            slot: New ScheduleSlot for the day

        Returns:
            New WeeklySchedule with the modification
        """
        days = [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ]
        if not 0 <= day <= 6:
            raise ValueError(f"Day must be 0-6, got {day}")
        days[day] = slot
        return WeeklySchedule(*days)


class ScheduleCodec:
    """
    Encode/decode schedule times for CAN communication.

    The heat pump uses 30-minute slots encoded as:
    - High byte: start slot (0-47)
    - Low byte: end slot (0-47)
    """

    SLOT_MINUTES = 30
    MAX_SLOT = 47  # 23:30

    @staticmethod
    def time_to_slot(t: time) -> int:
        """
        Convert time to 30-minute slot number.

        Args:
            t: Time value

        Returns:
            Slot number (0-47)

        Raises:
            ValidationError: If time not on 30-minute boundary
        """
        if t.minute % ScheduleCodec.SLOT_MINUTES != 0 or t.second != 0:
            raise ValidationError(
                field="time",
                value=t.strftime("%H:%M:%S"),
                constraint="must be on 30-minute boundary",
            )
        return t.hour * 2 + t.minute // ScheduleCodec.SLOT_MINUTES

    @staticmethod
    def slot_to_time(slot: int) -> time:
        """
        Convert 30-minute slot number to time.

        Args:
            slot: Slot number (0-47)

        Returns:
            Time value
        """
        if not 0 <= slot <= ScheduleCodec.MAX_SLOT:
            raise ValueError(f"Slot must be 0-47, got {slot}")
        hours = slot // 2
        minutes = (slot % 2) * ScheduleCodec.SLOT_MINUTES
        return time(hours, minutes)

    @staticmethod
    def encode(slot: ScheduleSlot) -> bytes:
        """
        Encode a schedule slot to 2-byte format.

        Args:
            slot: ScheduleSlot with start_time and end_time

        Returns:
            2 bytes in heat pump format (high=start, low=end)

        Raises:
            ValidationError: If times not on 30-minute boundaries
        """
        start_slot = ScheduleCodec.time_to_slot(slot.start_time)
        end_slot = ScheduleCodec.time_to_slot(slot.end_time)
        return bytes([start_slot, end_slot])

    @staticmethod
    def decode(data: bytes) -> ScheduleSlot:
        """
        Decode 2-byte format to a schedule slot.

        Args:
            data: 2 bytes from heat pump

        Returns:
            ScheduleSlot with start_time and end_time
        """
        if len(data) < 2:
            raise ValueError(f"Expected 2 bytes, got {len(data)}")
        start_slot = data[0] & 0x3F  # bits 0-5
        end_slot = data[1] & 0x3F  # bits 0-5
        return ScheduleSlot(
            start_time=ScheduleCodec.slot_to_time(start_slot),
            end_time=ScheduleCodec.slot_to_time(end_slot),
        )

    @staticmethod
    def get_sw2_read_index(documented_index: int) -> int:
        """
        Get the actual parameter index for reading sw2 (DHW) schedules.

        The documented indices only return end time (1 byte).
        To get both start and end times, read from index + 1.

        PROTOCOL: sw2 format stores full schedule at odd indices (+1 from documented).
        Reference: Hardware testing 2025-11-28, research.md

        Args:
            documented_index: Index from FHEM documentation

        Returns:
            Actual index to read (documented_index + 1)
        """
        return documented_index + 1

    @staticmethod
    def validate_dhw_time(t: time) -> None:
        """
        Validate time is on 30-minute boundary for DHW schedules.

        Args:
            t: Time to validate

        Raises:
            ValidationError: If not on 30-minute boundary
        """
        if t.minute % 30 != 0 or t.second != 0:
            raise ValidationError(
                field="time",
                value=t.strftime("%H:%M"),
                constraint="DHW schedules must be on 30-minute boundaries",
            )
