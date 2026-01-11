#!/usr/bin/env python3
"""Test script for parameter discovery and broadcast monitoring."""

import sys
import time

# Add the custom_components path to Python path
sys.path.insert(0, "/config/custom_components/buderus_wps")

from buderus_wps import BroadcastMonitor, HeatPump, HeatPumpClient, USBtinAdapter
from buderus_wps.can_message import CANMessage

PORT = "/dev/ttyACM0"
TIMEOUT = 5.0


def test_monitor_broadcasts(duration: float = 10.0):
    """Monitor broadcasts for a specified duration."""
    print(f"\n=== Monitoring broadcasts for {duration}s ===")

    adapter = USBtinAdapter(PORT, timeout=TIMEOUT)
    adapter.connect()

    try:
        monitor = BroadcastMonitor(adapter)
        cache = monitor.collect(duration=duration)

        print(f"\nCollected {len(cache.readings)} unique readings:")

        # Group by temperature range
        temps = []
        for _key, reading in cache.readings.items():
            if reading.is_temperature and 10.0 <= reading.temperature <= 80.0:
                temps.append(reading)

        # Sort by temperature
        temps.sort(key=lambda r: r.temperature)

        print("\n--- Temperature Readings (10-80°C) ---")
        for r in temps:
            print(f"  Base=0x{r.base:04X}, Idx={r.idx:3d}, Temp={r.temperature:5.1f}°C")

    finally:
        adapter.disconnect()


def test_read_parameter(param_name: str):
    """Read a single parameter via RTR."""
    print(f"\n=== Reading {param_name} ===")

    adapter = USBtinAdapter(PORT, timeout=TIMEOUT)
    adapter.connect()

    try:
        heat_pump = HeatPump()
        client = HeatPumpClient(adapter, heat_pump)

        result = client.read_parameter(param_name)

        print(f"  Name: {result['name']}")
        print(f"  Index: {result['idx']}")
        print(f"  Format: {result['format']}")
        print(f"  Raw: {result['raw'].hex()}")
        print(f"  Decoded: {result['decoded']}")

        return result

    except Exception as e:
        print(f"  ERROR: {e}")
        return None

    finally:
        adapter.disconnect()


def test_discovery_protocol():
    """Test the FHEM-style discovery protocol."""
    print("\n=== Testing Discovery Protocol ===")

    # FHEM CAN IDs for discovery
    ELEMENT_COUNT_REQUEST_ID = 0x01FD7FE0
    ELEMENT_COUNT_RESPONSE_ID = 0x09FD7FE0
    ELEMENT_DATA_REQUEST_ID = 0x01FD3FE0
    ELEMENT_DATA_RESPONSE_ID = 0x09FDBFE0

    adapter = USBtinAdapter(PORT, timeout=TIMEOUT)
    adapter.connect()

    try:
        # Step 1: Request element count
        print("\n1. Requesting element count...")
        count_request = CANMessage(
            arbitration_id=ELEMENT_COUNT_REQUEST_ID,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )

        adapter.flush_input_buffer()
        response = adapter.send_frame(count_request, timeout=5.0)

        if response:
            print(f"   Response ID: 0x{response.arbitration_id:08X}")
            print(f"   Response data: {response.data.hex()}")

            if response.arbitration_id == ELEMENT_COUNT_RESPONSE_ID:
                # Parse count from response
                if len(response.data) >= 4:
                    count = int.from_bytes(response.data[:4], "big")
                    print(f"   Element count: {count}")
                else:
                    print(f"   Data too short: {len(response.data)} bytes")
        else:
            print("   No response received")

        # Step 2: Request first chunk of data
        print("\n2. Requesting first data chunk (4096 bytes at offset 0)...")
        chunk_size = 4096
        offset = 0

        # Build request: 8 bytes = size (4 bytes) + offset (4 bytes)
        request_data = chunk_size.to_bytes(4, "big") + offset.to_bytes(4, "big")

        data_request = CANMessage(
            arbitration_id=ELEMENT_DATA_REQUEST_ID,
            data=request_data,
            is_extended_id=True,
        )

        adapter.flush_input_buffer()
        adapter.send_frame(data_request, timeout=0.5)

        # Also send RTR to trigger response (per FHEM)
        CANMessage(
            arbitration_id=ELEMENT_DATA_RESPONSE_ID,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )

        # Collect responses for a few seconds
        print("   Collecting responses...")
        received_data = bytearray()
        start_time = time.time()

        while time.time() - start_time < 3.0:
            try:
                frame = adapter.receive_frame(timeout=0.5)
                if frame:
                    if frame.arbitration_id == ELEMENT_DATA_RESPONSE_ID:
                        received_data.extend(frame.data)
                        print(
                            f"   Received {len(frame.data)} bytes (total: {len(received_data)})"
                        )
            except Exception:
                pass

        if received_data:
            print(f"\n   Total received: {len(received_data)} bytes")
            print(f"   First 64 bytes (hex): {received_data[:64].hex()}")

            # Try to parse first element
            if len(received_data) >= 18:
                idx = int.from_bytes(received_data[0:2], "big")
                extid = received_data[2:9].hex()
                max_val = int.from_bytes(received_data[9:13], "big", signed=True)
                min_val = int.from_bytes(received_data[13:17], "big", signed=True)
                name_len = received_data[17]

                print("\n   First element:")
                print(f"     idx: {idx}")
                print(f"     extid: {extid}")
                print(f"     max: {max_val}")
                print(f"     min: {min_val}")
                print(f"     name_len: {name_len}")

                if name_len > 0 and len(received_data) >= 18 + name_len:
                    name = received_data[18 : 18 + name_len - 1].decode(
                        "ascii", errors="replace"
                    )
                    print(f"     name: {name}")
        else:
            print("   No data received")

    finally:
        adapter.disconnect()


def main():
    """Run all tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Test discovery and monitoring")
    parser.add_argument(
        "--monitor", type=float, default=0, help="Monitor broadcasts for N seconds"
    )
    parser.add_argument("--read", type=str, default="", help="Read a parameter by name")
    parser.add_argument(
        "--discovery", action="store_true", help="Test discovery protocol"
    )
    args = parser.parse_args()

    if args.monitor > 0:
        test_monitor_broadcasts(args.monitor)

    if args.read:
        test_read_parameter(args.read)

    if args.discovery:
        test_discovery_protocol()

    # If no args, run all tests
    if not args.monitor and not args.read and not args.discovery:
        print("Usage:")
        print("  --monitor N     Monitor broadcasts for N seconds")
        print("  --read PARAM    Read parameter by name")
        print("  --discovery     Test FHEM discovery protocol")


if __name__ == "__main__":
    main()
