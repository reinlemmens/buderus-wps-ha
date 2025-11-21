# Quickstart: Buderus WPS Heat Pump Python Class

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-10-24
**Audience**: Python developers integrating with Buderus WPS heat pump

## Overview

This guide demonstrates how to use the Buderus WPS heat pump parameter class to access parameter metadata, validate values, and look up parameters by index or name.

## Installation

```python
# From your project that depends on buderus_wps
from buderus_wps.parameter import Parameter, HeatPump
```

## Quick Start Examples

### Example 1: Accessing Parameters by Name

```python
from buderus_wps.parameter import HeatPump

# Create heat pump instance (loads all 400+ parameters)
heat_pump = HeatPump()

# Look up a parameter by its human-readable name
access_level_param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

print(f"Parameter: {access_level_param.text}")
print(f"Index: {access_level_param.idx}")
print(f"Address: {access_level_param.extid}")
print(f"Valid range: {access_level_param.min} to {access_level_param.max}")
print(f"Format: {access_level_param.format}")
print(f"Writable: {access_level_param.is_writable()}")

# Output:
# Parameter: ACCESS_LEVEL
# Index: 1
# Address: 61E1E1FC660023
# Valid range: 0 to 5
# Format: int
# Writable: True
```

### Example 2: Accessing Parameters by Index

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# Look up by index (useful when receiving index-based data from device)
param = heat_pump.get_parameter_by_index(11)

print(f"[{param.idx}] {param.text}")
print(f"Temperature range: {param.min}°C to {param.max}°C")

# Output:
# [11] ADDITIONAL_BLOCK_HIGH_T2_TEMP
# Temperature range: -30°C to 40°C
```

### Example 3: Validating Parameter Values

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()
param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

# Check if a value is valid before sending to device
test_values = [0, 3, 5, 10, -1]

for value in test_values:
    if param.validate_value(value):
        print(f"✓ {value} is valid for {param.text}")
    else:
        print(f"✗ {value} is out of range for {param.text} ({param.min}-{param.max})")

# Output:
# ✓ 0 is valid for ACCESS_LEVEL
# ✓ 3 is valid for ACCESS_LEVEL
# ✓ 5 is valid for ACCESS_LEVEL
# ✗ 10 is out of range for ACCESS_LEVEL (0-5)
# ✗ -1 is out of range for ACCESS_LEVEL (0-5)
```

### Example 4: Checking Read-Only Parameters

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# Check if parameter can be written
param_writable = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
param_readonly = heat_pump.get_parameter_by_name("ADDITIONAL_DHW_ACKNOWLEDGED")

print(f"{param_writable.text}: writable={param_writable.is_writable()}")
print(f"{param_readonly.text}: writable={param_readonly.is_writable()}")

# Output:
# ACCESS_LEVEL: writable=True
# ADDITIONAL_DHW_ACKNOWLEDGED: writable=False
```

### Example 5: Listing All Parameters

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# Get total count
total = heat_pump.parameter_count()
print(f"Total parameters: {total}")

# List first 10 parameters
for param in heat_pump.list_all_parameters()[:10]:
    writable_flag = "RW" if param.is_writable() else "RO"
    print(f"[{param.idx:3d}] {param.text:45s} [{writable_flag}] {param.min:6d}-{param.max:6d}")

# Output:
# Total parameters: 400+
# [  0] ACCESSORIES_CONNECTED_BITMASK              [RW]      0-     0
# [  1] ACCESS_LEVEL                                [RW]      0-     5
# [  2] ACCESS_LEVEL_TIMEOUT_DELAY_TIME            [RW]      1-   240
# ...
```

### Example 6: Filtering by Writability

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# Get only writable parameters
writable = heat_pump.list_writable_parameters()
print(f"Writable parameters: {len(writable)}")

# Get only read-only parameters
readonly = heat_pump.list_readonly_parameters()
print(f"Read-only parameters: {len(readonly)}")

# Show first 5 writable parameters
print("\nFirst 5 writable parameters:")
for param in writable[:5]:
    print(f"  [{param.idx}] {param.text}")
```

### Example 7: Safe Parameter Lookup

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# Handle missing parameters gracefully
def safe_lookup_by_name(heat_pump, name):
    try:
        return heat_pump.get_parameter_by_name(name)
    except KeyError:
        print(f"Parameter '{name}' not found")
        return None

# Try to look up parameter that doesn't exist
param = safe_lookup_by_name(heat_pump, "NONEXISTENT_PARAMETER")
if param:
    print(f"Found: {param.text}")
else:
    print("Could not find parameter")

# Output:
# Parameter 'NONEXISTENT_PARAMETER' not found
# Could not find parameter
```

### Example 8: Integration with Device Communication

```python
from buderus_wps.parameter import HeatPump
from buderus_wps.can_adapter import USBtinAdapter  # Hypothetical usage

heat_pump = HeatPump()
adapter = USBtinAdapter('/dev/ttyACM0')

def set_parameter_safe(adapter, param_name, value):
    """Safely set a parameter value with validation."""
    # Look up parameter metadata
    param = heat_pump.get_parameter_by_name(param_name)

    # Check if writable
    if not param.is_writable():
        raise ValueError(f"{param_name} is read-only")

    # Validate value
    if not param.validate_value(value):
        raise ValueError(
            f"Value {value} out of range for {param_name} "
            f"(allowed: {param.min}-{param.max})"
        )

    # Send to device (implementation depends on CAN adapter)
    # adapter.write_parameter(param.extid, value)
    print(f"✓ Would write {value} to {param_name} (extid={param.extid})")

# Usage
try:
    set_parameter_safe(adapter, "ACCESS_LEVEL", 3)  # Valid
    set_parameter_safe(adapter, "ACCESS_LEVEL", 10)  # Invalid - out of range
except ValueError as e:
    print(f"Error: {e}")

# Output:
# ✓ Would write 3 to ACCESS_LEVEL (extid=61E1E1FC660023)
# Error: Value 10 out of range for ACCESS_LEVEL (allowed: 0-5)
```

## Common Use Cases

### Use Case 1: Parameter Discovery

Display all parameters with their valid ranges for documentation:

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# Generate parameter reference
with open("parameter_reference.txt", "w") as f:
    for param in heat_pump.list_all_parameters():
        f.write(f"{param.idx:4d} | {param.text:50s} | "
                f"{param.min:8d} | {param.max:8d} | "
                f"{'RW' if param.is_writable() else 'RO'}\n")
```

### Use Case 2: Configuration Validation

Validate a configuration file before applying to device:

```python
from buderus_wps.parameter import HeatPump
import json

heat_pump = HeatPump()

# Load config from file
with open("config.json") as f:
    config = json.load(f)  # {"ACCESS_LEVEL": 3, "ROOM_TEMP_LIMIT_MIN": 18}

# Validate all settings
errors = []
for param_name, value in config.items():
    try:
        param = heat_pump.get_parameter_by_name(param_name)

        if not param.is_writable():
            errors.append(f"{param_name} is read-only")
        elif not param.validate_value(value):
            errors.append(f"{param_name}={value} out of range ({param.min}-{param.max})")
    except KeyError:
        errors.append(f"{param_name} does not exist")

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✓ Configuration valid")
```

### Use Case 3: Interactive Parameter Browser

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

def search_parameters(query):
    """Search for parameters by name substring."""
    query_upper = query.upper()
    matches = [
        param for param in heat_pump.list_all_parameters()
        if query_upper in param.text
    ]
    return matches

# Search for temperature-related parameters
temp_params = search_parameters("TEMP")
print(f"Found {len(temp_params)} temperature parameters:")
for param in temp_params[:10]:
    print(f"  [{param.idx}] {param.text}")
```

## Error Handling

```python
from buderus_wps.parameter import HeatPump

heat_pump = HeatPump()

# KeyError when parameter doesn't exist
try:
    param = heat_pump.get_parameter_by_index(9999)
except KeyError:
    print("Parameter index 9999 does not exist")

try:
    param = heat_pump.get_parameter_by_name("INVALID_NAME")
except KeyError:
    print("Parameter name 'INVALID_NAME' does not exist")

# Use has_* methods to check existence
if heat_pump.has_parameter_index(1):
    param = heat_pump.get_parameter_by_index(1)
    print(f"Found parameter at index 1: {param.text}")

if not heat_pump.has_parameter_name("INVALID_NAME"):
    print("Parameter 'INVALID_NAME' does not exist")
```

## Performance Notes

- Parameter lookup by index: O(1) - completes in < 1ms
- Parameter lookup by name: O(1) - completes in < 1ms
- Listing all parameters: O(n) where n=400+ - completes in < 10ms
- Memory usage: ~few KB for all 400+ parameters

All operations meet the < 1 second performance requirements (SC-002, SC-003).

## Next Steps

- See [data-model.md](./data-model.md) for detailed entity documentation
- See [research.md](./research.md) for implementation decisions
- See [tasks.md](./tasks.md) for implementation task breakdown (generated by `/speckit.tasks`)

## Related Documentation

- Constitution Principle II: Hardware Abstraction & Protocol Fidelity
- Constitution Principle III: Safety & Reliability (validation)
- FHEM Reference: `fhem/26_KM273v018.pm` - KM273_elements_default array

