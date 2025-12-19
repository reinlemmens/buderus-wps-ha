#!/usr/bin/env python3
"""Scan heat pump parameters to discover correct idx mappings.

This tool scans a range of idx values and identifies:
- Temperature values (typically 200-700 range = 20.0-70.0°C)
- Boolean states (0 or 1)
- Active parameters (those that respond)
"""

import sys
import time
import json
from datetime import datetime

sys.path.insert(0, '/home/rein/buderus-wps-ha')

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.parameter_defaults import PARAMETER_DEFAULTS

SERIAL_PORT = '/dev/ttyACM0'

# Build reverse lookup: idx -> parameter name from static data
STATIC_BY_IDX = {p['idx']: p['text'] for p in PARAMETER_DEFAULTS}


def read_param(adapter, idx, timeout=1.0):
    """Read parameter by idx, return (value, raw_bytes) or (None, None) on error."""
    can_id = 0x04003FE0 | (idx << 14)
    r = CANMessage(arbitration_id=can_id, data=b"", is_extended_id=True, is_remote_frame=True)
    try:
        resp = adapter.send_frame(r, timeout=timeout)
        if resp and resp.data:
            val = int.from_bytes(resp.data, byteorder="big", signed=True)
            return val, resp.data.hex()
        return None, None
    except Exception:
        return None, None


def classify_value(val):
    """Classify a value into categories."""
    if val is None:
        return "no_response"
    if val == 0:
        return "zero"
    if val == 1:
        return "one/bool"
    if 150 <= val <= 800:
        return f"temp?({val/10:.1f}°C)"
    if -300 <= val < 0:
        return f"neg_temp?({val/10:.1f}°C)"
    if val > 10000:
        return "large"
    return "other"


def scan_range(adapter, start_idx, end_idx, delay=0.05):
    """Scan a range of idx values."""
    results = []

    for idx in range(start_idx, end_idx + 1):
        val, raw = read_param(adapter, idx)
        static_name = STATIC_BY_IDX.get(idx, "")

        if val is not None:
            category = classify_value(val)
            results.append({
                'idx': idx,
                'value': val,
                'raw': raw,
                'category': category,
                'static_name': static_name
            })

            # Print interesting ones
            if category != "zero" or static_name:
                print(f"idx={idx:4}  val={val:6}  {category:15}  static={static_name}")

        time.sleep(delay)

    return results


def find_dhw_temperatures(adapter):
    """Scan for DHW temperature parameters."""
    print("=" * 60)
    print("Scanning for DHW temperature parameters...")
    print("Looking for values in range 200-600 (20.0-60.0°C)")
    print("=" * 60)

    # Scan around known DHW-related idx ranges
    ranges_to_scan = [
        (370, 500, "DHW parameters range"),
        (1280, 1300, "GT sensor values"),
        (2470, 2500, "XDHW range"),
    ]

    all_temps = []

    with USBtinAdapter(SERIAL_PORT) as adapter:
        for start, end, desc in ranges_to_scan:
            print(f"\n--- {desc} (idx {start}-{end}) ---")
            results = scan_range(adapter, start, end)

            for r in results:
                if "temp" in r['category']:
                    all_temps.append(r)

    print("\n" + "=" * 60)
    print("Temperature-like values found:")
    print("=" * 60)
    for t in all_temps:
        print(f"idx={t['idx']:4}  {t['value']/10:.1f}°C  static={t['static_name']}")

    return all_temps


def find_xdhw_mapping(adapter):
    """Find the correct XDHW parameter mappings for this firmware."""
    print("=" * 60)
    print("Finding XDHW parameter mappings...")
    print("=" * 60)

    # Known XDHW static idx values
    xdhw_static = {
        2470: "XDHW_COMPRESSOR_REQUEST",
        2471: "XDHW_COMPRESSOR_REQUEST_2",
        2472: "XDHW_REQUEST",
        2473: "XDHW_STOP_TEMP",
        2475: "XDHW_TIME",
        2476: "XDHW_WEEKPROGRAM_DAY",
        2477: "XDHW_WEEKPROGRAM_DURATION_TIME",
        2478: "XDHW_WEEKPROGRAM_FAILED",
        2479: "XDHW_WEEKPROGRAM_HAS_FINISHED",
        2480: "XDHW_WEEKPROGRAM_HOUR",
        2481: "XDHW_WEEKPROGRAM_MAX_TIME",
        2482: "XDHW_WEEKPROGRAM_REQUEST",
        2483: "XDHW_WEEKPROGRAM_SAVED_DAY",
        2484: "XDHW_WEEKPROGRAM_STOP_TEMP",
        2486: "XDHW_WEEKPROGRAM_WEEK",
        2487: "XDHW_WEEKPROGRAM_WARM_KEEPING_TIMER",
        2489: "XDHW_TIMER",
    }

    results = {}

    with USBtinAdapter(SERIAL_PORT) as adapter:
        print(f"\n{'idx':>5} {'Value':>8} {'Category':>15} {'Static Name':<35}")
        print("-" * 70)

        for idx in sorted(xdhw_static.keys()):
            val, raw = read_param(adapter, idx)
            cat = classify_value(val)
            static_name = xdhw_static[idx]

            print(f"{idx:5} {val if val else 'N/A':>8} {cat:>15} {static_name:<35}")

            results[idx] = {
                'static_name': static_name,
                'value': val,
                'category': cat
            }

            time.sleep(0.05)

    return results


def main():
    print("Heat Pump Parameter Scanner")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # First, find XDHW mappings
    xdhw_results = find_xdhw_mapping(None)

    print("\n")

    # Then scan for temperatures
    temps = find_dhw_temperatures(None)

    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'xdhw_params': xdhw_results,
        'temperature_params': temps
    }

    with open('/home/rein/buderus-wps-ha/tools/scan_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print("\nResults saved to scan_results.json")


if __name__ == '__main__':
    main()
