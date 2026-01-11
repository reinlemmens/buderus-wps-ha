#!/usr/bin/env python3
"""Quick test to check specific broadcast positions for DHW temperature.

This is a simpler version that just checks the most likely candidates.
"""

import sys

sys.path.insert(0, ".")

from buderus_wps.broadcast_monitor import BroadcastMonitor
from buderus_wps.can_adapter import USBtinAdapter

# Candidates based on protocol documentation
CANDIDATES = [
    (0x0060, 33, "Common sensor / Room temp C0"),
    (0x0060, 58, "DHW_TEMP_ACTUAL (currently used - WRONG)"),
    (0x0060, 59, "Brine/ground temp"),
    (0x0060, 60, "Supply setpoint"),
    (0x0061, 33, "Common sensor / Room temp C1"),
    (0x0062, 33, "Common sensor / Room temp C2"),
    (0x0063, 33, "Common sensor / Room temp C3"),
    (0x0270, 0, "Supply Line Temp"),
    (0x0270, 1, "Compressor Discharge"),
    (0x0270, 4, "Heat Exchanger"),
    (0x0270, 5, "Condenser Out"),
    (0x0270, 6, "Flow Temp"),
]

print("Testing broadcast positions for DHW temperature...")
print("Looking for value near 27.2°C\n")

adapter = USBtinAdapter("/dev/ttyACM0", timeout=5.0)
monitor = BroadcastMonitor(adapter)

try:
    print("Collecting broadcast data for 10 seconds...")
    cache = monitor.collect(duration=10.0)
    print()

    print("=" * 80)
    print(f"{'Base':<12} {'Idx':<6} {'Temperature':<15} {'Description':<40}")
    print("=" * 80)

    found_match = False
    for base, idx, description in CANDIDATES:
        reading = cache.get_by_idx_and_base(idx, base)
        if reading and reading.is_temperature:
            temp = reading.temperature
            marker = ""
            if abs(temp - 27.2) < 1.0:
                marker = " <<< MATCH!"
                found_match = True
            elif idx == 58:
                marker = " (currently used)"

            print(
                f"0x{base:04X}       {idx:<6} {temp:>6.1f}°C        {description:<40}{marker}"
            )
        else:
            print(
                f"0x{base:04X}       {idx:<6} {'---':<15} {description:<40} (not found)"
            )

    print("=" * 80)

    if not found_match:
        print("\nNo exact match found for 27.2°C.")
        print("Showing all temperatures in 20-35°C range:")
        print()
        for reading in sorted(
            cache.readings.values(),
            key=lambda r: r.temperature if r.is_temperature else 999,
        ):
            if reading.is_temperature and 20.0 <= reading.temperature <= 35.0:
                print(
                    f"  Base=0x{reading.base:04X}, Idx={reading.idx:3d}: {reading.temperature:5.1f}°C"
                )

finally:
    adapter.disconnect()

print("\nNext step: Report the matching Base and Idx values")
