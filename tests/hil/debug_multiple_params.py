#!/usr/bin/env python3
"""Debug script to test multiple parameters with different characteristics."""

import time
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from buderus_wps import USBtinAdapter
from buderus_wps.can_message import CANMessage

# Test parameters with different min/max values
TEST_PARAMS = [
    # idx, name, min, max, format
    (681, "GT3_TEMP", 0, 0, "tem"),  # DHW temp - min/max both 0
    (2475, "XDHW_TIME", 0, 48, "int"),  # Extra DHW time - has range
    (2473, "XDHW_STOP_TEMP", 500, 650, "tem"),  # Extra DHW stop temp - has range
    (683, "GT41_KORRIGERING_GLOBAL", -50, 50, "tem"),  # Has negative min
    (8, "OUTDOOR_TEMP", -400, 400, "tem"),  # Outdoor temp
]

adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()

print("Testing multiple parameters:")
print("=" * 70)

for idx, name, min_val, max_val, fmt in TEST_PARAMS:
    request_id = 0x04003FE0 | (idx << 14)
    response_id = 0x0C003FE0 | (idx << 14)

    print(f"\n{name} (idx={idx}, min={min_val}, max={max_val}, format={fmt})")
    print(f"  Request:  0x{request_id:08X}")
    print(f"  Response: 0x{response_id:08X}")

    # Send RTR request
    request = CANMessage(
        arbitration_id=request_id,
        data=b'',
        is_extended_id=True,
        is_remote_frame=True
    )

    adapter.flush_input_buffer()
    adapter._write_command(request.to_usbtin_format().encode('ascii'))

    # Wait for response on expected ID (up to 2 seconds)
    found_response = False
    start = time.time()
    while time.time() - start < 2.0:
        frame = adapter._read_frame(timeout=0.2)
        if frame and frame.arbitration_id == response_id:
            data_hex = frame.data.hex() if frame.data else ""
            print(f"  Response: dlc={frame.dlc} data=0x{data_hex}")
            if frame.dlc >= 2:
                raw = int.from_bytes(frame.data[:2], 'big')
                if fmt == "tem":
                    val = raw / 10.0
                    print(f"  Decoded: {val}°C (raw={raw})")
                else:
                    print(f"  Decoded: {raw}")
            elif frame.dlc == 1:
                print(f"  Single byte response: {frame.data[0]}")
            found_response = True
            break

    if not found_response:
        print(f"  No response on expected ID")

    time.sleep(0.5)  # Brief pause between requests

print("\n" + "=" * 70)
print("Done")

adapter.disconnect()
