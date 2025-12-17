#!/usr/bin/env python3
"""Find which broadcast position contains the actual DHW tank temperature.

Run this script and compare the broadcast temperatures with your heat pump display.
Look for the value that matches 27.2°C (or current actual DHW temp on your display).
"""

import sys
import time

sys.path.insert(0, '.')

try:
    from buderus_wps.broadcast_monitor import BroadcastMonitor, KNOWN_BROADCASTS
    from buderus_wps.can_adapter import USBtinAdapter
except ImportError as e:
    print(f"Import error: {e}")
    print("\nThis script must be run on the system with the USBtin adapter.")
    print("Install dependencies: pip install pyserial")
    sys.exit(1)

print("=" * 70)
print("DHW Temperature Broadcast Position Finder")
print("=" * 70)
print("\nListening to CAN bus for 10 seconds...")
print("Please check your heat pump display for the ACTUAL hot water temperature.")
print()

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()  # Must connect first!
monitor = BroadcastMonitor(adapter)

try:
    # Collect broadcasts
    cache = monitor.collect(duration=10.0)

    print("\n" + "=" * 70)
    print("ALL TEMPERATURE READINGS (10-70°C range)")
    print("=" * 70)
    print(f"{'Base':<10} {'Idx':<6} {'Temp':<10} {'Known Name':<30}")
    print("-" * 70)

    # Collect all temperature readings in DHW range (10-70°C)
    dhw_candidates = []

    for reading in sorted(cache.readings.values(), key=lambda r: (r.base, r.idx)):
        if reading.is_temperature and 10.0 <= reading.temperature <= 70.0:
            known = KNOWN_BROADCASTS.get((reading.base, reading.idx))
            name = known[0] if known else f"UNKNOWN_{reading.idx}"

            print(f"0x{reading.base:04X}     {reading.idx:<6} {reading.temperature:>6.1f}°C   {name}")

            # Highlight potential DHW candidates (20-60°C range)
            if 20.0 <= reading.temperature <= 60.0:
                dhw_candidates.append((reading.base, reading.idx, reading.temperature, name))

    print("\n" + "=" * 70)
    print("POTENTIAL DHW TEMPERATURE CANDIDATES (20-60°C)")
    print("=" * 70)
    print(f"{'Base':<10} {'Idx':<6} {'Temp':<10} {'Current Mapping':<30}")
    print("-" * 70)

    for base, idx, temp, name in dhw_candidates:
        current = ">>> CURRENTLY USED <<<" if idx == 58 else ""
        print(f"0x{base:04X}     {idx:<6} {temp:>6.1f}°C   {name:<30} {current}")

    print("\n" + "=" * 70)
    print("INSTRUCTIONS")
    print("=" * 70)
    print("1. Look at your heat pump's physical display for 'Hot Water' temperature")
    print("2. Find which row above matches that temperature")
    print("3. Note the Base and Idx values for that row")
    print("4. Report these values so we can update the configuration")
    print()
    print("Current mapping: Base=0x0060-0x0063, Idx=58")
    print(f"Current reading: {cache.get_by_idx_and_base(58, 0x0060).temperature if cache.get_by_idx_and_base(58, 0x0060) else 'N/A'}°C")
    print()

    # Check if we found anything close to 27.2°C
    close_matches = [(b, i, t, n) for b, i, t, n in dhw_candidates if abs(t - 27.2) < 1.0]
    if close_matches:
        print("\n!!! POSSIBLE MATCHES near 27.2°C !!!")
        for base, idx, temp, name in close_matches:
            print(f"  Base=0x{base:04X}, Idx={idx}, Temp={temp:.1f}°C ({name})")

finally:
    adapter.disconnect()
    print("\n" + "=" * 70)
