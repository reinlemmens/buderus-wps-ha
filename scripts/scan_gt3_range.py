#!/usr/bin/env python3
"""Scan a range of indices to find GT3_TEMP.

Usage:
    python3 scripts/scan_gt3_range.py --port /dev/ttyACM0
"""

import argparse
import struct
import sys
import time
from typing import Optional

try:
    import serial
except ImportError:
    print("ERROR: pyserial required")
    sys.exit(1)

REQUEST_BASE = 0x04003FE0
RESPONSE_BASE = 0x0C003FE0


class SimpleCAN:
    def __init__(self, port: str):
        self.serial = serial.Serial(port=port, baudrate=115200, timeout=5.0)
        self.serial.write(b"C\r")
        time.sleep(0.1)
        self.serial.reset_input_buffer()
        self.serial.write(b"S4\r")
        time.sleep(0.1)
        self.serial.write(b"O\r")
        time.sleep(0.1)
        self.serial.reset_input_buffer()

    def close(self):
        self.serial.write(b"C\r")
        time.sleep(0.1)
        self.serial.close()

    def read_param(self, idx: int, timeout: float = 1.0) -> Optional[tuple]:
        request_id = REQUEST_BASE | (idx << 14)
        cmd = f"R{request_id:08X}0\r"
        self.serial.reset_input_buffer()
        self.serial.write(cmd.encode())

        start = time.time()
        buffer = b""
        while time.time() - start < timeout:
            if self.serial.in_waiting:
                buffer += self.serial.read(self.serial.in_waiting)
                while b"\r" in buffer:
                    idx_r = buffer.index(b"\r")
                    frame = buffer[:idx_r].decode("ascii", errors="replace").strip()
                    buffer = buffer[idx_r + 1:]
                    if frame.startswith("T") and len(frame) >= 10:
                        dlc = int(frame[9], 16)
                        data = bytes.fromhex(frame[10:10 + dlc * 2]) if dlc > 0 else b""
                        return (dlc, data)
            time.sleep(0.01)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", default="/dev/ttyACM0")
    parser.add_argument("--target", "-t", type=float, default=42.8,
                        help="Target temperature to find")
    args = parser.parse_args()

    print(f"Scanning for temperature ~{args.target}°C...")
    print()

    can = SimpleCAN(args.port)

    # Scan ranges around known GT3 area
    ranges = [
        (675, 695),    # GT3 area per static list
        (1030, 1040),  # HW_GT3 area
        (415, 440),    # DHW_GT3 area
    ]

    results = []

    for start, end in ranges:
        print(f"Scanning idx {start}-{end}...")
        for idx in range(start, end + 1):
            resp = can.read_param(idx, timeout=0.5)
            if resp:
                dlc, data = resp
                if dlc == 2:
                    raw = struct.unpack(">h", data[:2])[0]
                    temp = raw / 10.0
                    if 20.0 <= temp <= 70.0:
                        diff = abs(temp - args.target)
                        results.append((idx, temp, diff, data.hex().upper()))

    can.close()

    if results:
        # Sort by closeness to target
        results.sort(key=lambda x: x[2])
        print()
        print(f"{'idx':>5}  {'Temp':>8}  {'Diff':>6}  {'Raw'}")
        print("-" * 40)
        for idx, temp, diff, raw in results[:15]:
            marker = " <-- CLOSEST" if diff == results[0][2] else ""
            print(f"{idx:>5}  {temp:>7.1f}°C  {diff:>5.1f}°C  {raw}{marker}")
    else:
        print("No temperature readings found in scanned ranges")


if __name__ == "__main__":
    main()
