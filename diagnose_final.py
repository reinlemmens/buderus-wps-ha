#!/usr/bin/env python3
"""
Final standalone diagnostic - uses library from /tmp.
"""

import json
import os
import sys

# Use the clean library from /tmp (not the HA integration wrapper)
sys.path.insert(0, "/tmp")

print("=" * 70)
print("BUDERUS WPS GT10/GT11 DIAGNOSTIC")
print("=" * 70)

try:
    print("\n[1/6] Importing...")
    from buderus_wps.can_adapter import USBtinAdapter
    from buderus_wps.element_discovery import ElementDiscovery
    from buderus_wps.heat_pump import HeatPumpClient
    from buderus_wps.parameter import ParameterRegistry

    print("✓ OK")

    print("\n[2/6] Cache check...")
    cache = "/tmp/buderus_wps_elements.json"
    if os.path.exists(cache):
        with open(cache) as f:
            data = json.load(f)
        elems = data.get("elements", [])
        print(f"✓ {len(elems)} elements cached")
        for e in elems:
            if e.get("text") in ["GT10_TEMP", "GT11_TEMP"]:
                print(
                    f"  {e['text']}: idx={e['idx']}, min={e['min_value']}, max={e['max_value']}"
                )
    else:
        print("⚠ No cache")

    print("\n[3/6] Connecting...")
    adapter = USBtinAdapter("/dev/ttyACM0")
    adapter.connect()
    print("✓ Connected")

    print("\n[4/6] Registry...")
    reg = ParameterRegistry()

    print("Static:")
    for n in ["GT10_TEMP", "GT11_TEMP"]:
        p = reg.get_parameter(n)
        if p:
            print(f"  {n}: idx={p.idx} min={p.min} max={p.max}")

    print("\n[5/6] Discovery...")
    disc = ElementDiscovery(adapter)
    found = disc.discover_with_cache(cache_path=cache, refresh=False, timeout=30.0)

    if found:
        up = reg.update_from_discovery(found)
        print(f"✓ {len(found)} elements, {up} updated")

        print("After discovery:")
        for n in ["GT10_TEMP", "GT11_TEMP"]:
            p = reg.get_parameter(n)
            if p:
                print(f"  {n}: idx={p.idx} min={p.min} max={p.max}")

    print("\n[6/6] Reading...")
    client = HeatPumpClient(adapter, reg)

    for n in ["GT10_TEMP", "GT11_TEMP"]:
        print(f"\n--- {n} ---")
        p = reg.get_parameter(n)
        if not p:
            print("✗ NOT FOUND")
            continue

        print(f"idx={p.idx} min={p.min} max={p.max}")

        try:
            res = client.read_parameter(n)
            raw = res.get("raw", b"")
            dec = res.get("decoded")

            print(f"Raw: {raw.hex() if raw else '?'}")
            print(f"Dec: {dec}")

            if res.get("error"):
                print(f"✗ {res['error']}")
            elif dec is None:
                print("⚠ DEAD")
            elif abs(float(dec) - 0.1) < 0.01:
                print("✗ PROBLEM: 0.1°C means raw=1")
                print("   Likely: wrong idx or param doesn't exist")
            else:
                print(f"✓ {dec}°C")
        except Exception as e:
            print(f"✗ {e}")

    adapter.disconnect()
    print("\n✓ Done")

except Exception as e:
    print(f"\n✗ {e}")
    import traceback

    traceback.print_exc()
