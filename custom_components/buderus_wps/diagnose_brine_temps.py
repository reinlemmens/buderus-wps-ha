#!/usr/bin/env python3
"""
Diagnostic tool for GT10/GT11 brine temperature issue.
Run this directly on the HA server to diagnose why GT10/GT11 show 0.1°C.
"""

import os
import sys

# Ensure the integration path is last on sys.path to avoid stdlib shadowing
script_dir = os.path.dirname(os.path.abspath(__file__))
custom_component_path = os.path.join("custom_components", "buderus_wps")
for entry in list(sys.path):
    if entry.endswith(custom_component_path):
        sys.path.remove(entry)
if sys.path and sys.path[0] == script_dir:
    sys.path.pop(0)
if script_dir not in sys.path:
    sys.path.append(script_dir)

import json
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

print("=" * 70)
print("BUDERUS WPS GT10/GT11 DIAGNOSTIC TOOL")
print("=" * 70)

try:
    print("\n[1/6] Importing modules...")
    from buderus_wps import HeatPump, HeatPumpClient, USBtinAdapter
    from buderus_wps.element_discovery import ElementDiscovery

    print("✓ Modules imported successfully")

    print("\n[2/6] Checking element discovery cache...")
    # Check both paths - /config is new persistent location, /tmp is legacy
    cache_path = "/config/buderus_wps_elements.json"
    if not os.path.exists(cache_path):
        cache_path = "/tmp/buderus_wps_elements.json"  # Legacy fallback
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cache_data = json.load(f)
        print(f"✓ Cache exists: {len(cache_data.get('elements', []))} elements")

        # Search for GT10/GT11 in cache
        for elem in cache_data.get("elements", []):
            if "GT10_TEMP" in elem.get("text", "") or "GT11_TEMP" in elem.get(
                "text", ""
            ):
                print(
                    f"  Found in cache: {elem['text']} → idx={elem['idx']}, min={elem['min_value']}, max={elem['max_value']}"
                )
    else:
        print("⚠ No cache found - will run full discovery")

    print("\n[3/6] Connecting to heat pump...")
    adapter = USBtinAdapter("/dev/ttyACM0")
    adapter.connect()
    print("✓ Connected to /dev/ttyACM0")

    print("\n[4/6] Loading parameter registry...")
    registry = HeatPump()

    # Check static defaults
    print("\nStatic defaults for GT10/GT11:")
    for name in ["GT10_TEMP", "GT11_TEMP"]:
        param = registry.get_parameter(name)
        if param:
            print(
                f"  {name}: idx={param.idx}, min={param.min}, max={param.max}, format={param.format}"
            )
        else:
            print(f"  {name}: NOT FOUND")

    print("\n[5/6] Running element discovery...")
    discovery = ElementDiscovery(adapter)
    discovered = discovery.discover_with_cache(
        cache_path=cache_path, refresh=False, timeout=30.0
    )

    if discovered:
        updated = registry.update_from_discovery(discovered)
        print(
            f"✓ Discovery complete: {len(discovered)} elements, {updated} parameters updated"
        )

        # Check what was discovered for GT10/GT11
        print("\nDiscovered parameters for GT10/GT11:")
        for elem in discovered:
            if "GT10_TEMP" == elem.text or "GT11_TEMP" == elem.text:
                print(
                    f"  {elem.text}: idx={elem.idx}, min={elem.min_value}, max={elem.max_value}"
                )

        # Check registry after discovery
        print("\nRegistry after discovery:")
        for name in ["GT10_TEMP", "GT11_TEMP"]:
            param = registry.get_parameter(name)
            if param:
                print(
                    f"  {name}: idx={param.idx}, min={param.min}, max={param.max}, CAN ID=0x{param.get_read_can_id():08X}"
                )
            else:
                print(f"  {name}: NOT FOUND")
    else:
        print("⚠ Discovery returned no elements!")

    print("\n[6/6] Testing RTR reads for GT10_TEMP and GT11_TEMP...")
    client = HeatPumpClient(adapter, registry)

    for param_name in ["GT10_TEMP", "GT11_TEMP"]:
        print(f"\n--- Reading {param_name} ---")
        param = registry.get_parameter(param_name)
        if not param:
            print(f"  ✗ Parameter {param_name} not in registry!")
            continue

        print(f"  Using: idx={param.idx}, min={param.min}, max={param.max}")
        print(f"  CAN ID: 0x{param.get_read_can_id():08X}")

        try:
            result = client.read_parameter(param_name)
            print(f"  Raw bytes: {result.get('raw', 'N/A')}")
            raw_hex = result.get("raw", b"").hex() if result.get("raw") else "N/A"
            print(f"  Raw hex: {raw_hex}")
            decoded = result.get("decoded")
            print(f"  Decoded: {decoded}")

            if "error" in result:
                print(f"  ✗ Error: {result['error']}")
            elif decoded is None:
                print("  ⚠ Sensor is DEAD (0xDEAD value)")
            elif decoded == 0.1:
                print("  ✗ PROBLEM: Decoded to 0.1°C (raw value = 1)")
                print("     This suggests either:")
                print("       - RTR read is getting garbage data")
                print("       - Wrong parameter idx")
                print("       - Sensor doesn't exist on this heat pump model")
            else:
                print(f"  ✓ Read successful: {decoded}°C")

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            import traceback

            traceback.print_exc()

    print("\n[CLEANUP] Disconnecting...")
    adapter.disconnect()
    print("✓ Disconnected")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

except Exception as e:
    print(f"\n✗ FATAL ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
