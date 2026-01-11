#!/usr/bin/env python3
"""
Standalone diagnostic for GT10/GT11 - runs outside HA context.
"""

import sys
import json
import os

print("=" * 70)
print("BUDERUS WPS GT10/GT11 DIAGNOSTIC TOOL (STANDALONE)")
print("=" * 70)

# Add buderus_wps library to path (not the HA integration wrapper)
sys.path.insert(0, "/config/custom_components/buderus_wps/buderus_wps")

try:
    print("\n[1/6] Importing modules...")
    from can_adapter import USBtinAdapter
    from parameter import ParameterRegistry
    from heat_pump import HeatPumpClient
    from element_discovery import ElementDiscovery

    print("✓ Modules imported successfully")

    print("\n[2/6] Checking element discovery cache...")
    cache_path = "/tmp/buderus_wps_elements.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            cache_data = json.load(f)
        print(f"✓ Cache exists: {len(cache_data.get('elements', []))} elements")

        # Search for GT10/GT11 in cache
        gt_found = []
        for elem in cache_data.get("elements", []):
            text = elem.get("text", "")
            if "GT10_TEMP" == text or "GT11_TEMP" == text:
                gt_found.append(elem)
                print(
                    f"  Found: {text} → idx={elem['idx']}, min={elem['min_value']}, max={elem['max_value']}"
                )

        if not gt_found:
            print("  ⚠ GT10_TEMP and GT11_TEMP not found in cache!")
    else:
        print("⚠ No cache found at /tmp/buderus_wps_elements.json")

    print("\n[3/6] Connecting to heat pump...")
    adapter = USBtinAdapter("/dev/ttyACM0")
    adapter.connect()
    print("✓ Connected to /dev/ttyACM0")

    print("\n[4/6] Loading parameter registry...")
    registry = ParameterRegistry()

    # Check static defaults
    print("\nStatic defaults:")
    for name in ["GT10_TEMP", "GT11_TEMP", "GT3_TEMP"]:
        param = registry.get_parameter(name)
        if param:
            print(
                f"  {name}: idx={param.idx}, min={param.min}, max={param.max}, format={param.format}"
            )
        else:
            print(f"  {name}: NOT IN REGISTRY")

    print("\n[5/6] Running element discovery...")
    discovery = ElementDiscovery(adapter)
    discovered = discovery.discover_with_cache(
        cache_path=cache_path,
        refresh=False,
        timeout=30.0,
        max_retries=3,
        min_completion_ratio=0.95,
    )

    if discovered:
        updated = registry.update_from_discovery(discovered)
        print(f"✓ Discovery: {len(discovered)} elements, {updated} updated")

        # Show what was discovered
        print("\nDiscovered GT parameters:")
        for elem in discovered:
            if elem.text in ["GT10_TEMP", "GT11_TEMP", "GT3_TEMP"]:
                print(
                    f"  {elem.text}: idx={elem.idx}, min={elem.min_value}, max={elem.max_value}, extid={elem.extid}"
                )

        # Show registry after discovery
        print("\nRegistry after discovery:")
        for name in ["GT10_TEMP", "GT11_TEMP"]:
            param = registry.get_parameter(name)
            if param:
                can_id = 0x04003FE0 | (param.idx << 14)
                print(
                    f"  {name}: idx={param.idx}, min={param.min}, max={param.max}, CAN=0x{can_id:08X}"
                )
            else:
                print(f"  {name}: NOT IN REGISTRY")
    else:
        print("✗ Discovery returned nothing!")

    print("\n[6/6] Reading GT10_TEMP and GT11_TEMP via RTR...")
    client = HeatPumpClient(adapter, registry)

    for param_name in ["GT10_TEMP", "GT11_TEMP"]:
        print(f"\n--- Reading {param_name} ---")
        param = registry.get_parameter(param_name)

        if not param:
            print(f"  ✗ {param_name} NOT IN REGISTRY!")
            continue

        print(
            f"  Parameter: idx={param.idx}, min={param.min}, max={param.max}, format={param.format}"
        )
        can_id = 0x04003FE0 | (param.idx << 14)
        print(f"  CAN ID: 0x{can_id:08X}")

        try:
            result = client.read_parameter(param_name)
            raw = result.get("raw", b"")
            decoded = result.get("decoded")
            error = result.get("error")

            print(f"  Raw bytes: {raw}")
            print(f"  Raw hex: {raw.hex() if raw else 'N/A'}")
            print(f"  Decoded: {decoded}")

            if error:
                print(f"  ✗ Error: {error}")
            elif decoded is None:
                print(f"  ⚠ DEAD sensor (0xDEAD)")
            elif isinstance(decoded, (int, float)) and abs(decoded - 0.1) < 0.01:
                print(f"  ✗ PROBLEM: Got 0.1°C (raw value = 1)")
                print(f"     Possible causes:")
                print(f"       - Wrong parameter idx (not GT10/GT11 on your model)")
                print(f"       - Parameter doesn't exist")
                print(f"       - Reading uninitialized memory")
            else:
                print(f"  ✓ Success: {decoded}°C")

        except Exception as e:
            print(f"  ✗ Exception: {e}")

    print("\n[CLEANUP] Disconnecting...")
    adapter.disconnect()
    print("✓ Done")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

except Exception as e:
    print(f"\n✗ FATAL ERROR: {e}")
    import traceback

    traceback.print_exc()
