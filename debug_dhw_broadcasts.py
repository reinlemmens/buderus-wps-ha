#!/usr/bin/env python3
"""Debug DHW temperature broadcast positions."""

import sys

sys.path.insert(0, ".")

from buderus_wps.broadcast_monitor import KNOWN_BROADCASTS, BroadcastMonitor
from buderus_wps.can_adapter import USBtinAdapter

print("=== DHW Temperature Broadcast Debug ===\n")
print("Listening to CAN broadcasts for 10 seconds...")
print("Will show all temperature readings on base 0x0060-0x0063\n")

adapter = USBtinAdapter("/dev/ttyACM0", timeout=5.0)
monitor = BroadcastMonitor(adapter)

try:
    # Collect broadcasts
    cache = monitor.collect(duration=10.0)

    print("\n=== Temperature Readings Found ===")
    print(f"{'Base':<8} {'Idx':<5} {'Temperature':<12} {'Name':<30}")
    print("-" * 65)

    # Group by base
    for base in [0x0060, 0x0061, 0x0062, 0x0063, 0x0270, 0x0402]:
        found_any = False
        for reading in sorted(cache.readings.values(), key=lambda r: r.idx):
            if reading.base == base and reading.is_temperature:
                known_name = KNOWN_BROADCASTS.get(
                    (base, reading.idx), (f"UNKNOWN_{reading.idx}", "")
                )[0]
                print(
                    f"0x{base:04X}   {reading.idx:<5} {reading.temperature:>6.1f}°C     {known_name}"
                )
                found_any = True
        if found_any:
            print()

    # Specifically highlight positions around idx 58
    print("\n=== Focus on idx 58 (Currently Used for DHW) ===")
    for base in [0x0060, 0x0061, 0x0062, 0x0063]:
        reading = cache.get_by_idx_and_base(58, base)
        if reading:
            print(f"Base 0x{base:04X}, idx 58: {reading.temperature:.1f}°C")

    # Check nearby positions that might be actual DHW tank temp
    print("\n=== Nearby Positions (idx 33, 59, 60) ===")
    for idx in [33, 59, 60]:
        for base in [0x0060, 0x0061, 0x0062, 0x0063]:
            reading = cache.get_by_idx_and_base(idx, base)
            if reading:
                known_name = KNOWN_BROADCASTS.get((base, idx), ("UNKNOWN", ""))[0]
                print(
                    f"Base 0x{base:04X}, idx {idx}: {reading.temperature:.1f}°C ({known_name})"
                )

finally:
    adapter.disconnect()

print("\n=== Instructions ===")
print("Please compare these temperatures with your heat pump's physical menu.")
print("Look for which temperature matches the 27.2°C you see on the menu.")
