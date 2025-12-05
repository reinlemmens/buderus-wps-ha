#!/usr/bin/env python3
"""Verify readings by passively listening to CAN bus.

The FHEM extids ARE the CAN response IDs. The bus constantly broadcasts data.
"""

import sys
import time

sys.path.insert(0, '/home/rein/buderus-wps-ha')

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage

SERIAL_PORT = '/dev/ttyACM0'

# FHEM readings to verify (extid/CAN-ID -> expected_value)
FHEM_SAMPLES = {
    0x0C084060: (214, "GT1 temp 21.4°C"),
    0x0C084061: (233, "GT1-2 temp 23.3°C"),
    0x0C084062: (228, "GT1-3 temp 22.8°C"),
    0x0C084063: (246, "GT1-4 temp 24.6°C"),
    0x0C0E8060: (552, "GT8? 55.2°C"),
    0x0C0E8061: (531, "GT8-2 53.1°C"),
    0x0C0E8062: (537, "GT8-3 53.7°C"),
    0x0C000060: (201, "GT? 20.1°C"),
    0x0C0F0060: (975, "GT? 97.5? or 9.75?"),
    0x00008060: (4, "Status value"),
    0x00028063: (4, "Mode"),
    0x00030060: (55, "Outdoor? 5.5°C"),
}


def main():
    print("=" * 70)
    print("FHEM Verification - Passive Listening")
    print("Collecting CAN traffic and comparing with FHEM values")
    print("=" * 70)

    # Collect readings
    readings = {}
    listen_time = 10  # seconds

    try:
        with USBtinAdapter(SERIAL_PORT) as adapter:
            print(f"Listening for {listen_time} seconds...")

            start = time.time()
            while time.time() - start < listen_time:
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if frame and frame.data:
                        can_id = frame.arbitration_id
                        val = int.from_bytes(frame.data, 'big', signed=True)
                        readings[can_id] = val
                except Exception:
                    pass

            print(f"Collected {len(readings)} unique parameter readings\n")

            # Compare with FHEM
            print(f"{'CAN ID':<12} {'FHEM':>8} {'Live':>8} {'Diff':>6} {'Match':>6} Description")
            print("-" * 70)

            matches = 0
            close = 0
            missing = 0

            for can_id, (fhem_val, desc) in FHEM_SAMPLES.items():
                if can_id in readings:
                    live_val = readings[can_id]
                    diff = live_val - fhem_val

                    if diff == 0:
                        status = "✓"
                        matches += 1
                    elif abs(diff) <= 5:
                        status = "~"  # Close (values may have changed)
                        close += 1
                    else:
                        status = "✗"

                    print(f"0x{can_id:08X} {fhem_val:>8} {live_val:>8} {diff:>+6} {status:>6} {desc}")
                else:
                    missing += 1
                    print(f"0x{can_id:08X} {fhem_val:>8} {'N/A':>8} {'':>6} {'?':>6} {desc} (not seen)")

            print("-" * 70)
            print(f"Results: {matches} exact, {close} close (within 5), {missing} missing")
            print(f"\nNote: Small differences expected - values change in real-time!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
