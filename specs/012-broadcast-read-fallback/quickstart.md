# Quickstart: CLI Broadcast Read Fallback

**Feature**: 012-broadcast-read-fallback
**Date**: 2025-12-06

## Overview

This guide provides step-by-step implementation instructions for adding broadcast read fallback to the CLI `read` command.

## Prerequisites

- Existing `BroadcastMonitor` class in `buderus_wps/broadcast_monitor.py`
- Existing `cmd_read()` function in `buderus_wps_cli/main.py`
- pytest test framework configured

## Implementation Steps

### Step 1: Add Parameter-to-Broadcast Mapping

**File**: `buderus_wps/broadcast_monitor.py`

Add after `KNOWN_BROADCASTS` dictionary:

```python
# Mapping from standard parameter names to broadcast (base, idx)
# Used by CLI read command for broadcast fallback
PARAM_TO_BROADCAST: Dict[str, Tuple[int, int]] = {
    "GT2_TEMP": (0x0060, 12),      # Outdoor temperature
    "GT3_TEMP": (0x0060, 58),      # DHW temperature
    # Add more mappings as verified
}

def get_broadcast_for_param(param_name: str) -> Optional[Tuple[int, int]]:
    """Get broadcast (base, idx) tuple for a parameter name."""
    return PARAM_TO_BROADCAST.get(param_name.upper())
```

### Step 2: Add CLI Arguments

**File**: `buderus_wps_cli/main.py`

Update `build_parser()` read subparser:

```python
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
```

### Step 3: Add Broadcast Read Function

**File**: `buderus_wps_cli/main.py`

Add helper function:

```python
def read_from_broadcast(
    adapter: USBtinAdapter,
    param_name: str,
    duration: float = 5.0
) -> Optional[Tuple[float, bytes]]:
    """
    Read parameter value from broadcast traffic.

    Returns:
        Tuple of (decoded_value, raw_bytes) or None if not found
    """
    from buderus_wps.broadcast_monitor import (
        BroadcastMonitor, get_broadcast_for_param
    )

    mapping = get_broadcast_for_param(param_name)
    if mapping is None:
        return None

    base, idx = mapping
    monitor = BroadcastMonitor(adapter)
    cache = monitor.collect(duration=duration)

    reading = cache.get_by_idx_and_base(idx=idx, base=base)
    if reading and reading.is_temperature:
        return (reading.temperature, reading.raw_data)

    return None
```

### Step 4: Update cmd_read Function

**File**: `buderus_wps_cli/main.py`

Modify `cmd_read()` to support broadcast mode and fallback:

```python
def cmd_read(client: HeatPumpClient, adapter: USBtinAdapter, args: argparse.Namespace) -> int:
    try:
        param = resolve_param(client, args.param)
        source = "rtr"

        # Explicit broadcast mode
        if args.broadcast:
            result = read_from_broadcast(adapter, param.text, args.duration)
            if result is None:
                print(f"ERROR: {param.text} not available via broadcast", file=sys.stderr)
                return 1
            decoded, raw = result
            source = "broadcast"
        else:
            # Standard RTR read
            data = client.read_value(param.text, timeout=args.timeout)
            decoded = client._decode_value(param, data)
            raw = data

            # Check for invalid response and attempt fallback
            if (not args.no_fallback and
                param.format in ("tem", "temp") and
                len(data) == 1):
                # Invalid 1-byte response for temperature - try broadcast
                fallback = read_from_broadcast(adapter, param.text, args.duration)
                if fallback:
                    decoded, raw = fallback
                    source = "broadcast"
                else:
                    # Fallback failed - warn user
                    print(f"WARNING: RTR returned invalid data, broadcast fallback failed",
                          file=sys.stderr)

        # Output result
        if args.json:
            import json
            result = {
                "name": param.text,
                "idx": param.idx,
                "raw": raw.hex() if isinstance(raw, bytes) else raw,
                "decoded": decoded,
                "source": source
            }
            print(json.dumps(result))
        else:
            formatted = format_value(decoded, param.format)
            raw_hex = raw.hex().upper() if isinstance(raw, bytes) else raw
            print(f"{param.text} = {formatted}  (raw=0x{raw_hex}, idx={param.idx}, source={source})")

        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
```

### Step 5: Update main() Function

**File**: `buderus_wps_cli/main.py`

Pass adapter to cmd_read:

```python
if args.command == "read":
    return cmd_read(client, adapter, args)
```

## Testing

### Unit Tests

**File**: `tests/unit/test_cli.py`

```python
def test_read_broadcast_flag_parsed():
    """Test --broadcast flag is recognized."""
    from buderus_wps_cli.main import build_parser
    parser = build_parser()
    args = parser.parse_args(["read", "GT2_TEMP", "--broadcast"])
    assert args.broadcast is True

def test_read_duration_default():
    """Test --duration has correct default."""
    from buderus_wps_cli.main import build_parser
    parser = build_parser()
    args = parser.parse_args(["read", "GT2_TEMP"])
    assert args.duration == 5.0

def test_read_no_fallback_flag():
    """Test --no-fallback flag is recognized."""
    from buderus_wps_cli.main import build_parser
    parser = build_parser()
    args = parser.parse_args(["read", "GT2_TEMP", "--no-fallback"])
    assert args.no_fallback is True
```

### Integration Tests

**File**: `tests/integration/test_broadcast_read.py`

```python
def test_broadcast_read_returns_temperature(mock_adapter_with_broadcast):
    """Test broadcast read returns valid temperature."""
    # Mock adapter returns broadcast traffic with GT2_TEMP
    result = read_from_broadcast(mock_adapter_with_broadcast, "GT2_TEMP", duration=1.0)
    assert result is not None
    temp, raw = result
    assert 0 <= temp <= 50  # Reasonable outdoor temp range

def test_broadcast_fallback_on_invalid_rtr(mock_adapter_invalid_rtr):
    """Test automatic fallback when RTR returns 1-byte response."""
    # Mock adapter returns 1-byte RTR response, valid broadcast
    # Verify fallback is triggered and returns broadcast value
    pass
```

## Verification

After implementation, verify with real hardware:

```bash
# Test explicit broadcast mode
wps-cli read GT2_TEMP --broadcast

# Test automatic fallback (should show source=broadcast)
wps-cli read GT2_TEMP

# Test JSON output includes source
wps-cli read GT2_TEMP --json

# Test no-fallback returns RTR result with warning
wps-cli read GT2_TEMP --no-fallback
```

## Rollback

If issues arise, the changes are additive and can be reverted by:
1. Removing `--broadcast`, `--duration`, `--no-fallback` arguments
2. Reverting `cmd_read()` to original implementation
3. Keeping `PARAM_TO_BROADCAST` mapping for future use
