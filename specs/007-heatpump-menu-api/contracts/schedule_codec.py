"""
API Contract: Schedule Codec

This file defines the interface for encoding/decoding schedule times
between human-readable format and the heat pump's internal representation.

Note: This is a design document, not implementation code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import time
from typing import Tuple


@dataclass
class ScheduleSlot:
    """A time slot with start and end times."""

    start_time: time
    end_time: time


class ScheduleCodec(ABC):
    """
    Encode/decode schedule times for CAN communication.

    The heat pump uses different encoding formats:
    - sw1 (room schedules): 2 bytes at documented index
    - sw2 (DHW schedules): 2 bytes at odd index (+1 from documented)

    Both formats use the same encoding:
    - High byte bits 0-5: start slot (30-minute increments)
    - Low byte bits 0-5: end slot (30-minute increments)
    - Slot 0 = 00:00, Slot 1 = 00:30, ..., Slot 47 = 23:30
    """

    @staticmethod
    @abstractmethod
    def encode(slot: ScheduleSlot) -> bytes:
        """
        Encode a schedule slot to 2-byte format.

        Args:
            slot: ScheduleSlot with start_time and end_time

        Returns:
            2 bytes in heat pump format

        Raises:
            ValidationError: If times not on 30-minute boundaries

        Example:
            >>> slot = ScheduleSlot(time(13, 0), time(15, 0))
            >>> ScheduleCodec.encode(slot)
            b'\\x5a\\x1e'  # start=26 (13:00), end=30 (15:00)
        """
        ...

    @staticmethod
    @abstractmethod
    def decode(data: bytes) -> ScheduleSlot:
        """
        Decode 2-byte format to a schedule slot.

        Args:
            data: 2 bytes from heat pump

        Returns:
            ScheduleSlot with start_time and end_time

        Example:
            >>> ScheduleCodec.decode(b'\\x5a\\x1e')
            ScheduleSlot(start_time=time(13, 0), end_time=time(15, 0))
        """
        ...

    @staticmethod
    @abstractmethod
    def time_to_slot(t: time) -> int:
        """
        Convert time to 30-minute slot number.

        Args:
            t: Time value

        Returns:
            Slot number (0-47)

        Raises:
            ValidationError: If time not on 30-minute boundary

        Example:
            >>> ScheduleCodec.time_to_slot(time(13, 0))
            26
            >>> ScheduleCodec.time_to_slot(time(13, 30))
            27
        """
        ...

    @staticmethod
    @abstractmethod
    def slot_to_time(slot: int) -> time:
        """
        Convert 30-minute slot number to time.

        Args:
            slot: Slot number (0-47)

        Returns:
            Time value

        Example:
            >>> ScheduleCodec.slot_to_time(26)
            time(13, 0)
            >>> ScheduleCodec.slot_to_time(30)
            time(15, 0)
        """
        ...

    @staticmethod
    @abstractmethod
    def validate_dhw_time(t: time) -> None:
        """
        Validate time is on 30-minute boundary for DHW schedules.

        Args:
            t: Time to validate

        Raises:
            ValidationError: If not on 30-minute boundary
        """
        ...

    @staticmethod
    @abstractmethod
    def get_sw2_read_index(documented_index: int) -> int:
        """
        Get the actual parameter index for reading sw2 (DHW) schedules.

        The documented indices only return end time (1 byte).
        To get both start and end times, read from index + 1.

        Args:
            documented_index: Index from FHEM documentation

        Returns:
            Actual index to read (documented_index + 1)

        Example:
            >>> ScheduleCodec.get_sw2_read_index(460)  # DHW_TIMER_P1_MONDAY
            461  # Returns 2 bytes with start+end
        """
        ...
