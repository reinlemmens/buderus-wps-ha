#!/usr/bin/env python3
"""Quick diagnostic script to check GT10/GT11 temperature readings."""

import sys

sys.path.insert(0, "/config/custom_components/buderus_wps")

try:
    from buderus_wps import HeatPump, HeatPumpClient, USBtinAdapter
    from buderus_wps.element_discovery import ElementDiscovery

    # Connect to heat pump
    adapter = USBtinAdapter("/dev/ttyACM0")
    adapter.connect()

    # Create registry
    registry = HeatPump()

    # Run element discovery
    print("Running element discovery...")
    discovery = ElementDiscovery(adapter)
    discovered = discovery.discover_with_cache(
        cache_path="/tmp/buderus_wps_elements.json", refresh=False, timeout=30.0
    )

    if discovered:
        updated = registry.update_from_discovery(discovered)
        print(f"Discovery: {len(discovered)} elements, {updated} indices updated\n")

    # Check GT10/GT11 parameters
    for param_name in ["GT10_TEMP", "GT11_TEMP", "GT3_TEMP"]:
        param = registry.get_parameter(param_name)
        if param:
            print(f"{param_name}:")
            print(f"  idx: {param.idx}")
            print(f"  extid: {param.extid}")
            print(f"  format: {param.format}")
            print(f"  min: {param.min}, max: {param.max}")
            print(f"  CAN ID: 0x{0x04003FE0 | (param.idx << 14):08X}")
        else:
            print(f"{param_name}: NOT FOUND in registry")
        print()

    # Try reading values
    client = HeatPumpClient(adapter, registry)

    for param_name in ["GT10_TEMP", "GT11_TEMP"]:
        try:
            print(f"Reading {param_name}...")
            result = client.read_parameter(param_name)
            print(f"  Raw: {result.get('raw', 'N/A')}")
            print(f"  Decoded: {result.get('decoded', 'N/A')}")
            print(f"  Error: {result.get('error', 'None')}")
        except Exception as e:
            print(f"  FAILED: {e}")
        print()

    adapter.disconnect()
    print("Done!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
