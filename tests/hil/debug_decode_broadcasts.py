#!/usr/bin/env python3
"""Decode broadcast CAN IDs to find their parameter indices."""

import time
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from buderus_wps import USBtinAdapter
from buderus_wps.parameter_registry import ParameterRegistry

registry = ParameterRegistry()

print("Listening for broadcast frames with 2-byte temperature data...")
print("Will try to match CAN IDs to known parameters.\n")

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()

# Collect unique IDs with their data
seen_ids = {}
start = time.time()

# First, build a reverse lookup from response CAN ID to parameter
response_id_to_param = {}
for param in registry._by_idx.values():
    # Response ID for this parameter
    resp_id = 0x0C003FE0 | (param.idx << 14)
    response_id_to_param[resp_id] = param

print(f"Built lookup table with {len(response_id_to_param)} parameters")
print("Listening for 15 seconds...\n")

while time.time() - start < 15.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame and frame.dlc >= 2:
        can_id = frame.arbitration_id
        if can_id not in seen_ids:
            data_hex = frame.data.hex() if frame.data else ""
            raw = int(frame.data[:2].hex(), 16) if frame.data else 0

            # Check if this matches a known parameter
            param = response_id_to_param.get(can_id)
            if param:
                if param.format == "tem":
                    temp = raw / 10.0
                    print(f"MATCH: 0x{can_id:08X} -> {param.text} (idx={param.idx}): {temp}°C (raw=0x{raw:04X})")
                else:
                    print(f"MATCH: 0x{can_id:08X} -> {param.text} (idx={param.idx}): raw=0x{raw:04X}")
            else:
                # Try to decode the ID structure
                # Check if it matches base 0x3FE0 or other bases
                base = can_id & 0x3FFF  # Lower 14 bits
                idx_part = (can_id >> 14) & 0xFFF  # Bits 25-14 (12 bits)
                prefix = can_id >> 26  # Upper bits

                temp = raw / 10.0 if 0 < raw < 1500 else None

                # Try to find parameter by idx
                param_by_idx = registry.get_by_index(idx_part)

                if param_by_idx:
                    if temp and param_by_idx.format == "tem":
                        print(f"IDX MATCH: 0x{can_id:08X} base=0x{base:04X} idx={idx_part} -> {param_by_idx.text}: {temp}°C")
                    else:
                        print(f"IDX MATCH: 0x{can_id:08X} base=0x{base:04X} idx={idx_part} -> {param_by_idx.text}: raw=0x{raw:04X}")
                elif temp:
                    print(f"UNKNOWN: 0x{can_id:08X} base=0x{base:04X} idx={idx_part}: {temp}°C (raw=0x{raw:04X})")

            seen_ids[can_id] = (frame.dlc, data_hex)

print(f"\n=== Summary ===")
print(f"Total unique 2+ byte frames seen: {len(seen_ids)}")

# Specifically check for frames with base 0x3FE0 (our parameter base)
print(f"\nFrames with base 0x3FE0 (our parameter base):")
count = 0
for can_id in sorted(seen_ids.keys()):
    base = can_id & 0x3FFF
    if base == 0x3FE0:
        count += 1
        dlc, data = seen_ids[can_id]
        print(f"  0x{can_id:08X}: dlc={dlc} data={data}")
if count == 0:
    print("  (none found)")

adapter.disconnect()
