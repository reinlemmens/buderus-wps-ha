#!/usr/bin/env python3
"""Read compressor-related parameters to identify which indicates running status."""

import sys

sys.path.insert(0, ".")

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.heat_pump import HeatPumpClient
from buderus_wps.parameter_registry import ParameterRegistry

# Compressor-related parameters from FHEM analysis
COMPRESSOR_PARAMS = [
    "COMPRESSOR_STATE",  # idx 294
    "COMPRESSOR_STATE_2",  # idx 295
    "COMPRESSOR_DHW_REQUEST",  # idx 261 (read=1)
    "COMPRESSOR_HEATING_REQUEST",  # idx 273 (read=1)
    "COMPRESSOR_REAL_FREQUENCY",  # idx 278
    "COMPRESSOR_START",  # idx 288
    "COMPRESSOR_BLOCKED",  # idx 247
    "HW_COMPRESSOR",  # idx 941
    "HW_COMPRESSOR_WORKING_FREQ",  # idx 955
    "HW_COMPRESSOR_TARGET_FREQ",  # idx 950
    "XDHW_COMPRESSOR_REQUEST",  # idx 2470 (read=1)
]


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/tty.usbmodem2101", help="Serial port")
    args = parser.parse_args()
    port = args.port

    print(f"Connecting to {port}...")
    adapter = USBtinAdapter(port=port)
    adapter.connect()

    try:
        registry = ParameterRegistry()
        client = HeatPumpClient(adapter, registry)

        print("\n=== Compressor Status Parameters ===\n")

        for name in COMPRESSOR_PARAMS:
            try:
                result = client.read_parameter(name, timeout=3.0)
                raw_hex = result["raw"].hex() if result["raw"] else "N/A"
                decoded = result["decoded"]
                idx = result["idx"]
                print(
                    f"{name:35s} (idx={idx:4d}): raw=0x{raw_hex:16s} decoded={decoded}"
                )
            except KeyError:
                print(f"{name:35s}: NOT FOUND in registry")
            except Exception as e:
                print(f"{name:35s}: ERROR - {e}")

    finally:
        adapter.disconnect()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
