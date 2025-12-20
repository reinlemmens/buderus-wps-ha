#!/usr/bin/env python3
"""Debug script to try data frame request instead of RTR."""

import logging
import time

logging.basicConfig(level=logging.DEBUG, format="%(message)s")

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

adapter = USBtinAdapter("/dev/ttyACM0", timeout=5.0)
adapter.connect()

# GT3_TEMP (idx=681)
idx = 681
request_id = 0x04003FE0 | (idx << 14)
response_id = 0x0C003FE0 | (idx << 14)
print(f"Parameter: GT3_TEMP (idx={idx})")
print(f"Request ID: 0x{request_id:08X}")
print(f"Response ID: 0x{response_id:08X}")

# Try 1: RTR request (what we currently do)
print("\n=== Method 1: RTR Request ===")
request = CANMessage(
    arbitration_id=request_id, data=b"", is_extended_id=True, is_remote_frame=True
)
adapter.flush_input_buffer()
slcan = request.to_usbtin_format()
print(f"Sending: {slcan}")
adapter._write_command(slcan.encode("ascii"))

start = time.time()
while time.time() - start < 1.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame and frame.arbitration_id == response_id:
        print(
            f"Response: id=0x{frame.arbitration_id:08X} dlc={frame.dlc} data={frame.data.hex()}"
        )
        break

# Try 2: Data frame with empty data
print("\n=== Method 2: Data Frame (empty) ===")
request = CANMessage(
    arbitration_id=request_id, data=b"", is_extended_id=True, is_remote_frame=False
)
adapter.flush_input_buffer()
slcan = request.to_usbtin_format()
print(f"Sending: {slcan}")
adapter._write_command(slcan.encode("ascii"))

start = time.time()
while time.time() - start < 1.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame and frame.arbitration_id == response_id:
        print(
            f"Response: id=0x{frame.arbitration_id:08X} dlc={frame.dlc} data={frame.data.hex()}"
        )
        break

# Try 3: Data frame with 0x00 byte
print("\n=== Method 3: Data Frame (0x00) ===")
request = CANMessage(
    arbitration_id=request_id, data=b"\x00", is_extended_id=True, is_remote_frame=False
)
adapter.flush_input_buffer()
slcan = request.to_usbtin_format()
print(f"Sending: {slcan}")
adapter._write_command(slcan.encode("ascii"))

start = time.time()
while time.time() - start < 1.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame and frame.arbitration_id == response_id:
        print(
            f"Response: id=0x{frame.arbitration_id:08X} dlc={frame.dlc} data={frame.data.hex()}"
        )
        break

adapter.disconnect()
