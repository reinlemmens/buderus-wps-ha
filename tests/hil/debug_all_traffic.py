#!/usr/bin/env python3
"""Debug script to capture ALL CAN traffic after RTR request."""

import logging
import time

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s")

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

# Build and send RTR request
request = CANMessage(
    arbitration_id=request_id, data=b"", is_extended_id=True, is_remote_frame=True
)
slcan = request.to_usbtin_format()
print(f"Sending SLCAN: {repr(slcan)}")

adapter.flush_input_buffer()
adapter._write_command(slcan.encode("ascii"))

# Read ALL frames for 5 seconds
print("\n=== Capturing ALL frames for 5 seconds ===\n")
frames = []
start = time.time()
while time.time() - start < 5.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame:
        elapsed = time.time() - start
        is_response = frame.arbitration_id == response_id
        marker = "*** RESPONSE ***" if is_response else ""
        data_hex = frame.data.hex() if frame.data else ""
        print(
            f"[{elapsed:5.2f}s] ID=0x{frame.arbitration_id:08X} DLC={frame.dlc} DATA={data_hex:16s} {marker}"
        )
        frames.append((elapsed, frame))

print("\n=== Summary ===")
print(f"Total frames received: {len(frames)}")

# Group by ID
by_id = {}
for elapsed, frame in frames:
    fid = frame.arbitration_id
    if fid not in by_id:
        by_id[fid] = []
    by_id[fid].append((elapsed, frame.dlc, frame.data.hex() if frame.data else ""))

print(f"\nUnique IDs seen: {len(by_id)}")
print("\nFrames by ID:")
for fid in sorted(by_id.keys()):
    items = by_id[fid]
    is_resp = " <-- EXPECTED RESPONSE ID" if fid == response_id else ""
    is_req = " <-- REQUEST ID" if fid == request_id else ""
    print(f"  0x{fid:08X}: {len(items)} frames{is_resp}{is_req}")
    for t, dlc, data in items[:3]:  # Show first 3
        print(f"    t={t:.2f}s dlc={dlc} data={data}")
    if len(items) > 3:
        print(f"    ... and {len(items)-3} more")

# Specifically check for responses
responses = by_id.get(response_id, [])
if responses:
    print(f"\n=== Response frames on 0x{response_id:08X} ===")
    for t, dlc, data in responses:
        # Try to decode as temperature if 2+ bytes
        if dlc >= 2:
            raw_val = int(data[:4], 16) if len(data) >= 4 else 0
            temp = raw_val / 10.0
            print(f"  t={t:.2f}s dlc={dlc} data=0x{data} -> {temp}°C")
        else:
            print(f"  t={t:.2f}s dlc={dlc} data=0x{data}")
else:
    print(f"\n*** NO FRAMES RECEIVED ON EXPECTED RESPONSE ID 0x{response_id:08X} ***")

adapter.disconnect()
