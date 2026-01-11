#!/usr/bin/env python3
"""Verify CAN readings by passively listening to heat pump broadcasts.

T078: Tool for comparing live CAN readings with FHEM reference data.

This tool connects to a USBtin adapter and passively monitors the CAN bus,
comparing received values against known FHEM readings to validate the
CAN communication implementation.

Usage:
    python tools/verify_fhem.py [--port /dev/ttyACM0] [--duration 10]

Hardware Verified: 2025-12-05 on Raspberry Pi with Buderus WPS heat pump.
The FHEM extids ARE the CAN response IDs - the bus constantly broadcasts data.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from buderus_wps import (
    CAN_PREFIX_COUNTER,
    CAN_PREFIX_DATA,
    CAN_PREFIX_STATUS,
    ELEMENT_E21,
    ELEMENT_E22,
    ELEMENT_E31,
    ELEMENT_E32,
    USBtinAdapter,
)

# FHEM reference readings (captured 2025-12-05)
# Format: CAN_ID -> (fhem_value, description)
FHEM_REFERENCE = {
    # Temperature readings (values in 0.1°C units)
    0x0C084060: (214, "GT1 indoor temp 21.4°C"),
    0x0C084061: (233, "GT1-2 temp 23.3°C"),
    0x0C084062: (228, "GT1-3 temp 22.8°C"),
    0x0C084063: (246, "GT1-4 temp 24.6°C"),
    0x0C0E8060: (552, "GT8 flow temp 55.2°C"),
    0x0C0E8061: (531, "GT8-2 53.1°C"),
    0x0C0E8062: (537, "GT8-3 53.7°C"),
    0x0C000060: (201, "GT? 20.1°C"),
    0x0C0F0060: (975, "GT? 97.5? or 9.75?"),
    # Status values
    0x00008060: (4, "Status value"),
    0x00028063: (4, "Mode"),
    0x00030060: (55, "Outdoor temp 5.5°C"),
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify CAN readings against FHEM reference values"
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyACM0",
        help="Serial port for USBtin adapter (default: /dev/ttyACM0)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Listening duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all received CAN messages",
    )
    return parser.parse_args()


def prefix_name(prefix: int) -> str:
    """Get human-readable name for CAN ID prefix."""
    names = {
        CAN_PREFIX_DATA: "DATA",
        CAN_PREFIX_STATUS: "STATUS",
        CAN_PREFIX_COUNTER: "COUNTER",
    }
    return names.get(prefix, f"0x{prefix:02X}")


def element_name(element_type: int) -> str:
    """Get human-readable name for element type."""
    names = {
        ELEMENT_E21: "E21",
        ELEMENT_E22: "E22",
        ELEMENT_E31: "E31",
        ELEMENT_E32: "E32",
        0x270: "COUNTER",
        0x403: "CONFIG",
    }
    return names.get(element_type, f"0x{element_type:03X}")


def main() -> int:
    """Run FHEM verification."""
    args = parse_args()

    print("=" * 70)
    print("FHEM Verification - Passive CAN Bus Monitoring")
    print(f"Port: {args.port} | Duration: {args.duration}s")
    print("=" * 70)

    # Collect readings
    readings: dict[int, int] = {}
    message_count = 0

    try:
        with USBtinAdapter(args.port) as adapter:
            print("\nConnected to USBtin adapter")
            print(f"Listening for {args.duration} seconds...\n")

            start = time.time()
            while time.time() - start < args.duration:
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if frame and frame.data:
                        message_count += 1
                        can_id = frame.arbitration_id
                        value = int.from_bytes(frame.data, "big", signed=True)
                        readings[can_id] = value

                        if args.verbose:
                            prefix, param_idx, elem = frame.decode_broadcast_id()
                            print(
                                f"  ID=0x{can_id:08X} [{prefix_name(prefix)}] "
                                f"param={param_idx:3d} elem={element_name(elem)} "
                                f"val={value}"
                            )

                except TimeoutError:
                    pass

            print(
                f"\nCollected {len(readings)} unique readings from {message_count} messages"
            )
            print(f"Message rate: {message_count / args.duration:.1f} msg/sec\n")

            # Compare with FHEM reference
            print(
                f"{'CAN ID':<12} {'FHEM':>8} {'Live':>8} {'Diff':>6} {'Match':>6} Description"
            )
            print("-" * 70)

            exact_matches = 0
            close_matches = 0
            missing = 0

            for can_id, (fhem_val, desc) in FHEM_REFERENCE.items():
                if can_id in readings:
                    live_val = readings[can_id]
                    diff = live_val - fhem_val

                    if diff == 0:
                        status = "✓"
                        exact_matches += 1
                    elif abs(diff) <= 10:
                        status = "~"  # Close (values change in real-time)
                        close_matches += 1
                    else:
                        status = "✗"

                    print(
                        f"0x{can_id:08X} {fhem_val:>8} {live_val:>8} {diff:>+6} "
                        f"{status:>6} {desc}"
                    )
                else:
                    missing += 1
                    print(
                        f"0x{can_id:08X} {fhem_val:>8} {'N/A':>8} {'':>6} "
                        f"{'?':>6} {desc} (not seen)"
                    )

            print("-" * 70)
            print(
                f"Results: {exact_matches} exact, {close_matches} close (±10), {missing} missing"
            )
            print("\nNote: Small differences expected - values change in real-time!")

            # Decode a sample message to demonstrate the decode_broadcast_id method
            if readings:
                sample_id = next(iter(readings.keys()))
                # Create a demo frame
                from buderus_wps import CANMessage

                demo = CANMessage(sample_id, b"\x00", is_extended_id=True)
                prefix, param_idx, elem = demo.decode_broadcast_id()
                print("\nCAN ID Decode Demo:")
                print(
                    f"  CAN ID 0x{sample_id:08X} -> prefix={prefix_name(prefix)}, param_idx=0x{param_idx:03X}, element={element_name(elem)}"
                )

            return 0 if missing == 0 else 1

    except FileNotFoundError:
        print(f"Error: Serial port {args.port} not found")
        print("Make sure USBtin adapter is connected")
        return 1
    except PermissionError:
        print(f"Error: Permission denied for {args.port}")
        print("Try: sudo chmod 666 {args.port}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
