#!/usr/bin/env python3
"""Test GT3_TEMP (DHW) reading with correct discovered idx.

Based on FHEM investigation:
- Static parameter_data.py says GT3_TEMP is at idx=681
- But FHEM discovery shows it's actually at idx=682 on some heat pumps
- The extid (0EB5CF43420068) is constant, but idx varies by firmware/model

This script tests both indices to verify which one returns the correct temperature.

Usage:
    python3 scripts/test_gt3_temp.py --port /dev/ttyACM0

Requirements:
    - pyserial (pip install pyserial)
    - Stop the Buderus WPS integration before running (to release serial port)
"""

import argparse
import struct
import sys
import time
from typing import Optional

try:
    import serial
except ImportError:
    print("ERROR: pyserial is required. Install with: pip install pyserial")
    sys.exit(1)


# CAN protocol constants
REQUEST_BASE = 0x04003FE0  # RTR request base
RESPONSE_BASE = 0x0C003FE0  # Response base

# Parameter indices to test
PARAMS_TO_TEST = [
    # (idx, name, expected_format)
    (680, "GT3_STATUS (static)", "int"),
    (681, "GT3_TEMP (static) / GT3_STATUS (discovered)", "tem"),
    (682, "GT3_TEMP (discovered)", "tem"),
    (683, "GT41_KORRIGERING_GLOBAL", "tem"),
]


class SimpleCAN:
    """Minimal CAN adapter for standalone testing."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Connect and initialize USBtin at 125kbps."""
        self.serial = serial.Serial(
            port=self.port, baudrate=self.baudrate, timeout=self.timeout
        )

        # Close any existing connection
        self.serial.write(b"C\r")
        time.sleep(0.1)
        self.serial.reset_input_buffer()

        # Set 125kbps (S4) - required for Buderus WPS
        self.serial.write(b"S4\r")
        time.sleep(0.1)

        # Open channel
        self.serial.write(b"O\r")
        time.sleep(0.1)

        self.serial.reset_input_buffer()
        print(f"Connected to {self.port} at 125kbps")

    def disconnect(self) -> None:
        """Disconnect from adapter."""
        if self.serial:
            try:
                self.serial.write(b"C\r")
                time.sleep(0.1)
                self.serial.close()
            except Exception:
                pass
            self.serial = None

    def send_rtr(self, can_id: int, timeout: float = 2.0) -> Optional[dict]:
        """Send RTR request and wait for response."""
        if not self.serial:
            raise RuntimeError("Not connected")

        # Format: R{id:8x}0\r (extended RTR, DLC=0)
        cmd = f"R{can_id:08X}0\r"

        self.serial.reset_input_buffer()
        self.serial.write(cmd.encode())

        # Wait for response
        start = time.time()
        buffer = b""

        while time.time() - start < timeout:
            if self.serial.in_waiting:
                buffer += self.serial.read(self.serial.in_waiting)

                # Parse complete frames (terminated by \r)
                while b"\r" in buffer:
                    idx = buffer.index(b"\r")
                    frame_data = buffer[:idx]
                    buffer = buffer[idx + 1 :]

                    parsed = self._parse_frame(frame_data)
                    if parsed and parsed["type"] == "data":
                        return parsed

            time.sleep(0.01)

        return None

    def _parse_frame(self, data: bytes) -> Optional[dict]:
        """Parse SLCAN frame."""
        try:
            response = data.decode("ascii", errors="replace").strip()
        except Exception:
            return None

        if not response:
            return None

        # Extended data frame: T{id:8x}{len:1x}{data}
        if response.startswith("T") and len(response) >= 10:
            can_id = int(response[1:9], 16)
            dlc = int(response[9], 16)
            frame_data = bytes.fromhex(response[10 : 10 + dlc * 2]) if dlc > 0 else b""
            return {"type": "data", "id": can_id, "dlc": dlc, "data": frame_data}

        # ACK
        if response in ("z", "Z"):
            return {"type": "ack"}

        return None


def decode_temperature(data: bytes) -> Optional[float]:
    """Decode temperature from 2-byte big-endian signed value."""
    if len(data) >= 2:
        raw = struct.unpack(">h", data[:2])[0]
        return raw / 10.0
    return None


def test_parameter(can: SimpleCAN, idx: int, name: str, expected_format: str) -> dict:
    """Test reading a parameter via RTR."""
    request_id = REQUEST_BASE | (idx << 14)
    response_id = RESPONSE_BASE | (idx << 14)

    result = {
        "idx": idx,
        "name": name,
        "request_id": f"0x{request_id:08X}",
        "response_id": f"0x{response_id:08X}",
        "success": False,
        "dlc": None,
        "raw_data": None,
        "decoded": None,
        "is_temperature": False,
    }

    response = can.send_rtr(request_id, timeout=2.0)

    if response:
        result["success"] = True
        result["dlc"] = response["dlc"]
        result["raw_data"] = response["data"].hex().upper()

        if response["dlc"] == 2 and expected_format == "tem":
            temp = decode_temperature(response["data"])
            if temp is not None and -50.0 <= temp <= 100.0:
                result["decoded"] = f"{temp:.1f}°C"
                result["is_temperature"] = True
            else:
                result["decoded"] = f"raw={struct.unpack('>h', response['data'])[0]}"
        elif response["dlc"] == 1:
            result["decoded"] = f"status={response['data'][0]}"
        elif response["dlc"] >= 2:
            raw = struct.unpack(">h", response["data"][:2])[0]
            result["decoded"] = f"raw={raw}"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Test GT3_TEMP (DHW) reading with correct discovered idx"
    )
    parser.add_argument(
        "--port",
        "-p",
        default="/dev/ttyACM0",
        help="Serial port for USBtin adapter (default: /dev/ttyACM0)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("GT3_TEMP (DHW Temperature) Test")
    print("=" * 70)
    print()
    print("Based on FHEM investigation:")
    print("  - Static lists say GT3_TEMP is at idx=681")
    print("  - Discovery shows GT3_TEMP is at idx=682 on your heat pump")
    print("  - This script tests both to verify")
    print()
    print("IMPORTANT: Note the GT3 temperature shown on heat pump display!")
    print()

    can = SimpleCAN(args.port)

    try:
        can.connect()
    except Exception as e:
        print(f"ERROR: Failed to connect: {e}")
        print()
        print("Make sure:")
        print("  1. The Buderus WPS integration is STOPPED in Home Assistant")
        print("  2. The USB device is connected and accessible")
        print("  3. You have permission to access the serial port")
        sys.exit(1)

    try:
        print()
        print("Testing parameter reads...")
        print()
        print(f"{'idx':>5}  {'DLC':>3}  {'Raw':>8}  {'Decoded':>12}  {'Name'}")
        print("-" * 70)

        results = []
        for idx, name, fmt in PARAMS_TO_TEST:
            result = test_parameter(can, idx, name, fmt)
            results.append(result)

            dlc_str = str(result["dlc"]) if result["dlc"] is not None else "N/A"
            raw_str = result["raw_data"] or "N/A"
            decoded_str = result["decoded"] or "TIMEOUT"

            # Highlight temperature readings
            marker = ""
            if result["is_temperature"]:
                marker = " <-- TEMPERATURE"

            print(
                f"{idx:>5}  {dlc_str:>3}  {raw_str:>8}  {decoded_str:>12}  {name}{marker}"
            )

        print()
        print("=" * 70)
        print("Analysis")
        print("=" * 70)
        print()

        # Find temperature readings
        temp_results = [r for r in results if r["is_temperature"]]

        if not temp_results:
            print("WARNING: No valid temperature readings found!")
            print()
            print("Possible causes:")
            print("  1. Heat pump is not responding to RTR requests")
            print("  2. CAN bus communication issue")
            print("  3. Need to try different idx values")
        else:
            print("Temperature readings found:")
            for r in temp_results:
                print(f"  idx={r['idx']}: {r['decoded']} ({r['name']})")

            print()
            print("Compare with heat pump display GT3 value.")
            print()

            # Check idx 682 specifically
            idx_682 = next((r for r in results if r["idx"] == 682), None)
            if idx_682 and idx_682["is_temperature"]:
                print(f"✓ idx=682 returns {idx_682['decoded']}")
                print("  If this matches heat pump GT3, use idx=682 for GT3_TEMP")
            elif idx_682:
                print(f"⚠ idx=682 returned DLC={idx_682['dlc']}, not a temperature")

            # Check idx 681 specifically
            idx_681 = next((r for r in results if r["idx"] == 681), None)
            if idx_681:
                if idx_681["dlc"] == 1:
                    print(
                        f"✓ idx=681 returns DLC=1 (status byte) - confirms it's GT3_STATUS"
                    )
                elif idx_681["is_temperature"]:
                    print(
                        f"✓ idx=681 returns {idx_681['decoded']} - might be GT3_TEMP on your HP"
                    )

        print()

    finally:
        can.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()
