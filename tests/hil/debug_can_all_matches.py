#!/usr/bin/env python3
"""Check ALL frames matching the response ID."""

import time
import logging
logging.basicConfig(level=logging.WARNING)

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()

# GT3_TEMP (idx=681)
idx = 681
request_id = 0x04003FE0 | (idx << 14)
response_id = 0x0C003FE0 | (idx << 14)
print(f"Looking for response ID: 0x{response_id:08X}")

# Send RTR request
request = CANMessage(arbitration_id=request_id, data=b'', is_extended_id=True, is_remote_frame=True)
adapter.flush_input_buffer()
slcan = request.to_usbtin_format()
print(f"Sent: {slcan}")
adapter._write_command(slcan.encode('ascii'))

# Collect ALL matching frames over 5 seconds
print("\nCollecting ALL frames with matching ID for 5 seconds...")
matches = []
start = time.time()
while time.time() - start < 5.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame:
        if frame.arbitration_id == response_id:
            matches.append((time.time() - start, frame.dlc, frame.data.hex() if frame.data else ''))
            print(f"  MATCH at {time.time()-start:.2f}s: dlc={frame.dlc} data={frame.data.hex() if frame.data else ''}")

print(f"\nTotal matches: {len(matches)}")
for t, dlc, data in matches:
    print(f"  t={t:.2f}s dlc={dlc} data=0x{data}")

adapter.disconnect()
