#!/usr/bin/env python3
"""
Standalone diagnostic for GT10/GT11 - works with package imports.
"""

import sys
import json
import os

print("=" * 70)
print("BUDERUS WPS GT10/GT11 DIAGNOSTIC TOOL")
print("=" * 70)

# Add parent directory to path so we can import buderus_wps as a package
sys.path.insert(0, "/config/custom_components/buderus_wps")

try:
    print("\n[1/6] Importing modules...")
    from buderus_wps.can_adapter import USBtinAdapter
    from buderus_wps.parameter import ParameterRegistry
    from buderus_wps.heat_pump import HeatPumpClient
    from buderus_wps.element_discovery import ElementDiscovery

    print("✓ Modules imported")

    print("\n[2/6] Checking cache...")
    cache_path = "/tmp/buderus_wps_elements.json"
    cache_exists = os.path.exists(cache_path)

    if cache_exists:
        with open(cache_path, "r") as f:
            cache_data = json.load(f)
        print(f"✓ Cache: {len(cache_data.get('elements', []))} elements")

        # Find GT10/GT11 in cache
        for elem in cache_data.get("elements", []):
            if elem.get("text") in ["GT10_TEMP", "GT11_TEMP"]:
                print(
                    f"  {elem['text']}: idx={elem['idx']}, min={elem['min_value']}, max={elem['max_value']}"
                )
    else:
        print("⚠ No cache")

    print("\n[3/6] Connecting...")
    adapter = USBtinAdapter("/dev/ttyACM0")
    adapter.connect()
    print("✓ Connected")

    print("\n[4/6] Loading registry...")
    registry = ParameterRegistry()

    print("\nStatic defaults:")
    for name in ["GT10_TEMP", "GT11_TEMP"]:
        p = registry.get_parameter(name)
        if p:
            print(f"  {name}: idx={p.idx}, min={p.min}, max={p.max}")

    print("\n[5/6] Running discovery...")
    discovery = ElementDiscovery(adapter)
    discovered = discovery.discover_with_cache(
        cache_path=cache_path, refresh=False, timeout=30.0
    )

    if discovered:
        updated = registry.update_from_discovery(discovered)
        print(f"✓ {len(discovered)} elements, {updated} updated")

        print("\nAfter discovery:")
        for name in ["GT10_TEMP", "GT11_TEMP"]:
            p = registry.get_parameter(name)
            if p:
                print(f"  {name}: idx={p.idx}, min={p.min}, max={p.max}")

    print("\n[6/6] Reading temperatures...")
    client = HeatPumpClient(adapter, registry)

    for name in ["GT10_TEMP", "GT11_TEMP"]:
        print(f"\n--- {name} ---")
        p = registry.get_parameter(name)
        if not p:
            print("  ✗ NOT IN REGISTRY")
            continue

        print(f"  idx={p.idx}, min={p.min}, max={p.max}")
        try:
            result = client.read_parameter(name)
            raw = result.get("raw", b"")
            dec = result.get("decoded")
            err = result.get("error")

            print(f"  Raw: {raw.hex() if raw else 'N/A'}")
            print(f"  Decoded: {dec}")

            if err:
                print(f"  ✗ Error: {err}")
            elif dec is None:
                print(f"  ⚠ DEAD sensor")
            elif abs(float(dec) - 0.1) < 0.01:
                print(f"  ✗ PROBLEM: 0.1°C (raw=1)")
            else:
                print(f"  ✓ OK: {dec}°C")
        except Exception as e:
            print(f"  ✗ Exception: {e}")

    adapter.disconnect()
    print("\n✓ Done")

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback

    traceback.print_exc()
