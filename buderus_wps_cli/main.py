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

from buderus_wps import USBtinAdapter, HeatPumpClient, ParameterRegistry


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

    # write
    write_p = sub.add_parser("write", help="Write a parameter by name or index")
    write_p.add_argument("param", help="Parameter name or index")
    write_p.add_argument("value", help="Value to write")

    # list
    list_p = sub.add_parser("list", help="List parameters")
    list_p.add_argument("--filter", default=None, help="Substring filter (case-insensitive) on name")

    return parser


def resolve_param(client: HeatPumpClient, param: str) -> Any:
    try:
        idx = int(param)
        return client.get(idx)
    except ValueError:
        return client.get(param)


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


def cmd_read(client: HeatPumpClient, args: argparse.Namespace) -> int:
    try:
        if args.json:
            result = client.read_parameter(args.param)
            # Convert raw bytes to hex for JSON
            result["raw"] = result["raw"].hex() if isinstance(result["raw"], (bytes, bytearray)) else result["raw"]
            import json

            print(json.dumps(result))
        else:
            param = resolve_param(client, args.param)
            data = client.read_value(param.text)
            decoded = client._decode_value(param, data)
            print(f"{param.text}: decoded={decoded} raw={data.hex()} idx={param.idx} extid={param.extid} fmt={param.format} min={param.min} max={param.max} read={param.read}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_write(client: HeatPumpClient, args: argparse.Namespace) -> int:
    try:
        if client._adapter.read_only or args.dry_run:
            raise PermissionError("Adapter is in read-only/dry-run mode")
        param = resolve_param(client, args.param)
        client.write_value(param.text, args.value)
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
            return cmd_read(client, args)
        if args.command == "write":
            return cmd_write(client, args)
        if args.command == "list":
            return cmd_list(client, args)
        print("Unknown command", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
