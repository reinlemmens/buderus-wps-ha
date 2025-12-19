# Quickstart: Energy Blocking Control

**Feature**: 010-energy-blocking-control
**Date**: 2025-12-06

## Overview

This feature enables users to block the heat pump from using energy on high-consumption components (compressor and auxiliary heater) via CLI commands or TUI interface.

## Prerequisites

- Connected to heat pump via USB serial (USBtin adapter)
- `buderus-wps` CLI installed
- Python 3.9+

## Quick Usage

### Block Compressor (Peak Demand)

```bash
# Block compressor during peak electricity rates
buderus-wps energy block-compressor

# Output: Compressor blocked successfully
```

### Check Status

```bash
buderus-wps energy status

# Output:
# Energy Blocking Status:
#   Compressor:     BLOCKED (user)
#   Aux Heater:     Normal
```

### Restore Normal Operation

```bash
# Clear all blocks at once
buderus-wps energy clear-all

# Output: All energy blocks cleared
```

## Library Usage

```python
from buderus_wps import USBtinAdapter, HeatPumpClient, ParameterRegistry
from buderus_wps.energy_blocking import EnergyBlockingControl

# Connect to heat pump
adapter = USBtinAdapter("/dev/ttyACM0")
adapter.connect()
client = HeatPumpClient(adapter, ParameterRegistry())

# Create blocking control
blocking = EnergyBlockingControl(client)

# Block compressor during peak rates
result = blocking.block_compressor()
if result.success:
    print("Compressor blocked")

# Check status
status = blocking.get_status()
print(f"Compressor: {'BLOCKED' if status.compressor.blocked else 'Normal'}")
print(f"Aux Heater: {'BLOCKED' if status.aux_heater.blocked else 'Normal'}")

# Restore normal operation
blocking.clear_all_blocks()
```

## Common Scenarios

### Demand Response Integration

```bash
# When receiving peak pricing signal
buderus-wps energy block-compressor
buderus-wps energy block-aux-heater

# When off-peak pricing resumes
buderus-wps energy clear-all
```

### Manual Load Shedding

```bash
# During high grid demand
buderus-wps energy block-compressor

# When demand subsides
buderus-wps energy unblock-compressor
```

## Safety Notes

- The heat pump has internal safety overrides (anti-freeze protection) that cannot be bypassed
- Blocking state persists until explicitly cleared
- Defrost cycles may temporarily override blocking for equipment protection

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Command completed successfully |
| 1 | Command failed (communication error) |
| 2 | Invalid arguments |

## JSON Output

For integration with automation systems:

```bash
buderus-wps energy status --format json
```

```json
{
  "compressor": {"blocked": true, "source": "user"},
  "aux_heater": {"blocked": false, "source": "none"}
}
```
