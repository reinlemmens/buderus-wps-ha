"""
Simple CLI for Buderus WPS heat pump via USBtin.

Commands: read, write, list
Defaults: /dev/ttyACM0 @ 115200, 5s timeout, read-only flag available
"""

from __future__ import annotations

import argparse
import sys
from typing import Any
import logging
import logging.handlers
import os

from buderus_wps import USBtinAdapter, HeatPumpClient, ParameterRegistry, BroadcastMonitor, EnergyBlockingControl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wps-cli", description="Buderus WPS CLI over USBtin")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port (default: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Operation timeout seconds (default: 5)")
    parser.add_argument("--read-only", action="store_true", help="Force read-only mode (block writes)")
    parser.add_argument("--dry-run", action="store_true", help="Validate writes without sending to device")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", default=None, help="Log file path (default: ~/.cache/buderus-wps/buderus.log)")

    sub = parser.add_subparsers(dest="command", required=True)

    # read
    read_p = sub.add_parser("read", help="Read a parameter by name or index")
    read_p.add_argument("param", help="Parameter name or index")
    read_p.add_argument("--json", action="store_true", help="Output JSON (decoded + raw)")
    read_p.add_argument("--broadcast", action="store_true",
                        help="Read from broadcast traffic instead of RTR")
    read_p.add_argument("--duration", type=float, default=5.0,
                        help="Broadcast collection duration in seconds (default: 5)")
    read_p.add_argument("--no-fallback", action="store_true",
                        help="Disable automatic broadcast fallback for invalid RTR responses")

    # write
    write_p = sub.add_parser("write", help="Write a parameter by name or index")
    write_p.add_argument("param", help="Parameter name or index")
    write_p.add_argument("value", help="Value to write")

    # list
    list_p = sub.add_parser("list", help="List parameters")
    list_p.add_argument("--filter", default=None, help="Substring filter (case-insensitive) on name")

    # dump
    dump_p = sub.add_parser("dump", help="Dump all parameter values")
    dump_p.add_argument("--json", action="store_true", help="Output JSON for all parameters")

    # monitor
    monitor_p = sub.add_parser("monitor", help="Monitor broadcast traffic for sensor values")
    monitor_p.add_argument("--duration", type=float, default=10.0, help="Collection duration in seconds (default: 10)")
    monitor_p.add_argument("--json", action="store_true", help="Output JSON format")
    monitor_p.add_argument("--temps-only", action="store_true", help="Only show temperature readings")

    # energy command group
    energy_p = sub.add_parser("energy", help="Energy blocking control commands")
    energy_sub = energy_p.add_subparsers(dest="energy_cmd", required=True)

    # energy block-compressor
    energy_sub.add_parser("block-compressor", help="Block compressor from running")

    # energy unblock-compressor
    energy_sub.add_parser("unblock-compressor", help="Unblock compressor, restore normal operation")

    # energy block-aux-heater
    energy_sub.add_parser("block-aux-heater", help="Block auxiliary heater from running")

    # energy unblock-aux-heater
    energy_sub.add_parser("unblock-aux-heater", help="Unblock auxiliary heater, restore normal operation")

    # energy status
    energy_status_p = energy_sub.add_parser("status", help="Show energy blocking status")
    energy_status_p.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

    # energy clear-all
    energy_sub.add_parser("clear-all", help="Clear all energy blocking restrictions")

    # energy block-all
    energy_sub.add_parser("block-all", help="Block both compressor and auxiliary heater")

    return parser


def resolve_param(client: HeatPumpClient, param: str) -> Any:
    try:
        idx = int(param)
        return client.get(idx)
    except ValueError:
        return client.get(param)


def format_value(decoded: Any, fmt: str) -> str:
    """Format decoded value with appropriate unit based on format type."""
    if fmt == "tem" or fmt.startswith("temp"):
        return f"{decoded}°C"
    elif fmt.startswith("dp") or fmt.startswith("rp"):
        # Decimal point formats - value already scaled
        return str(decoded)
    else:
        return str(decoded)


def _configure_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.verbose else logging.ERROR
    logging.basicConfig(level=level)
    log_file = args.log_file or os.path.expanduser("~/.cache/buderus-wps/buderus.log")
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3)
        handler.setLevel(level)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.addHandler(handler)
    except Exception:
        pass


# --- Broadcast Read Helpers (T015, T025) ---

from typing import Optional, Tuple


def read_from_broadcast(
    adapter: "USBtinAdapter",
    param_name: str,
    duration: float = 5.0
) -> Optional[Tuple[float, bytes]]:
    """
    Read parameter value from broadcast traffic.

    Args:
        adapter: Connected USBtin adapter
        param_name: Parameter name to read
        duration: How long to collect broadcast data (seconds)

    Returns:
        Tuple of (decoded_value, raw_bytes) or None if not found
    """
    from buderus_wps.broadcast_monitor import (
        BroadcastMonitor, get_broadcast_for_param, CIRCUIT_BASES
    )

    mapping = get_broadcast_for_param(param_name)
    if mapping is None:
        return None

    base, idx = mapping
    monitor = BroadcastMonitor(adapter)
    cache = monitor.collect(duration=duration)

    # If base is None, search all circuit bases
    if base is None:
        for circuit_base in CIRCUIT_BASES:
            reading = cache.get_by_idx_and_base(idx=idx, base=circuit_base)
            if reading and reading.is_temperature and reading.temperature is not None:
                return (reading.temperature, reading.raw_data)
        return None

    # Specific base lookup
    reading = cache.get_by_idx_and_base(idx=idx, base=base)
    if reading and reading.is_temperature and reading.temperature is not None:
        return (reading.temperature, reading.raw_data)

    return None


def is_invalid_rtr_response(data: bytes, param_format: str) -> bool:
    """
    Check if RTR response is invalid and needs fallback.

    For temperature parameters, a 1-byte response indicates an incomplete
    read from the heat pump (returns 0x01 = 0.1°C instead of proper 2-byte value).

    Args:
        data: Raw bytes from RTR response
        param_format: Parameter format string (e.g., "tem", "dec")

    Returns:
        True if response is invalid and fallback should be attempted
    """
    from buderus_wps.broadcast_monitor import is_temperature_param

    # Only check for invalid response on temperature parameters
    if not is_temperature_param(param_format):
        return False

    # Temperature parameters should have 2-byte response
    # 1-byte response indicates protocol failure
    return len(data) == 1


def cmd_read(client: HeatPumpClient, args: argparse.Namespace, adapter: Optional["USBtinAdapter"] = None) -> int:
    """Read a parameter value.

    Supports:
    - Standard RTR read (default)
    - Broadcast read (--broadcast flag)
    - Automatic fallback to broadcast for invalid RTR responses (unless --no-fallback)
    """
    try:
        param = resolve_param(client, args.param)
        source = "rtr"

        # Explicit broadcast mode (T016)
        if getattr(args, 'broadcast', False):
            if adapter is None:
                print("ERROR: Adapter required for broadcast read", file=sys.stderr)
                return 1

            result = read_from_broadcast(adapter, param.text, args.duration)
            if result is None:
                print(f"ERROR: {param.text} not available via broadcast", file=sys.stderr)
                return 1

            decoded, raw = result
            source = "broadcast"
        else:
            # Standard RTR read
            raw = client.read_value(param.text, timeout=args.timeout)
            decoded = client._decode_value(param, raw)

            # Automatic fallback for invalid RTR response (US2 - but check flag here)
            if (adapter is not None and
                not getattr(args, 'no_fallback', False) and
                is_invalid_rtr_response(raw, param.format)):

                print("WARNING: RTR returned invalid data, using broadcast fallback", file=sys.stderr)
                fallback = read_from_broadcast(adapter, param.text, args.duration)
                if fallback:
                    decoded, raw = fallback
                    source = "broadcast"
                else:
                    print("WARNING: RTR returned invalid data, broadcast fallback failed", file=sys.stderr)
                    # Continue with original invalid data

        # Output result with source indication (US3)
        if getattr(args, 'json', False):
            import json
            json_output = {
                "name": param.text,
                "idx": param.idx,
                "raw": raw.hex() if isinstance(raw, bytes) else raw,
                "decoded": decoded,
                "source": source
            }
            print(json.dumps(json_output))
        else:
            formatted = format_value(decoded, param.format)
            raw_hex = raw.hex().upper() if isinstance(raw, bytes) else str(raw)
            print(f"{param.text} = {formatted}  (raw=0x{raw_hex}, idx={param.idx}, source={source})")

        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


# Named value mappings for specific parameters
# Maps (param_name, named_value) -> numeric_value
NAMED_VALUES: dict[str, dict[str, int]] = {
    "HEATING_SEASON_MODE": {
        "winter": 0,
        "automatic": 1,
        "auto": 1,
        "off": 2,
        "summer": 2,
    },
    "DHW_PROGRAM_MODE": {
        "automatic": 0,
        "auto": 0,
        "on": 1,
        "always_on": 1,
        "off": 2,
        "always_off": 2,
    },
}


def resolve_named_value(param_name: str, value: str) -> str:
    """Resolve named value to numeric value if applicable.

    Args:
        param_name: Parameter name (e.g., HEATING_SEASON_MODE)
        value: Value string (may be numeric or named like 'winter')

    Returns:
        Resolved value as string (numeric)
    """
    # Check if parameter has named values
    param_upper = param_name.upper()
    if param_upper not in NAMED_VALUES:
        return value

    # Check if value is a named value (case-insensitive)
    value_lower = value.lower()
    if value_lower in NAMED_VALUES[param_upper]:
        return str(NAMED_VALUES[param_upper][value_lower])

    return value


def cmd_write(client: HeatPumpClient, args: argparse.Namespace) -> int:
    try:
        if client._adapter.read_only or args.dry_run:
            raise PermissionError("Adapter is in read-only/dry-run mode")
        param = resolve_param(client, args.param)

        # Resolve named values (e.g., 'winter' -> 0 for HEATING_SEASON_MODE)
        resolved_value = resolve_named_value(param.text, args.value)

        client.write_value(param.text, resolved_value, timeout=args.timeout)

        # Show both original and resolved value if different
        if resolved_value != args.value:
            print(f"OK: wrote {param.text}={args.value} ({resolved_value})")
        else:
            print(f"OK: wrote {param.text}={args.value}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_list(client: HeatPumpClient, args: argparse.Namespace) -> int:
    regs = client.registry.parameters
    filt = args.filter.upper() if args.filter else None
    for p in regs:
        if filt and filt not in p.text.upper():
            continue
        print(f"{p.idx:4d} {p.extid:>14} {p.text:<40} fmt={p.format:<6} min={p.min:<6} max={p.max:<6} read={p.read}")
    return 0


def cmd_dump(client: HeatPumpClient, args: argparse.Namespace) -> int:
    errors: list[str] = []
    results = []
    for p in client.registry.parameters:
        try:
            res = client.read_parameter(p.text, timeout=args.timeout)
            if args.json:
                res_copy = dict(res)
                res_copy["raw"] = res_copy["raw"].hex() if isinstance(res_copy["raw"], (bytes, bytearray)) else res_copy["raw"]
                results.append(res_copy)
            else:
                raw = res["raw"]
                raw_hex = raw.hex() if isinstance(raw, (bytes, bytearray)) else raw
                print(f"{p.idx:4d} {p.extid:>14} {p.text:<40} decoded={res['decoded']} raw={raw_hex} fmt={p.format} min={p.min} max={p.max} read={p.read}")
        except Exception as e:
            msg = f"{p.text}: {e}"
            errors.append(msg)
            if not args.json:
                print(f"ERROR: {msg}", file=sys.stderr)
    if args.json:
        import json
        print(json.dumps({"results": results, "errors": errors}))
    return 0 if not errors else 1


def cmd_monitor(adapter: "USBtinAdapter", args: argparse.Namespace) -> int:
    """Monitor broadcast traffic and display sensor readings."""
    monitor = BroadcastMonitor(adapter)
    print(f"Monitoring CAN bus for {args.duration} seconds...", file=sys.stderr)

    filter_func = None
    if args.temps_only:
        filter_func = lambda r: r.is_temperature

    cache = monitor.collect(duration=args.duration, filter_func=filter_func)

    if args.json:
        import json
        results = []
        for can_id, reading in sorted(cache.readings.items()):
            name = monitor.get_known_name(reading)
            results.append({
                "can_id": f"0x{can_id:08X}",
                "base": f"0x{reading.base:04X}",
                "idx": reading.idx,
                "name": name,
                "dlc": reading.dlc,
                "raw_hex": reading.raw_data.hex(),
                "raw_value": reading.raw_value,
                "temperature": reading.temperature,
                "is_temperature": reading.is_temperature,
            })
        print(json.dumps({"count": len(results), "readings": results}))
    else:
        if not cache.readings:
            print("No broadcast readings captured.")
            return 0

        print(f"\nCaptured {len(cache.readings)} unique CAN IDs:\n")
        print(f"{'CAN ID':<12} {'Base':<8} {'Idx':<6} {'Name':<24} {'DLC':<5} {'Raw':<12} {'Value':<10}")
        print("-" * 90)

        for can_id, reading in sorted(cache.readings.items()):
            raw_hex = reading.raw_data.hex().upper()
            name = monitor.get_known_name(reading) or "-"
            if reading.is_temperature:
                value_str = f"{reading.temperature:.1f}°C"
            else:
                value_str = str(reading.raw_value)
            print(f"0x{can_id:08X}  0x{reading.base:04X}   {reading.idx:<6} {name:<24} {reading.dlc:<5} 0x{raw_hex:<10} {value_str}")

    return 0


def cmd_energy(client: HeatPumpClient, args: argparse.Namespace) -> int:
    """Handle energy blocking commands."""
    control = EnergyBlockingControl(client)

    if args.energy_cmd == "block-compressor":
        result = control.block_compressor(timeout=args.timeout)
        if result.success:
            print(f"OK: {result.message}")
            return 0
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            if result.error:
                print(f"  Detail: {result.error}", file=sys.stderr)
            return 1

    elif args.energy_cmd == "unblock-compressor":
        result = control.unblock_compressor(timeout=args.timeout)
        if result.success:
            print(f"OK: {result.message}")
            return 0
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            if result.error:
                print(f"  Detail: {result.error}", file=sys.stderr)
            return 1

    elif args.energy_cmd == "block-aux-heater":
        result = control.block_aux_heater(timeout=args.timeout)
        if result.success:
            print(f"OK: {result.message}")
            return 0
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            if result.error:
                print(f"  Detail: {result.error}", file=sys.stderr)
            return 1

    elif args.energy_cmd == "unblock-aux-heater":
        result = control.unblock_aux_heater(timeout=args.timeout)
        if result.success:
            print(f"OK: {result.message}")
            return 0
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            if result.error:
                print(f"  Detail: {result.error}", file=sys.stderr)
            return 1

    elif args.energy_cmd == "status":
        status = control.get_status(timeout=args.timeout)
        if args.format == "json":
            import json
            output = {
                "compressor": {
                    "blocked": status.compressor.blocked,
                    "source": status.compressor.source,
                },
                "aux_heater": {
                    "blocked": status.aux_heater.blocked,
                    "source": status.aux_heater.source,
                },
                "timestamp": status.timestamp,
            }
            print(json.dumps(output))
        else:
            print("Energy Blocking Status:")
            print(f"  Compressor: {'BLOCKED' if status.compressor.blocked else 'Normal'} (source: {status.compressor.source})")
            print(f"  Aux Heater: {'BLOCKED' if status.aux_heater.blocked else 'Normal'} (source: {status.aux_heater.source})")
        return 0

    elif args.energy_cmd == "clear-all":
        result = control.clear_all_blocks(timeout=args.timeout)
        if result.success:
            print(f"OK: {result.message}")
            return 0
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            if result.error:
                print(f"  Detail: {result.error}", file=sys.stderr)
            return 1

    elif args.energy_cmd == "block-all":
        result = control.block_all(timeout=args.timeout)
        if result.success:
            print(f"OK: {result.message}")
            return 0
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            if result.error:
                print(f"  Detail: {result.error}", file=sys.stderr)
            return 1

    print(f"Unknown energy command: {args.energy_cmd}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args)
    adapter = USBtinAdapter(args.port, baudrate=args.baud, timeout=args.timeout, read_only=args.read_only or args.dry_run)
    registry = ParameterRegistry()
    client = HeatPumpClient(adapter, registry)
    # Connect once
    try:
        adapter.connect()
    except Exception as e:
        print(f"ERROR: failed to connect to {args.port}: {e}", file=sys.stderr)
        return 1
    try:
        if args.command == "read":
            return cmd_read(client, args, adapter)
        if args.command == "write":
            return cmd_write(client, args)
        if args.command == "list":
            return cmd_list(client, args)
        if args.command == "dump":
            return cmd_dump(client, args)
        if args.command == "monitor":
            return cmd_monitor(adapter, args)
        if args.command == "energy":
            return cmd_energy(client, args)
        print("Unknown command", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
