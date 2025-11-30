#!/usr/bin/env python3
"""Try to request element list from heat pump like FHEM does."""

import time
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

print("Attempting to request element list from heat pump...")
print("(This is what FHEM does during initialization)\n")

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()

# Step 1: Send RTR to 0x01FD7FE0 to request element count
# (FHEM: CAN_Write($hash,"R01FD7FE00"))
count_request_id = 0x01FD7FE0
count_response_id = 0x09FD7FE0  # Guessing based on pattern

print(f"Step 1: Request element count via RTR to 0x{count_request_id:08X}")
request = CANMessage(
    arbitration_id=count_request_id,
    data=b'',
    is_extended_id=True,
    is_remote_frame=True
)
adapter.flush_input_buffer()
adapter._write_command(request.to_usbtin_format().encode('ascii'))

# Wait for response
print("Waiting for response...")
responses = []
start = time.time()
while time.time() - start < 3.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame:
        data_hex = frame.data.hex() if frame.data else ""
        print(f"  Received: ID=0x{frame.arbitration_id:08X} DLC={frame.dlc} DATA={data_hex}")
        responses.append(frame)
        if frame.arbitration_id in (count_response_id, 0x09FDBFE0):
            print("    ^ This could be the element count response!")

if not responses:
    print("  (no response)")

# Step 2: Try to request element data (FHEM: T01FD3FE08<size><offset>)
print(f"\nStep 2: Request element data via data frame to 0x01FD3FE0")
data_request_id = 0x01FD3FE0
# FHEM sends: T01FD3FE08<size in 4 bytes><offset in 4 bytes>
# Let's try requesting 256 bytes from offset 0
size = 256
offset = 0
data = size.to_bytes(4, 'big') + offset.to_bytes(4, 'big')
request = CANMessage(
    arbitration_id=data_request_id,
    data=data,
    is_extended_id=True,
    is_remote_frame=False
)
adapter.flush_input_buffer()
slcan = request.to_usbtin_format()
print(f"  Sending: {slcan.strip()}")
adapter._write_command(slcan.encode('ascii'))

# Then send RTR to 0x01FDBFE0 to request the data
print(f"Step 3: Send RTR to 0x01FDBFE0 to retrieve data")
rtr_request_id = 0x01FDBFE0
rtr_response_id = 0x09FDBFE0  # Expected response ID
request = CANMessage(
    arbitration_id=rtr_request_id,
    data=b'',
    is_extended_id=True,
    is_remote_frame=True
)
adapter._write_command(request.to_usbtin_format().encode('ascii'))

# Wait for element list data
print("Waiting for element list data...")
element_data = bytearray()
start = time.time()
while time.time() - start < 5.0:
    frame = adapter._read_frame(timeout=0.2)
    if frame:
        data_hex = frame.data.hex() if frame.data else ""
        print(f"  Received: ID=0x{frame.arbitration_id:08X} DLC={frame.dlc} DATA={data_hex}")
        if frame.arbitration_id == rtr_response_id:
            element_data.extend(frame.data)
            print(f"    ^ Element data! Total collected: {len(element_data)} bytes")

if element_data:
    print(f"\n=== Collected {len(element_data)} bytes of element data ===")
    print(f"Hex dump: {element_data.hex()}")

    # Try to parse as element list (FHEM format: 2-byte idx, 7-byte extid, 4-byte max, 4-byte min)
    # Total: 17 bytes per element
    print(f"\nAttempting to parse as element list (17 bytes per element)...")
    pos = 0
    count = 0
    while pos + 17 <= len(element_data) and count < 5:  # Show first 5
        idx = int.from_bytes(element_data[pos:pos+2], 'big')
        extid = element_data[pos+2:pos+9].hex()
        max_val = int.from_bytes(element_data[pos+9:pos+13], 'big', signed=True)
        min_val = int.from_bytes(element_data[pos+13:pos+17], 'big', signed=True)
        print(f"  Element: idx={idx} extid={extid} max={max_val} min={min_val}")
        pos += 17
        count += 1
else:
    print("\nNo element list data received")

print("\n=== Done ===")
adapter.disconnect()
