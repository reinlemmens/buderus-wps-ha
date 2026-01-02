#!/usr/bin/env python3
"""DHW Temperature Diagnostic Script.

Captures CAN bus traffic and identifies all temperature broadcasts
to help locate the correct GT3 (DHW) sensor position.

Usage:
    python3 scripts/diagnose_dhw.py --port /dev/ttyACM0 --duration 60

Requirements:
    - pyserial (pip install pyserial)
    - Stop the Buderus WPS integration before running (to release serial port)
"""

import argparse
import struct
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

try:
    import serial
except ImportError:
    print("ERROR: pyserial is required. Install with: pip install pyserial")
    sys.exit(1)


# =============================================================================
# Known sensor mappings for reference
# =============================================================================

KNOWN_MAPPINGS = {
    # Current config.py mappings
    (0x0270, 4): "CURRENT DHW (config.py) - UNVERIFIED",
    (0x0270, 5): "GT9_TEMP (return) - verified",
    (0x0270, 6): "GT8_TEMP (supply) - verified",
    # broadcast_monitor.py claims
    (0x0402, 78): "GT3_TEMP (DHW) per broadcast_monitor.py",
    (0x0403, 78): "GT3_TEMP copy per broadcast_monitor.py",
    # Old incorrect mappings
    (0x0060, 58): "DHW_SETPOINT_OR_SUPPLY (NOT actual tank)",
    (0x0061, 58): "DHW_SETPOINT_OR_SUPPLY copy",
    # Room temperatures
    (0x0060, 0): "RC10_C1_ROOM_TEMP",
    (0x0061, 0): "RC10_C2_ROOM_TEMP",
    (0x0062, 0): "RC10_C3_ROOM_TEMP",
    (0x0063, 0): "RC10_C4_ROOM_TEMP",
    # Outdoor
    (0x0060, 12): "OUTDOOR_TEMP",
    (0x0061, 12): "OUTDOOR_TEMP copy",
}


@dataclass
class TemperatureReading:
    """Statistics for a temperature reading at a specific (base, idx)."""
    base: int
    idx: int
    count: int = 0
    total: float = 0.0
    min_temp: float = 999.0
    max_temp: float = -999.0
    last_temp: float = 0.0

    @property
    def avg_temp(self) -> float:
        return self.total / self.count if self.count > 0 else 0.0

    def update(self, temp: float) -> None:
        self.count += 1
        self.total += temp
        self.last_temp = temp
        self.min_temp = min(self.min_temp, temp)
        self.max_temp = max(self.max_temp, temp)


def decode_can_id(can_id: int) -> tuple:
    """Decode CAN ID into (direction, idx, base) per Buderus protocol.

    CAN ID bit layout:
    - bits 27-26: direction (0x0C for broadcast/response)
    - bits 25-14: idx (12-bit parameter index)
    - bits 13-0:  base (14-bit base address)
    """
    base = can_id & 0x3FFF
    idx = (can_id >> 14) & 0xFFF
    direction = can_id >> 26
    return (direction, idx, base)


def decode_temperature(data: bytes) -> Optional[float]:
    """Decode temperature from 2-byte big-endian signed value."""
    if len(data) >= 2:
        raw = struct.unpack(">h", data[:2])[0]
        return raw / 10.0
    return None


class SimpleCAN:
    """Minimal CAN adapter for standalone operation."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Connect and initialize USBtin at 125kbps."""
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
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

    def collect_frames(self, duration: float) -> list:
        """Collect all frames for specified duration."""
        if not self.serial:
            raise RuntimeError("Not connected")

        frames = []
        self.serial.reset_input_buffer()
        start = time.time()
        buffer = b""

        while time.time() - start < duration:
            if self.serial.in_waiting:
                buffer += self.serial.read(self.serial.in_waiting)

                # Parse complete frames (terminated by \r)
                while b"\r" in buffer:
                    idx = buffer.index(b"\r")
                    frame_data = buffer[:idx]
                    buffer = buffer[idx + 1:]

                    parsed = self._parse_frame(frame_data)
                    if parsed:
                        frames.append(parsed)

            time.sleep(0.01)

        return frames

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
            frame_data = bytes.fromhex(response[10:10 + dlc * 2]) if dlc > 0 else b""
            return {"type": "data", "id": can_id, "dlc": dlc, "data": frame_data}

        return None


def run_diagnostic(port: str, duration: float, temp_min: float, temp_max: float) -> None:
    """Run the DHW temperature diagnostic."""
    print("=" * 60)
    print("DHW Temperature Diagnostic")
    print("=" * 60)
    print()
    print(f"Port: {port}")
    print(f"Duration: {duration}s")
    print(f"Temperature filter: {temp_min}°C to {temp_max}°C")
    print()
    print("IMPORTANT: Note the GT3 temperature shown on heat pump display")
    print("           before and after this capture!")
    print()

    can = SimpleCAN(port)
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
        print(f"\nCollecting CAN traffic for {duration} seconds...")
        print("(You should see activity on the heat pump CAN bus)")
        print()

        frames = can.collect_frames(duration)
        print(f"\nReceived {len(frames)} frames total")

        # Process frames - group temperature readings by (base, idx)
        readings: dict[tuple, TemperatureReading] = {}
        data_frames = 0

        for f in frames:
            if f["type"] != "data":
                continue
            data_frames += 1

            direction, idx, base = decode_can_id(f["id"])
            temp = decode_temperature(f["data"])

            # Filter for temperature-like values
            if temp is not None and temp_min <= temp <= temp_max:
                key = (base, idx)
                if key not in readings:
                    readings[key] = TemperatureReading(base=base, idx=idx)
                readings[key].update(temp)

        print(f"Data frames: {data_frames}")
        print(f"Temperature readings in range: {len(readings)}")
        print()

        if not readings:
            print("WARNING: No temperature readings found!")
            print("Check that the heat pump is powered on and CAN bus is active.")
            return

        # Sort by temperature value for easy matching
        sorted_readings = sorted(
            readings.values(),
            key=lambda r: r.avg_temp
        )

        # Print results
        print("=" * 60)
        print("Temperature Broadcasts (sorted by value)")
        print("=" * 60)
        print()
        print(f"{'Base':>8}  {'Idx':>4}  {'Temp':>7}  {'Count':>5}  {'Min':>6}  {'Max':>6}  Notes")
        print("-" * 80)

        for r in sorted_readings:
            key = (r.base, r.idx)
            notes = KNOWN_MAPPINGS.get(key, "")

            # Highlight potential DHW matches (typically 30-60°C range)
            marker = ""
            if 30.0 <= r.avg_temp <= 60.0:
                marker = " <-- DHW range"

            print(
                f"0x{r.base:04X}  {r.idx:4d}  {r.avg_temp:6.1f}°C  {r.count:5d}  "
                f"{r.min_temp:5.1f}°C  {r.max_temp:5.1f}°C  {notes}{marker}"
            )

        print()
        print("=" * 60)
        print("Instructions")
        print("=" * 60)
        print()
        print("1. Note the GT3 temperature shown on heat pump display")
        print("2. Find the matching value in the list above")
        print("3. That (Base, Idx) is the correct DHW sensor position")
        print()
        print("Expected: GT3 DHW should be at Base=0x0402, Idx=78")
        print("          (per broadcast_monitor.py)")
        print()
        print("Current config.py uses: Base=0x0270, Idx=4 (UNVERIFIED)")
        print()

        # Check if expected mapping was found
        expected_key = (0x0402, 78)
        current_key = (0x0270, 4)

        if expected_key in readings:
            r = readings[expected_key]
            print(f"FOUND: Expected DHW at 0x0402/78 = {r.avg_temp:.1f}°C")
        else:
            print("WARNING: Expected DHW location (0x0402/78) not found!")

        if current_key in readings:
            r = readings[current_key]
            print(f"FOUND: Current config DHW at 0x0270/4 = {r.avg_temp:.1f}°C")
        else:
            print("INFO: Current config location (0x0270/4) not found")

    finally:
        can.disconnect()
        print("\nDisconnected.")


def main():
    parser = argparse.ArgumentParser(
        description="DHW Temperature Diagnostic - find correct GT3 sensor position"
    )
    parser.add_argument(
        "--port", "-p",
        default="/dev/ttyACM0",
        help="Serial port for USBtin adapter (default: /dev/ttyACM0)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=60.0,
        help="Capture duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--temp-min",
        type=float,
        default=-10.0,
        help="Minimum temperature filter (default: -10°C)"
    )
    parser.add_argument(
        "--temp-max",
        type=float,
        default=100.0,
        help="Maximum temperature filter (default: 100°C)"
    )

    args = parser.parse_args()

    run_diagnostic(
        port=args.port,
        duration=args.duration,
        temp_min=args.temp_min,
        temp_max=args.temp_max
    )


if __name__ == "__main__":
    main()
