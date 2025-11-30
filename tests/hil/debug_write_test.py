#!/usr/bin/env python3
"""Test write operation to XDHW_TIME parameter."""

import time
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

# XDHW_TIME (idx=2475, format=int, min=0, max=48)
# Setting to 1 should activate extra DHW for 30 minutes
idx = 2475
name = "XDHW_TIME"
request_id = 0x04003FE0 | (idx << 14)
response_id = 0x0C003FE0 | (idx << 14)

print(f"Parameter: {name} (idx={idx})")
print(f"Request/Write ID: 0x{request_id:08X}")
print(f"Response ID:      0x{response_id:08X}")
print()

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()

# Step 1: Read current value
print("Step 1: Read current value")
request = CANMessage(
    arbitration_id=request_id,
    data=b'',
    is_extended_id=True,
    is_remote_frame=True
)
adapter.flush_input_buffer()
adapter._write_command(request.to_usbtin_format().encode('ascii'))

start = time.time()
while time.time() - start < 2.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame and frame.arbitration_id == response_id:
        print(f"  Response: dlc={frame.dlc} data={frame.data.hex()}")
        break

time.sleep(0.5)

# Step 2: Write value 1 (30 minutes extra DHW)
print("\nStep 2: Write value 1")
# FHEM format: T<CAN_ID>2<data_hex_4chars> for 2-byte write
# Value 1 as 2 bytes big-endian = 0x0001
write_value = 1
data = write_value.to_bytes(2, 'big')

write_msg = CANMessage(
    arbitration_id=request_id,  # Same ID as RTR request
    data=data,
    is_extended_id=True,
    is_remote_frame=False
)
adapter.flush_input_buffer()
slcan = write_msg.to_usbtin_format()
print(f"  Sending: {slcan.strip()}")
adapter._write_command(slcan.encode('ascii'))

# Check for response/ack
print("  Waiting for response...")
start = time.time()
while time.time() - start < 2.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame:
        if frame.arbitration_id == response_id:
            print(f"  Response on expected ID: dlc={frame.dlc} data={frame.data.hex()}")
        elif frame.arbitration_id == request_id:
            print(f"  Echo on request ID: dlc={frame.dlc} data={frame.data.hex()}")

time.sleep(0.5)

# Step 3: Read back to verify
print("\nStep 3: Read back value")
request = CANMessage(
    arbitration_id=request_id,
    data=b'',
    is_extended_id=True,
    is_remote_frame=True
)
adapter.flush_input_buffer()
adapter._write_command(request.to_usbtin_format().encode('ascii'))

start = time.time()
while time.time() - start < 2.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame and frame.arbitration_id == response_id:
        print(f"  Response: dlc={frame.dlc} data={frame.data.hex()}")
        if frame.dlc == 1:
            print(f"  Value: {frame.data[0]}")
        elif frame.dlc >= 2:
            val = int.from_bytes(frame.data[:2], 'big')
            print(f"  Value: {val}")
        break

print("\n=== Done ===")
print("Check heat pump display to see if extra DHW is activated!")
adapter.disconnect()
