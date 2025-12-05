#!/usr/bin/env python3
"""Debug CAN communication to understand extid mapping."""

import sys
import time

sys.path.insert(0, '/home/rein/buderus-wps-ha')

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage

SERIAL_PORT = '/dev/ttyACM0'


def test_read_methods(adapter: USBtinAdapter, idx: int, name: str):
    """Test different ways to read a parameter."""
    print(f"\n=== Testing idx={idx} ({name}) ===")

    # Method 1: Original formula from heat_pump.py
    request_id = 0x04003FE0 | (idx << 14)
    response_id = 0x0C003FE0 | (idx << 14)
    print(f"Method 1: request=0x{request_id:08X}, expect response=0x{response_id:08X}")

    request = CANMessage(
        arbitration_id=request_id,
        data=b"",
        is_extended_id=True,
        is_remote_frame=True
    )

    try:
        adapter.flush_input_buffer()
        adapter.send_frame(request, timeout=2.0)
        response = adapter.receive_frame(timeout=2.0)
        if response:
            val = int.from_bytes(response.data, 'big', signed=True) if response.data else None
            print(f"  Got: ID=0x{response.arbitration_id:08X}, data={response.data.hex()}, val={val}")
        else:
            print("  No response")
    except Exception as e:
        print(f"  Error: {e}")


def read_raw_traffic(adapter: USBtinAdapter, duration: float = 3.0):
    """Just listen to CAN bus traffic for a few seconds."""
    print(f"\n=== Listening to CAN traffic for {duration}s ===")
    start = time.time()

    while time.time() - start < duration:
        try:
            frame = adapter.receive_frame(timeout=0.5)
            if frame:
                val = int.from_bytes(frame.data, 'big', signed=True) if frame.data else None
                print(f"ID=0x{frame.arbitration_id:08X} data={frame.data.hex()} val={val}")
        except Exception:
            pass


def main():
    print("CAN Communication Debug")
    print("=" * 70)

    # Known parameters from FHEM
    test_params = [
        (2, "STATUS"),           # Common status parameter
        (3, "GT11_STOP"),        # Defrost param
        (770, "OUTDOOR_TEMP"),   # Typical outdoor temp idx
    ]

    try:
        with USBtinAdapter(SERIAL_PORT) as adapter:
            print(f"Connected: {adapter.status}")

            # First, listen to passive traffic
            read_raw_traffic(adapter, 2.0)

            # Test reading known parameters
            for idx, name in test_params:
                test_read_methods(adapter, idx, name)
                time.sleep(0.2)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
