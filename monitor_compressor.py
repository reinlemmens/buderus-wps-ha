#!/usr/bin/env python3
"""
Monitor compressor status in real-time.

Displays compressor running state, frequency, and mode, updating every 2 seconds.
Useful for observing compressor behavior during DHW or heating cycles.

Usage:
    python monitor_compressor.py --port /dev/ttyACM0

Press Ctrl+C to stop monitoring.
"""

import argparse
import sys
import time
from datetime import datetime

sys.path.insert(0, ".")

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.heat_pump import HeatPumpClient
from buderus_wps.parameter_registry import ParameterRegistry


def read_compressor_status(client: HeatPumpClient) -> dict:
    """Read all compressor-related parameters."""
    status = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "frequency": 0,
        "running": False,
        "state": 0,
        "dhw_request": 0,
        "heating_request": 0,
        "mode": "Idle",
    }

    try:
        result = client.read_parameter("COMPRESSOR_REAL_FREQUENCY", timeout=2.0)
        status["frequency"] = int(result.get("decoded", 0))
        status["running"] = status["frequency"] > 0
    except Exception:
        pass

    try:
        result = client.read_parameter("COMPRESSOR_STATE", timeout=2.0)
        status["state"] = int(result.get("decoded", 0))
    except Exception:
        pass

    try:
        result = client.read_parameter("COMPRESSOR_DHW_REQUEST", timeout=2.0)
        status["dhw_request"] = int(result.get("decoded", 0))
        if status["dhw_request"] > 0:
            status["mode"] = "DHW"
    except Exception:
        pass

    try:
        result = client.read_parameter("COMPRESSOR_HEATING_REQUEST", timeout=2.0)
        status["heating_request"] = int(result.get("decoded", 0))
        if status["heating_request"] > 0 and status["mode"] == "Idle":
            status["mode"] = "Heating"
    except Exception:
        pass

    return status


def format_status_line(status: dict, prev_status: dict = None) -> str:
    """Format status as a single line with change indicators."""
    running_str = "RUNNING" if status["running"] else "STOPPED"
    freq_str = f"{status['frequency']:3d} Hz" if status["running"] else "  0 Hz"

    # Show change indicator
    changed = ""
    if prev_status:
        if status["running"] != prev_status["running"]:
            changed = " <-- STATE CHANGED!"
        elif status["frequency"] != prev_status["frequency"]:
            changed = " *"

    return (
        f"[{status['timestamp']}] "
        f"{running_str:8s} | "
        f"Freq: {freq_str} | "
        f"Mode: {status['mode']:8s} | "
        f"State: {status['state']:3d} | "
        f"DHW: {status['dhw_request']:3d} | "
        f"Heat: {status['heating_request']:3d}"
        f"{changed}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Monitor compressor status in real-time"
    )
    parser.add_argument(
        "--port", default="/dev/ttyACM0", help="Serial port (default: /dev/ttyACM0)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Update interval in seconds (default: 2.0)",
    )
    args = parser.parse_args()

    print(f"Connecting to {args.port}...")
    adapter = USBtinAdapter(port=args.port)
    adapter.connect()

    try:
        registry = ParameterRegistry()
        client = HeatPumpClient(adapter, registry)

        print()
        print("=" * 90)
        print("COMPRESSOR MONITOR - Press Ctrl+C to stop")
        print("=" * 90)
        print()
        print("Time       Status   | Freq     | Mode     | State | DHW | Heat")
        print("-" * 90)

        prev_status = None

        while True:
            status = read_compressor_status(client)
            line = format_status_line(status, prev_status)
            print(line)

            prev_status = status
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    finally:
        adapter.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()
