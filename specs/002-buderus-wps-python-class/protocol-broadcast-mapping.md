# CAN Bus Broadcast Mapping Reference

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-12-06
**Status**: Hardware Verified
**Hardware**: Buderus WPS heat pump with USBtin CAN adapter

## Overview

This document describes the CAN bus broadcast message structure used by Buderus WPS heat pumps. Data was captured via passive monitoring of CAN bus traffic and verified against actual display values.

## CAN ID Structure

Buderus WPS uses 29-bit extended CAN IDs with the following structure:

```
CAN ID (29 bits): PPPP PPII IIII IIII IIII BBBB BBBB BBBB BB
                  |         |                   |
                  Prefix    Index (12 bits)     Base (14 bits)
                  (4 bits)
```

### Bit Fields

| Field | Bits | Range | Description |
|-------|------|-------|-------------|
| Prefix | 31-28 | 0x0-0xF | Message type identifier |
| Index | 27-14 | 0-4095 | Parameter/sensor index |
| Base | 13-0 | 0x0000-0x3FFF | Element type/circuit |

### Decoding Example

```python
def decode_can_id(can_id: int) -> tuple:
    """Decode CAN ID into components."""
    base = can_id & 0x3FFF           # Bits 13-0
    idx = (can_id >> 14) & 0xFFF     # Bits 25-14
    prefix = can_id >> 26            # Bits 31-26
    return (prefix, idx, base)

# Example: 0x0C084063
# prefix = 0x03 (response/broadcast)
# idx = 33
# base = 0x0063 (Circuit 3)
```

## Prefix Values

| Prefix | Hex | Description |
|--------|-----|-------------|
| 0x00 | `0x00xxxxxx` | Status frames |
| 0x04 | `0x04xxxxxx` | RTR Request (write/read request) |
| 0x08 | `0x08xxxxxx` | Counter/timer frames |
| 0x0C | `0x0Cxxxxxxx` | Data response/broadcast frames |

## Base Element Addresses

### Circuit Elements (0x0060-0x0063)

Temperature and status data per heating circuit.

| Base | Element | Description |
|------|---------|-------------|
| 0x0060 | E21 / Circuit 0 | Primary heating circuit |
| 0x0061 | E22 / Circuit 1 | Secondary heating circuit |
| 0x0062 | E31 / Circuit 2 | Third heating circuit |
| 0x0063 | E32 / Circuit 3 | Fourth heating circuit |

### Status and Configuration Elements

| Base | Element | Description |
|------|---------|-------------|
| 0x0270 | Status | Operating status, compressor data |
| 0x0402 | Pump/Circulation | Pump status, flow data, room sensors |
| 0x0403 | Pump Extended | Additional pump/circulation data |
| 0x0430 | Configuration | System configuration values |
| 0x3FE0 | Parameter RTR | RTR-based parameter read/write |

## Broadcast Temperature Mappings

### Outdoor Temperature

| CAN ID | Base | Index | Description | Verified |
|--------|------|-------|-------------|----------|
| 0x00030060 | 0x0060 | 12 | Outdoor temp (GT2) | Yes |
| 0x00030061 | 0x0061 | 12 | Outdoor temp (copy) | Yes |
| 0x00030062 | 0x0062 | 12 | Outdoor temp (copy) | Yes |
| 0x00030063 | 0x0063 | 12 | Outdoor temp (copy) | Yes |

### Room Temperature (from internal sensors)

| CAN ID | Base | Index | Description |
|--------|------|-------|-------------|
| 0x0C084060 | 0x0060 | 33 | Room temp Circuit 0 |
| 0x0C084061 | 0x0061 | 33 | Room temp Circuit 1 |
| 0x0C084062 | 0x0062 | 33 | Room temp Circuit 2 |
| 0x0C084063 | 0x0063 | 33 | Room temp Circuit 3 |

### RC10 Room Controller Data

RC10 room controllers broadcast their data to **different locations depending on which circuit they control**. This is a key discovery from hardware testing.

#### Circuit-Specific RC10 Broadcast Patterns

| Circuit | RC10 Display | Room Temp Location | Demand Location |
|---------|--------------|-------------------|-----------------|
| C1 | Shows "1" | idx=0, base=0x0060 | idx=18, base=0x0060 |
| C3 | Shows "3" | idx=55, base=0x0402 | idx=107, base=0x0402 |

#### Demand Setpoint Index Pattern

The demand setpoint uses **idx=18** on circuit-specific bases. This was observed during live testing:

| CAN ID | Base | Index | Circuit | Verified |
|--------|------|-------|---------|----------|
| 0x0C048060 | 0x0060 | 18 | C1 | Yes (change captured) |
| 0x0C048062 | 0x0062 | 18 | C2 | Yes (change captured) |

**Note**: C3's RC10 broadcasts demand on the shared base 0x0402 (idx=107) instead of the circuit-specific base 0x0063.

#### C1 RC10 Controller (Circuit 1)

The RC10 controlling Circuit 1 broadcasts on **circuit-specific base 0x0060**:

| CAN ID | Base | Index | Description | Verified |
|--------|------|-------|-------------|----------|
| 0x0C000060 | 0x0060 | 0 | C1 RC10 Room Temperature | Yes (20.5°C) |
| 0x0C14C060 | 0x0060 | 83 | C1 RC10 Room Temperature (copy) | Yes |
| 0x0C048060 | 0x0060 | 18 | C1 RC10 Temperature Demand/Setpoint | Yes (19.0°C) |

#### C3 RC10 Controller (Circuit 3)

The RC10 controlling Circuit 3 broadcasts on **shared base 0x0402**:

| CAN ID | Base | Index | Description | Verified |
|--------|------|-------|-------------|----------|
| 0x0C0DC402 | 0x0402 | 55 | C3 RC10 Room Temperature | Yes (22.1°C) |
| 0x0C188402 | 0x0402 | 98 | C3 RC10 Room Temperature (copy) | Yes |
| 0x0C1AC402 | 0x0402 | 107 | C3 RC10 Temperature Demand/Setpoint | Yes (change captured: 18.5→21.5°C) |

**Important Notes**:
- The number displayed on the RC10 indicates which heating circuit it controls
- Different RC10s use different CAN bases (circuit-specific vs shared)
- Demand values may show intermediate transition values when changed (e.g., 21.0 → 19.5 → 19.0)
- Some broadcasts occur less frequently than others (demand may require 30+ second captures)

### DHW (Domestic Hot Water) Temperature

| CAN ID | Base | Index | Description |
|--------|------|-------|-------------|
| 0x0C0E8060 | 0x0060 | 58 | DHW Actual Temperature |
| 0x0C0E8062 | 0x0062 | 58 | DHW Actual Temperature (copy) |

### Heat Pump Internal Sensors

| CAN ID | Base | Index | Description | Typical Range |
|--------|------|-------|-------------|---------------|
| 0x08000270 | 0x0270 | 0 | Supply Line Temp | 35-50°C |
| 0x08004270 | 0x0270 | 1 | Compressor Discharge | 60-80°C |
| 0x0800C270 | 0x0270 | 3 | Hot Gas Temp | 50-70°C |
| 0x08010270 | 0x0270 | 4 | Heat Exchanger | 20-50°C |
| 0x08014270 | 0x0270 | 5 | Condenser Out | 35-50°C |
| 0x08018270 | 0x0270 | 6 | Flow Temp | 40-55°C |
| 0x08020270 | 0x0270 | 8 | Compressor Suction | 60-75°C |

### Common/Shared Sensors

| CAN ID | Base | Index | Description |
|--------|------|-------|-------------|
| 0x0C08C060-63 | 0x0060-63 | 35 | Common sensor (17.0°C typical) |
| 0x0C0EC060-63 | 0x0060-63 | 59 | Brine/ground temp (5-7°C) |
| 0x0C0F0060-63 | 0x0060-63 | 60 | Supply setpoint (high values ~100°C) |

## Data Format

### Temperature Values

All temperature values use **factor 0.1** (tenths of degrees Celsius):

```python
raw_value = 220  # From CAN frame
temperature_celsius = raw_value / 10.0  # = 22.0°C
```

### Data Length (DLC)

| DLC | Description | Value Range |
|-----|-------------|-------------|
| 1 | Single byte | 0-255 (0.0-25.5°C for temps) |
| 2 | Two bytes (big-endian) | 0-65535 |

**Important**: Many parameters use 1-byte storage regardless of their documented min/max range. Always check actual DLC from responses.

## Access Methods

### Passive Monitoring (Recommended)

Sensor values are continuously broadcast on the CAN bus. Use passive monitoring for:
- Real-time temperature readings
- Status monitoring
- No impact on heat pump operation

```python
from buderus_wps import USBtinAdapter, BroadcastMonitor

adapter = USBtinAdapter('/dev/ttyACM0')
adapter.connect()
monitor = BroadcastMonitor(adapter)

# Collect readings for 10 seconds
cache = monitor.collect(duration=10)

# Get temperature readings
for reading in cache.get_temperatures():
    print(f"0x{reading.can_id:08X}: {reading.temperature}°C")
```

### RTR-Based Parameter Access

Configuration parameters use Request-To-Respond (RTR) protocol:

```python
# Request CAN ID:  0x04003FE0 | (parameter_idx << 14)
# Response CAN ID: 0x0C003FE0 | (parameter_idx << 14)

# Example: Read parameter idx=459 (DHW_MAX_TIME)
request_id = 0x04003FE0 | (459 << 14)  # = 0x072FFFE0
response_id = 0x0C003FE0 | (459 << 14) # = 0x0F2FFFE0
```

## Verified Hardware Configuration

**Test Setup** (2025-12-06):
- Buderus WPS heat pump
- USBtin CAN adapter on Raspberry Pi
- RC10 room controller on Circuit 1 (displays "1")
- RC10 room controller on Circuit 3 (displays "3")
- Passive monitoring via `wps-cli monitor`

**Verified Values - Circuit 1 (RC10 shows "1")**:
| Display | Broadcast | CAN Location |
|---------|-----------|--------------|
| Outside: 10.5°C | 10.5°C | 0x00030060 (idx=12, base=0x0060) |
| Inside: 20.5°C | 20.5°C | 0x0C000060 (idx=0, base=0x0060) |
| Demand: 19.0°C | 19.0°C | 0x0C048060 (idx=18, base=0x0060) |

**Verified Values - Circuit 3 (RC10 shows "3")**:
| Display | Broadcast | CAN Location |
|---------|-----------|--------------|
| Outside: 10.5°C | 10.5°C | 0x00030062 (idx=12, base=0x0062) |
| Room: 22.1°C | 22.1°C | 0x0C0DC402 (idx=55, base=0x0402) |
| Demand: 22.5°C | 22.5°C | 0x0C1AC402 (idx=107, base=0x0402) |

## Related Files

- [buderus_wps/broadcast_monitor.py](../../buderus_wps/broadcast_monitor.py) - Passive monitoring implementation
- [buderus_wps/can_message.py](../../buderus_wps/can_message.py) - CAN ID constants and structure
- [fhem/26_KM273v018.pm](../../fhem/26_KM273v018.pm) - FHEM reference implementation

## Revision History

| Date | Change |
|------|--------|
| 2025-12-06 | Initial documentation from hardware testing |
| 2025-12-06 | Added C1 RC10 controller mappings; discovered circuit-specific broadcast patterns |
| 2025-12-06 | Verified C3 demand change capture; discovered idx=18 demand pattern on circuit bases |
