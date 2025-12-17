"""
Broadcast monitor for reading CAN bus traffic passively.

The Buderus heat pump broadcasts sensor values on various CAN IDs using
different base addresses:
- Base 0x0060-0x0063: Temperature sensors (different circuits/modules)
- Base 0x0402-0x0403: Circulation/pump data
- Base 0x0270: Status data

This module provides passive monitoring to capture these broadcast values
without relying on RTR request/response patterns.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable, Any

from .can_adapter import USBtinAdapter
from .can_message import CANMessage


@dataclass
class BroadcastReading:
    """A single reading captured from broadcast traffic."""
    can_id: int
    base: int  # Lower 14 bits
    idx: int   # Bits 25-14 (12 bits)
    dlc: int
    raw_data: bytes
    raw_value: int
    timestamp: float

    @property
    def is_temperature(self) -> bool:
        """Check if this looks like a temperature value."""
        # 2-byte value in reasonable temp range (0.1 to 150.0°C)
        return self.dlc == 2 and 1 <= self.raw_value <= 1500

    @property
    def temperature(self) -> Optional[float]:
        """Decode as temperature (tenths of degree C)."""
        if self.dlc >= 2:
            return self.raw_value / 10.0
        return None

    @property
    def circuit(self) -> Optional[int]:
        """Get circuit number from base (0x0060=0, 0x0061=1, etc.)."""
        if 0x0060 <= self.base <= 0x0063:
            return self.base - 0x0060
        return None


@dataclass
class BroadcastCache:
    """Cache of recent broadcast readings."""
    readings: Dict[int, BroadcastReading] = field(default_factory=dict)

    def update(self, reading: BroadcastReading) -> None:
        """Update cache with new reading."""
        self.readings[reading.can_id] = reading

    def get(self, can_id: int) -> Optional[BroadcastReading]:
        """Get cached reading by CAN ID."""
        return self.readings.get(can_id)

    def get_by_idx_and_base(self, idx: int, base: int) -> Optional[BroadcastReading]:
        """Get cached reading by idx and base.

        Searches all readings for one matching the given idx and base,
        since the high bits of the CAN ID can vary.
        """
        for reading in self.readings.values():
            if reading.idx == idx and reading.base == base:
                return reading
        return None

    def get_temperatures(self, circuit: Optional[int] = None) -> List[BroadcastReading]:
        """Get all temperature readings, optionally filtered by circuit."""
        temps = [r for r in self.readings.values() if r.is_temperature]
        if circuit is not None:
            temps = [r for r in temps if r.circuit == circuit]
        return sorted(temps, key=lambda r: r.idx)

    def clear(self) -> None:
        """Clear the cache."""
        self.readings.clear()


# Known broadcast ID mappings based on observed traffic
# Format: (base, idx) -> (name, format)
KNOWN_BROADCASTS: Dict[tuple, tuple] = {
    # Outdoor temperature (idx=12 on all circuit bases) - Hardware verified
    (0x0060, 12): ("OUTDOOR_TEMP_C0", "tem"),
    (0x0061, 12): ("OUTDOOR_TEMP_C1", "tem"),
    (0x0062, 12): ("OUTDOOR_TEMP_C2", "tem"),
    (0x0063, 12): ("OUTDOOR_TEMP_C3", "tem"),

    # RC10 Room Controller - Circuit 1 (base 0x0060) - Hardware verified
    (0x0060, 0): ("RC10_C1_ROOM_TEMP", "tem"),      # Room temperature
    (0x0060, 18): ("RC10_C1_DEMAND_TEMP", "tem"),   # Demand/setpoint temperature
    (0x0060, 83): ("RC10_C1_ROOM_TEMP_COPY", "tem"),  # Room temperature (copy)

    # RC10 Room Controller - Circuit 3 (base 0x0402) - Hardware verified
    (0x0402, 55): ("RC10_C3_ROOM_TEMP", "tem"),     # Room temperature
    (0x0402, 78): ("DHW_TEMP_ACTUAL", "tem"),       # ACTUAL DHW tank temp (~27°C)
    (0x0402, 98): ("RC10_C3_ROOM_TEMP_COPY", "tem"),  # Room temperature (copy)
    (0x0402, 107): ("RC10_C3_DEMAND_TEMP", "tem"),  # Demand/setpoint temperature
    (0x0403, 78): ("DHW_TEMP_ACTUAL_COPY", "tem"),  # ACTUAL DHW tank temp (copy)

    # Demand setpoint (idx=18 on circuit bases) - Hardware verified
    (0x0062, 18): ("DEMAND_TEMP_C2", "tem"),  # Circuit 2 demand

    # Base 0x0060 - Circuit 0 / Main
    (0x0060, 33): ("SENSOR_TEMP_C0_33", "tem"),
    (0x0060, 58): ("DHW_SETPOINT_OR_SUPPLY", "tem"),  # ~54°C - NOT actual tank temp!
    (0x0060, 59): ("SENSOR_TEMP_C0_59", "tem"),
    (0x0060, 60): ("SENSOR_TEMP_C0_60", "tem"),

    # Base 0x0061 - Circuit 1
    (0x0061, 33): ("SENSOR_TEMP_C1_33", "tem"),
    (0x0061, 58): ("SENSOR_TEMP_C1_58", "tem"),
    (0x0061, 59): ("SENSOR_TEMP_C1_59", "tem"),
    (0x0061, 60): ("SENSOR_TEMP_C1_60", "tem"),

    # Base 0x0062 - Circuit 2
    (0x0062, 33): ("SENSOR_TEMP_C2_33", "tem"),
    (0x0062, 58): ("SENSOR_TEMP_C2_58", "tem"),
    (0x0062, 59): ("SENSOR_TEMP_C2_59", "tem"),
    (0x0062, 60): ("SENSOR_TEMP_C2_60", "tem"),

    # Base 0x0063 - Circuit 3
    (0x0063, 33): ("SENSOR_TEMP_C3_33", "tem"),
    (0x0063, 58): ("SENSOR_TEMP_C3_58", "tem"),
    (0x0063, 59): ("SENSOR_TEMP_C3_59", "tem"),
    (0x0063, 60): ("SENSOR_TEMP_C3_60", "tem"),

    # Base 0x0270 - Buffer tank temperatures - Hardware verified
    (0x0270, 5): ("GT9_TEMP", "tem"),   # Buffer tank bottom/return
    (0x0270, 6): ("GT8_TEMP", "tem"),   # Buffer tank top/supply
}


# Mapping from standard parameter names to broadcast (base, idx)
# Used by CLI read command for broadcast fallback
# Maps FHEM parameter names to their broadcast equivalents
# Mapping from standard parameter names to broadcast idx
# For temperature sensors, we search across all circuit bases (0x0060-0x0063)
# For other sensors, we specify the exact base
PARAM_TO_BROADCAST: Dict[str, tuple] = {
    # Outdoor temperature - idx=12, broadcasts on varying circuit bases
    "GT2_TEMP": (None, 12),  # None = search all circuit bases
    # DHW temperature - idx=78 on base 0x0402/0x0403 (CORRECTED 2025-12-16)
    # Previous mapping (idx=58) was wrong, reading ~54°C instead of actual ~27°C
    "GT3_TEMP": (0x0402, 78),  # Actual DHW tank temperature
    # Buffer tank temperatures - base 0x0270 - Hardware verified
    "GT8_TEMP": (0x0270, 6),  # Buffer tank top/supply (~46°C observed)
    "GT9_TEMP": (0x0270, 5),  # Buffer tank bottom/return (~43°C observed)
    # Room temperature sensors - specific circuits
    "RC10_C1_ROOM_TEMP": (0x0060, 0),
    "RC10_C3_ROOM_TEMP": (0x0402, 55),
}

# Circuit base addresses for temperature broadcasts
CIRCUIT_BASES = [0x0060, 0x0061, 0x0062, 0x0063]


def get_broadcast_for_param(param_name: str) -> Optional[tuple]:
    """
    Get broadcast (base, idx) tuple for a parameter name.

    Args:
        param_name: Parameter name (case-insensitive)

    Returns:
        Tuple of (base, idx) or None if not found in broadcast mapping
    """
    return PARAM_TO_BROADCAST.get(param_name.upper())


def is_temperature_param(param_format: str) -> bool:
    """
    Check if a parameter format indicates a temperature value.

    Args:
        param_format: The format string from parameter definition

    Returns:
        True if parameter is a temperature type
    """
    return param_format == "tem" or param_format.startswith("temp")


def decode_can_id(can_id: int) -> tuple:
    """
    Decode CAN ID into components.

    Returns:
        (direction, idx, base) where:
        - direction: upper bits (0x0C for response/broadcast)
        - idx: bits 25-14 (12-bit index)
        - base: bits 13-0 (14-bit base address)
    """
    base = can_id & 0x3FFF
    idx = (can_id >> 14) & 0xFFF
    direction = can_id >> 26
    return (direction, idx, base)


def encode_can_id(direction: int, idx: int, base: int) -> int:
    """Encode components into CAN ID."""
    return (direction << 26) | (idx << 14) | base


class BroadcastMonitor:
    """
    Monitor CAN bus for broadcast messages.

    Usage:
        monitor = BroadcastMonitor(adapter)

        # Collect readings for 5 seconds
        cache = monitor.collect(duration=5.0)

        # Get temperature readings
        for reading in cache.get_temperatures():
            print(f"{reading.can_id:08X}: {reading.temperature}°C")
    """

    def __init__(
        self,
        adapter: USBtinAdapter,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._adapter = adapter
        self._logger = logger or logging.getLogger(__name__)
        self._cache = BroadcastCache()
        self._callbacks: List[Callable[[BroadcastReading], None]] = []

    @property
    def cache(self) -> BroadcastCache:
        """Access the reading cache."""
        return self._cache

    def add_callback(self, callback: Callable[[BroadcastReading], None]) -> None:
        """Add callback to be called for each new reading."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[BroadcastReading], None]) -> None:
        """Remove a callback."""
        self._callbacks.remove(callback)

    def _process_frame(self, frame: CANMessage) -> Optional[BroadcastReading]:
        """Process a CAN frame into a BroadcastReading."""
        if frame.dlc < 1:
            return None

        direction, idx, base = decode_can_id(frame.arbitration_id)

        # Parse raw value (big-endian)
        raw_value = 0
        for byte in frame.data[:min(frame.dlc, 4)]:
            raw_value = (raw_value << 8) | byte

        reading = BroadcastReading(
            can_id=frame.arbitration_id,
            base=base,
            idx=idx,
            dlc=frame.dlc,
            raw_data=bytes(frame.data),
            raw_value=raw_value,
            timestamp=time.time(),
        )

        return reading

    def collect(
        self,
        duration: float = 5.0,
        filter_func: Optional[Callable[[BroadcastReading], bool]] = None,
    ) -> BroadcastCache:
        """
        Collect broadcast readings for specified duration.

        Args:
            duration: How long to collect (seconds)
            filter_func: Optional filter to select which readings to keep

        Returns:
            BroadcastCache with collected readings
        """
        if not self._adapter.is_open:
            raise RuntimeError("Adapter not connected")

        self._cache.clear()
        start = time.time()

        while time.time() - start < duration:
            try:
                frame = self._adapter._read_frame(timeout=0.1)
                if frame:
                    reading = self._process_frame(frame)
                    if reading:
                        if filter_func is None or filter_func(reading):
                            self._cache.update(reading)
                            for callback in self._callbacks:
                                try:
                                    callback(reading)
                                except Exception as e:
                                    self._logger.warning("Callback error: %s", e)
            except Exception as e:
                self._logger.debug("Read error: %s", e)

        return self._cache

    def collect_temperatures(self, duration: float = 5.0) -> List[BroadcastReading]:
        """
        Collect temperature readings for specified duration.

        Args:
            duration: How long to collect (seconds)

        Returns:
            List of temperature readings
        """
        def is_temp(r: BroadcastReading) -> bool:
            return r.is_temperature

        cache = self.collect(duration=duration, filter_func=is_temp)
        return cache.get_temperatures()

    def get_known_name(self, reading: BroadcastReading) -> Optional[str]:
        """Get known parameter name for a reading."""
        key = (reading.base, reading.idx)
        if key in KNOWN_BROADCASTS:
            return KNOWN_BROADCASTS[key][0]
        return None

    def find_dhw_temperature(self, duration: float = 5.0) -> Optional[float]:
        """
        Find the DHW (hot water) temperature from broadcast traffic.

        Looks for readings on base 0x0060 with idx=58 which appears to be
        the DHW actual temperature based on observed values (~54°C).

        Args:
            duration: How long to monitor

        Returns:
            Temperature in °C or None if not found
        """
        cache = self.collect(duration=duration)
        reading = cache.get_by_idx_and_base(idx=58, base=0x0060)
        if reading and reading.is_temperature:
            return reading.temperature
        return None
