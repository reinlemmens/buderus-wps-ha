#!/usr/bin/env python3
"""Standalone CAN test script - no module dependencies."""

import struct
import time

import serial

PORT = "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 5.0


class SimpleCAN:
    """Minimal CAN adapter for testing."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect(self):
        """Connect and initialize USBtin."""
        self.serial = serial.Serial(
            port=self.port, baudrate=self.baudrate, timeout=self.timeout
        )

        # Close any open connection
        self.serial.write(b"C\r")
        time.sleep(0.1)
        self.serial.reset_input_buffer()

        # Set 125kbps (S4) and open in normal mode
        # PROTOCOL: Buderus WPS uses 125kbps CAN bus speed
        self.serial.write(b"S4\r")
        time.sleep(0.1)

        self.serial.write(b"O\r")
        time.sleep(0.1)

        # Read any init responses
        self.serial.reset_input_buffer()
        print(f"Connected to {self.port}")

    def disconnect(self):
        """Disconnect."""
        if self.serial:
            self.serial.write(b"C\r")
            time.sleep(0.1)
            self.serial.close()
            self.serial = None

    def send_extended_rtr(self, can_id: int, timeout: float = None):
        """Send extended RTR and wait for response."""
        # Format: R{id:8x}0\r
        cmd = f"R{can_id:08X}0\r"
        print(f"TX: {cmd.strip()}")

        self.serial.reset_input_buffer()
        self.serial.write(cmd.encode())

        # Wait for response
        timeout = timeout or self.timeout
        start = time.time()
        response = b""

        while time.time() - start < timeout:
            if self.serial.in_waiting:
                data = self.serial.read(self.serial.in_waiting)
                response += data
                if b"\r" in response:
                    break
            time.sleep(0.01)

        if response:
            print(f"RX: {response.decode('ascii', errors='replace').strip()}")
            return self._parse_response(response)
        return None

    def send_extended_frame(self, can_id: int, data: bytes, timeout: float = None):
        """Send extended data frame and wait for response."""
        # Format: T{id:8x}{len:1x}{data:hex}\r
        data_hex = data.hex().upper()
        cmd = f"T{can_id:08X}{len(data):X}{data_hex}\r"
        print(f"TX: {cmd.strip()}")

        self.serial.reset_input_buffer()
        self.serial.write(cmd.encode())

        # Wait for response
        timeout = timeout or self.timeout
        start = time.time()
        response = b""

        while time.time() - start < timeout:
            if self.serial.in_waiting:
                data = self.serial.read(self.serial.in_waiting)
                response += data
                if b"\r" in response:
                    break
            time.sleep(0.01)

        if response:
            print(f"RX: {response.decode('ascii', errors='replace').strip()}")
            return self._parse_response(response)
        return None

    def collect_frames(self, duration: float = 10.0):
        """Collect all frames for a duration."""
        frames = []
        self.serial.reset_input_buffer()

        start = time.time()
        buffer = b""

        while time.time() - start < duration:
            if self.serial.in_waiting:
                buffer += self.serial.read(self.serial.in_waiting)

                # Parse complete frames
                while b"\r" in buffer:
                    idx = buffer.index(b"\r")
                    frame_data = buffer[:idx]
                    buffer = buffer[idx + 1 :]

                    parsed = self._parse_response(frame_data + b"\r")
                    if parsed:
                        frames.append(parsed)

            time.sleep(0.01)

        return frames

    def _parse_response(self, response: bytes):
        """Parse SLCAN response."""
        response = response.decode("ascii", errors="replace").strip()
        if not response:
            return None

        if response.startswith("T") and len(response) >= 10:
            # Extended data frame: T{id:8x}{len:1x}{data}
            can_id = int(response[1:9], 16)
            dlc = int(response[9], 16)
            data = bytes.fromhex(response[10 : 10 + dlc * 2]) if dlc > 0 else b""
            return {"type": "data", "id": can_id, "dlc": dlc, "data": data}

        elif response.startswith("R") and len(response) >= 10:
            # Extended RTR: R{id:8x}{len:1x}
            can_id = int(response[1:9], 16)
            dlc = int(response[9], 16)
            return {"type": "rtr", "id": can_id, "dlc": dlc, "data": b""}

        elif response == "z" or response == "Z":
            # ACK
            return {"type": "ack"}

        return None


def decode_temperature(data: bytes) -> float:
    """Decode temperature from 2-byte big-endian signed."""
    if len(data) >= 2:
        raw = struct.unpack(">h", data[:2])[0]
        return raw * 0.1
    return None


def decode_can_id(can_id: int):
    """Decode CAN ID to base and index."""
    # Extended ID format: base in high bits, index in low bits
    base = (can_id >> 16) & 0xFFFF
    idx = can_id & 0xFFFF
    return base, idx


def test_monitor(duration: float):
    """Monitor broadcasts."""
    print(f"\n=== Monitoring broadcasts for {duration}s ===\n")

    can = SimpleCAN(PORT, BAUDRATE, TIMEOUT)
    can.connect()

    try:
        frames = can.collect_frames(duration)

        print(f"\nReceived {len(frames)} frames")

        # Group by CAN ID and find temperatures
        by_id = {}
        for f in frames:
            if f["type"] == "data":
                by_id[f["id"]] = f

        print("\n--- All unique data frames ---")
        for can_id, f in sorted(by_id.items()):
            base, idx = decode_can_id(can_id)
            data = f["data"]
            temp = decode_temperature(data) if len(data) >= 2 else None

            temp_str = f"{temp:6.1f}°C" if temp and -50 < temp < 100 else "       "
            print(
                f"  ID=0x{can_id:08X} Base=0x{base:04X} Idx={idx:3d} DLC={len(data)} Data={data.hex():16s} {temp_str}"
            )

    finally:
        can.disconnect()


def test_read_param(idx: int):
    """Read a parameter by index via RTR."""
    print(f"\n=== Reading parameter idx={idx} ===\n")

    # Calculate CAN ID: 0x04003FE0 | (idx << 14)
    can_id = 0x04003FE0 | (idx << 14)
    response_id = 0x0C003FE0 | (idx << 14)

    print(f"Request ID:  0x{can_id:08X}")
    print(f"Response ID: 0x{response_id:08X}")

    can = SimpleCAN(PORT, BAUDRATE, TIMEOUT)
    can.connect()

    try:
        result = can.send_extended_rtr(can_id, timeout=2.0)

        if result and result["type"] == "data":
            data = result["data"]
            print(f"\nResponse: {data.hex()}")
            print(f"DLC: {len(data)}")

            if len(data) >= 2:
                raw = struct.unpack(">h", data[:2])[0]
                temp = raw * 0.1
                print(f"Raw (signed): {raw}")
                print(f"As temperature: {temp:.1f}°C")

    finally:
        can.disconnect()


def test_discovery():
    """Test FHEM-style discovery protocol."""
    print("\n=== Testing Discovery Protocol ===\n")

    # FHEM CAN IDs
    ELEMENT_COUNT_REQUEST = 0x01FD7FE0
    ELEMENT_DATA_REQUEST = 0x01FD3FE0
    ELEMENT_DATA_RESPONSE = 0x09FDBFE0

    can = SimpleCAN(PORT, BAUDRATE, TIMEOUT)
    can.connect()

    try:
        # Step 1: Request element count
        print("1. Requesting element count...")
        result = can.send_extended_rtr(ELEMENT_COUNT_REQUEST, timeout=3.0)

        if result and result["type"] == "data":
            data = result["data"]
            if len(data) >= 4:
                count = struct.unpack(">I", data[:4])[0]
                print(f"   Element count: {count}")
            else:
                print(f"   Data: {data.hex()}")

        # Step 2: Request first data chunk
        print("\n2. Requesting first data chunk (4096 bytes at offset 0)...")

        # Build request: size (4 bytes) + offset (4 bytes)
        request_data = struct.pack(">II", 4096, 0)
        result = can.send_extended_frame(
            ELEMENT_DATA_REQUEST, request_data, timeout=0.5
        )

        # Collect responses
        print("   Collecting data responses...")
        frames = can.collect_frames(duration=5.0)

        data_frames = [
            f
            for f in frames
            if f["type"] == "data" and f["id"] == ELEMENT_DATA_RESPONSE
        ]
        print(
            f"   Received {len(data_frames)} data frames from 0x{ELEMENT_DATA_RESPONSE:08X}"
        )

        if data_frames:
            # Concatenate all data
            all_data = bytearray()
            for f in data_frames:
                all_data.extend(f["data"])

            print(f"   Total data: {len(all_data)} bytes")
            print(f"   First 64 bytes: {all_data[:64].hex()}")

            # Try to parse first element
            if len(all_data) >= 18:
                idx = struct.unpack(">H", all_data[0:2])[0]
                extid = all_data[2:9].hex()
                max_val = struct.unpack(">i", all_data[9:13])[0]
                min_val = struct.unpack(">i", all_data[13:17])[0]
                name_len = all_data[17]

                print("\n   First element header:")
                print(f"     idx: {idx}")
                print(f"     extid: {extid}")
                print(f"     max: {max_val}")
                print(f"     min: {min_val}")
                print(f"     name_len: {name_len}")

                if name_len > 0 and len(all_data) >= 18 + name_len:
                    name = all_data[18 : 18 + name_len - 1].decode(
                        "ascii", errors="replace"
                    )
                    print(f"     name: {name}")

    finally:
        can.disconnect()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Standalone CAN test")
    parser.add_argument(
        "--monitor", type=float, default=0, help="Monitor broadcasts for N seconds"
    )
    parser.add_argument("--read", type=int, default=-1, help="Read parameter by index")
    parser.add_argument(
        "--discovery", action="store_true", help="Test discovery protocol"
    )
    args = parser.parse_args()

    if args.monitor > 0:
        test_monitor(args.monitor)
    elif args.read >= 0:
        test_read_param(args.read)
    elif args.discovery:
        test_discovery()
    else:
        print("Usage:")
        print("  --monitor N     Monitor broadcasts for N seconds")
        print("  --read IDX      Read parameter by index")
        print("  --discovery     Test FHEM discovery protocol")


if __name__ == "__main__":
    main()
