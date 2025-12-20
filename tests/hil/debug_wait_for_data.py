#!/usr/bin/env python3
"""Debug script to wait for a second data frame after the 1-byte response."""

import logging
import time

logging.basicConfig(level=logging.INFO, format="%(message)s")

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

# GT3_TEMP (idx=681)
idx = 681
request_id = 0x04003FE0 | (idx << 14)
response_id = 0x0C003FE0 | (idx << 14)

print(f"Parameter: GT3_TEMP (idx={idx})")
print(f"Request ID:  0x{request_id:08X}")
print(f"Response ID: 0x{response_id:08X}")
print()

adapter = USBtinAdapter("/dev/ttyACM0", timeout=5.0)
adapter.connect()

# Send RTR request
request = CANMessage(
    arbitration_id=request_id, data=b"", is_extended_id=True, is_remote_frame=True
)

adapter.flush_input_buffer()
adapter._write_command(request.to_usbtin_format().encode("ascii"))

# Wait and collect ALL frames on the response ID for 10 seconds
print(f"Watching for frames on 0x{response_id:08X} for 10 seconds...")
print("(Also showing any other frames with 2-byte data that could be temperatures)")
print()

responses = []
temps = []
start = time.time()
while time.time() - start < 10.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame:
        elapsed = time.time() - start
        data_hex = frame.data.hex() if frame.data else ""

        if frame.arbitration_id == response_id:
            responses.append((elapsed, frame.dlc, data_hex))
            print(f"[{elapsed:5.2f}s] RESPONSE: dlc={frame.dlc} data=0x{data_hex}")

        # Also track any 2-byte frames that could be temperatures
        if frame.dlc == 2:
            raw = int(frame.data[:2].hex(), 16) if frame.data else 0
            if 0 < raw < 1000:  # Reasonable temp range (0.1 to 99.9°C)
                temp = raw / 10.0
                temps.append((elapsed, frame.arbitration_id, raw, temp))

print("\n=== Summary ===")
print(f"Responses on 0x{response_id:08X}: {len(responses)}")
for t, dlc, data in responses:
    print(f"  t={t:.2f}s dlc={dlc} data=0x{data}")

if len(responses) == 1 and responses[0][1] == 1:
    print("\n*** Only got 1-byte ACK, no 2-byte data frame followed ***")

if temps:
    print("\nOther 2-byte frames that look like temperatures:")
    unique_ids = {}
    for t, can_id, raw, temp in temps:
        if can_id not in unique_ids:
            unique_ids[can_id] = (raw, temp)
            idx_from_id = (
                ((can_id ^ 0x0C003FE0) >> 14) if (can_id & 0x3FFF) == 0x3FE0 else None
            )
            if idx_from_id is not None and idx_from_id > 0 and idx_from_id < 4096:
                print(
                    f"  0x{can_id:08X} (idx={idx_from_id}): {temp}°C (raw=0x{raw:04X})"
                )
            else:
                print(f"  0x{can_id:08X}: {temp}°C (raw=0x{raw:04X})")

adapter.disconnect()
