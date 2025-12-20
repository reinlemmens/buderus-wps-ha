#!/usr/bin/env python3
"""Test multiple requests to same parameter."""

import time

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

adapter = USBtinAdapter("/dev/ttyACM0", timeout=5.0)
adapter.connect()

idx = 681  # GT3_TEMP
request_id = 0x04003FE0 | (idx << 14)
response_id = 0x0C003FE0 | (idx << 14)

print(f"Testing GT3_TEMP (idx={idx})")
print(f"Response ID: 0x{response_id:08X}\n")

for i in range(5):
    request = CANMessage(
        arbitration_id=request_id, data=b"", is_extended_id=True, is_remote_frame=True
    )
    adapter.flush_input_buffer()
    adapter._write_command(request.to_usbtin_format().encode("ascii"))

    frame = adapter._read_frame(timeout=1.0)
    while frame and frame.arbitration_id != response_id:
        frame = adapter._read_frame(timeout=0.5)

    if frame:
        data_hex = frame.data.hex() if frame.data else ""
        print(f"Request {i+1}: dlc={frame.dlc} data=0x{data_hex}")
    else:
        print(f"Request {i+1}: timeout")
    time.sleep(0.5)

adapter.disconnect()
