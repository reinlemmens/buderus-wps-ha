# Quickstart: Buderus WPS Heat Pump Python Class with Dynamic Discovery

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-12-18 (Updated)
**Audience**: Python developers integrating with Buderus WPS heat pump

## Overview

This guide demonstrates how to use the Buderus WPS heat pump parameter class to:
- Discover parameters dynamically from the device
- Access parameter metadata and calculate CAN IDs
- Validate values before sending to device
- Use caching to avoid slow discovery on reconnection

## Installation

```python
# From your project that depends on buderus_wps
from buderus_wps.parameter import Parameter, HeatPump
from buderus_wps.discovery import ParameterDiscovery  # NEW
from buderus_wps.cache import ParameterCache  # NEW
```

## Quick Start Examples

### Example 1: Basic Parameter Access (Existing)

```python
from buderus_wps.parameter import HeatPump

# Create heat pump instance (loads from cache, discovery, or fallback)
heat_pump = HeatPump()

# Look up a parameter by its human-readable name
param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

print(f"Parameter: {param.text}")
print(f"Index: {param.idx}")
print(f"Valid range: {param.min} to {param.max}")
print(f"Writable: {param.is_writable()}")

# Output:
# Parameter: ACCESS_LEVEL
# Index: 1
# Valid range: 0 to 5
# Writable: True
```

### Example 2: CAN ID Calculation (NEW)

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()
param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

# Calculate CAN IDs dynamically from parameter index
read_can_id = param.get_read_can_id()
write_can_id = param.get_write_can_id()

print(f"Parameter: {param.text} (idx={param.idx})")
print(f"Read CAN ID:  0x{read_can_id:08X}")
print(f"Write CAN ID: 0x{write_can_id:08X}")

# Output:
# Parameter: ACCESS_LEVEL (idx=1)
# Read CAN ID:  0x04007FE0
# Write CAN ID: 0x0C007FE0

# PROTOCOL: Formulas from fhem/26_KM273v018.pm:2229-2230
# Read:  rtr = 0x04003FE0 | (idx << 14)
# Write: txd = 0x0C003FE0 | (idx << 14)
```

### Example 3: Discovery with Caching (NEW)

```python
from pathlib import Path
from buderus_wps.parameter import HeatPump
from buderus_wps.can_adapter import USBtinAdapter

# Connect to device
adapter = USBtinAdapter('/dev/ttyACM0')

# Create heat pump with caching enabled
cache_path = Path.home() / ".cache" / "buderus" / "params.json"
heat_pump = HeatPump(adapter=adapter, cache_path=cache_path)

# Check where data came from
print(f"Data source: {heat_pump.data_source}")
# Output: "cache" (fast, ~1s) or "discovery" (slow, ~30s) or "fallback"

if heat_pump.using_fallback:
    print("WARNING: Using static fallback data - some parameters may not match device")
```

### Example 4: Force Re-Discovery (NEW)

```python
from buderus_wps.parameter import HeatPump
from buderus_wps.can_adapter import USBtinAdapter

adapter = USBtinAdapter('/dev/ttyACM0')

# Force discovery even if cache exists
heat_pump = HeatPump(
    adapter=adapter,
    cache_path=Path("~/.cache/buderus/params.json"),
    force_discovery=True  # Bypass cache
)

print(f"Discovered {heat_pump.parameter_count()} parameters from device")
```

### Example 5: Standalone Fallback Mode (Existing, Documented)

```python
from buderus_wps.parameter import HeatPump

# No adapter = always use static fallback data
heat_pump = HeatPump()

# Works offline with 1789 parameters from FHEM reference
print(f"Loaded {heat_pump.parameter_count()} fallback parameters")
print(f"Using fallback: {heat_pump.using_fallback}")  # True

# Useful for:
# - Development without hardware
# - Testing
# - Documentation generation
```

### Example 6: Validating Parameter Values

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()
param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

# Check if a value is valid before sending to device
for value in [0, 3, 5, 10, -1]:
    if param.validate_value(value):
        print(f"✓ {value} is valid")
    else:
        print(f"✗ {value} is out of range ({param.min}-{param.max})")

# Output:
# ✓ 0 is valid
# ✓ 3 is valid
# ✓ 5 is valid
# ✗ 10 is out of range (0-5)
# ✗ -1 is out of range (0-5)
```

### Example 7: Safe Write with CAN ID (NEW)

```python
from buderus_wps.parameter import HeatPump
from buderus_wps.can_adapter import USBtinAdapter

heat_pump = HeatPump()
adapter = USBtinAdapter('/dev/ttyACM0')

def write_parameter(adapter, param_name, value):
    """Safely write a parameter value with full validation."""
    param = heat_pump.get_parameter_by_name(param_name)

    # Check writability
    if not param.is_writable():
        raise ValueError(f"{param_name} is read-only")

    # Validate value
    if not param.validate_value(value):
        raise ValueError(f"Value {value} out of range ({param.min}-{param.max})")

    # Get dynamically calculated CAN ID
    can_id = param.get_write_can_id()

    # Send to device (hypothetical adapter method)
    # adapter.send(can_id, value)
    print(f"✓ Would write {value} to 0x{can_id:08X} ({param_name})")

# Usage
write_parameter(adapter, "ACCESS_LEVEL", 3)
# Output: ✓ Would write 3 to 0x0C007FE0 (ACCESS_LEVEL)
```

### Example 8: Reading Parameters with CAN ID (NEW)

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

def read_parameter(adapter, param_name):
    """Read a parameter value from the device."""
    param = heat_pump.get_parameter_by_name(param_name)

    # Get dynamically calculated read CAN ID
    can_id = param.get_read_can_id()

    # Request from device (hypothetical)
    # value = adapter.request(can_id)
    print(f"Would send read request to 0x{can_id:08X} ({param_name})")

    # Return value after validation
    # return value

# Usage
read_parameter(None, "ROOM_TEMP")
# Output: Would send read request to 0x04XXXXXX (ROOM_TEMP)
```

### Example 9: Listing Parameters by Category

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

def search_parameters(query):
    """Search parameters by name substring."""
    query_upper = query.upper()
    return [p for p in heat_pump.list_all_parameters() if query_upper in p.text]

# Find all temperature parameters
temp_params = search_parameters("TEMP")
print(f"Found {len(temp_params)} temperature parameters:")
for param in temp_params[:5]:
    print(f"  [{param.idx}] {param.text}")
    print(f"       Range: {param.min}°C to {param.max}°C")
    print(f"       Read CAN: 0x{param.get_read_can_id():08X}")
```

## Common Use Cases

### Use Case 1: Monitoring Dashboard

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump(adapter=adapter, cache_path=cache_path)

# Define parameters to monitor
monitor_params = [
    "ROOM_TEMP",
    "OUTDOOR_TEMP",
    "DHW_TEMP",
    "COMPRESSOR_STATE",
]

for name in monitor_params:
    if heat_pump.has_parameter_name(name):
        param = heat_pump.get_parameter_by_name(name)
        can_id = param.get_read_can_id()
        print(f"{name}: CAN ID 0x{can_id:08X}")
```

### Use Case 2: Configuration Export

```python
from buderus_wps.parameter import HeatPump
import json

heat_pump = HeatPump()

# Export writable parameters for configuration backup
writable = heat_pump.list_writable_parameters()

config = {}
for param in writable:
    config[param.text] = {
        "idx": param.idx,
        "read_can_id": f"0x{param.get_read_can_id():08X}",
        "write_can_id": f"0x{param.get_write_can_id():08X}",
        "min": param.min,
        "max": param.max,
    }

with open("writable_params.json", "w") as f:
    json.dump(config, f, indent=2)
```

### Use Case 3: Cache Management

```python
from pathlib import Path
from buderus_wps.cache import ParameterCache

cache = ParameterCache(Path("~/.cache/buderus/params.json").expanduser())

# Check if cache is valid
if cache.is_valid():
    print("Cache is valid, will load from cache")
else:
    print("Cache invalid or missing, will discover from device")

# Invalidate cache to force re-discovery
cache.invalidate()
print("Cache invalidated, next load will discover from device")
```

## Error Handling

```python
from buderus_wps.parameter import HeatPump
from buderus_wps.exceptions import DiscoveryError

heat_pump = HeatPump()

# KeyError for missing parameters
try:
    param = heat_pump.get_parameter_by_index(99999)
except KeyError:
    print("Parameter index 99999 does not exist")

# Use has_* methods for safe lookup
if heat_pump.has_parameter_name("ACCESS_LEVEL"):
    param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
    can_id = param.get_read_can_id()
```

## Data Source Priority

The HeatPump class loads parameters in this priority order:

1. **Cache** (fastest, ~1s): Valid JSON cache from previous discovery
2. **Discovery** (slow, ~30s): CAN bus protocol to retrieve from device
3. **Fallback** (always available): Static data from FHEM reference

```python
heat_pump = HeatPump(adapter=adapter, cache_path=cache_path)

match heat_pump.data_source:
    case "cache":
        print("Loaded from cache (fast)")
    case "discovery":
        print("Discovered from device (slow but accurate)")
    case "fallback":
        print("Using static data (may not match device)")
```

## Performance Notes

- Parameter lookup by index/name: O(1) - completes in < 1ms
- CAN ID calculation: O(1) - completes in < 1ms
- Discovery from device: ~30 seconds for 1789 parameters
- Cache load: < 3 seconds
- Listing all parameters: O(n) - completes in < 10ms

All operations meet success criteria SC-001 through SC-010.

## CAN ID Reference

| idx | Read CAN ID | Write CAN ID | Parameter |
|-----|-------------|--------------|-----------|
| 0 | 0x04003FE0 | 0x0C003FE0 | ACCESSORIES_CONNECTED_BITMASK |
| 1 | 0x04007FE0 | 0x0C007FE0 | ACCESS_LEVEL |
| 11 | 0x0402BFE0 | 0x0C02BFE0 | ADDITIONAL_BLOCK_HIGH_T2_TEMP |

Formula: `read = 0x04003FE0 | (idx << 14)`, `write = 0x0C003FE0 | (idx << 14)`

## Related Documentation

- [spec.md](./spec.md) - Feature specification
- [data-model.md](./data-model.md) - Detailed entity documentation
- [research.md](./research.md) - Implementation decisions
- [tasks.md](./tasks.md) - Implementation task breakdown

## FHEM Reference

- Discovery protocol: `fhem/26_KM273v018.pm:2052-2187`
- CAN ID formulas: `fhem/26_KM273v018.pm:2229-2230`
- Element parsing: `fhem/26_KM273v018.pm:2135-2143`
- Fallback data: `fhem/26_KM273v018.pm:218-2009`
