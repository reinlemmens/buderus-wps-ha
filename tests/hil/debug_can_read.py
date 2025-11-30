#!/usr/bin/env python3
"""Debug script to see all CAN frames received after a read request."""

import time
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()

# Send RTR for GT3_TEMP (idx=681)
request_id = 0x04003FE0 | (681 << 14)
response_id = 0x0C003FE0 | (681 << 14)
print(f"Request ID: 0x{request_id:08X}")
print(f"Expected response ID: 0x{response_id:08X}")

request = CANMessage(arbitration_id=request_id, data=b'', is_extended_id=True, is_remote_frame=True)
adapter.flush_input_buffer()

# Send request manually
slcan = request.to_usbtin_format()
print(f"Sending: {slcan}")
adapter._write_command(slcan.encode('ascii'))

# Read multiple responses over 3 seconds
print("\nReceiving frames for 3 seconds...")
start = time.time()
frame_count = 0
while time.time() - start < 3.0:
    frame = adapter._read_frame(timeout=0.5)
    if frame:
        frame_count += 1
        match = "MATCH!" if frame.arbitration_id == response_id else ""
        print(f"Frame {frame_count}: id=0x{frame.arbitration_id:08X} dlc={frame.dlc} data={frame.data.hex() if frame.data else ''} {match}")
    else:
        print("  (timeout)")

print(f"\nTotal frames received: {frame_count}")
adapter.disconnect()
