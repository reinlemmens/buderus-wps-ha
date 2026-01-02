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

All RC10 room controllers broadcast room temperature at **idx=0** and adjusted setpoint at **idx=33** on their respective circuit bases. This pattern was verified across all 4 circuits on 2024-12-28.

| Circuit | Base | Room Temp (idx) | Adjusted Setpoint (idx) | Verified |
|---------|------|-----------------|-------------------------|----------|
| C1 | 0x0060 | 0 | 33 | Yes (20.5°C) |
| C2 | 0x0061 | 0 | 33 | Yes (22.0°C) - 2024-12-28 |
| C3 | 0x0062 | 0 | 33 | Yes (22.5°C) - 2024-12-28 |
| C4 | 0x0063 | 0 | 33 | Yes (23.9°C) - 2024-12-28 |

**Note**: C3 also broadcasts on alternate location (idx=55, base=0x0402) for legacy compatibility.

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

#### C2 RC10 Controller (Circuit 2)

The RC10 controlling Circuit 2 broadcasts on **circuit-specific base 0x0061**:

| CAN ID | Base | Index | Description | Verified |
|--------|------|-------|-------------|----------|
| 0x0C000061 | 0x0061 | 0 | C2 RC10 Room Temperature | Yes (22.0°C) - 2024-12-28 |
| 0x0C14C061 | 0x0061 | 83 | C2 RC10 Room Temperature (copy) | Yes |
| 0x0C084061 | 0x0061 | 33 | C2 RC10 Adjusted Setpoint | Yes - 2024-12-28 |

#### C3 RC10 Controller (Circuit 3)

The RC10 controlling Circuit 3 broadcasts on **circuit-specific base 0x0062** (primary) and **shared base 0x0402** (alternate):

| CAN ID | Base | Index | Description | Verified |
|--------|------|-------|-------------|----------|
| 0x0C000062 | 0x0062 | 0 | C3 RC10 Room Temperature | Yes (22.5°C) - 2024-12-28 |
| 0x0C084062 | 0x0062 | 33 | C3 RC10 Adjusted Setpoint | Yes - 2024-12-28 |
| 0x0C0DC402 | 0x0402 | 55 | C3 RC10 Room Temperature (alternate) | Yes (legacy location) |
| 0x0C188402 | 0x0402 | 98 | C3 RC10 Room Temperature (copy) | Yes |
| 0x0C1AC402 | 0x0402 | 107 | C3 RC10 Temperature Demand/Setpoint | Yes (change captured: 18.5→21.5°C) |

#### C4 RC10 Controller (Circuit 4)

The RC10 controlling Circuit 4 broadcasts on **circuit-specific base 0x0063**:

| CAN ID | Base | Index | Description | Verified |
|--------|------|-------|-------------|----------|
| 0x0C000063 | 0x0063 | 0 | C4 RC10 Room Temperature | Yes (23.9°C) - 2024-12-28 |
| 0x0C14C063 | 0x0063 | 83 | C4 RC10 Room Temperature (copy) | Yes |
| 0x0C084063 | 0x0063 | 33 | C4 RC10 Adjusted Setpoint | Yes - 2024-12-28 |

**Important Notes**:
- The number displayed on the RC10 indicates which heating circuit it controls
- Different RC10s use different CAN bases (circuit-specific vs shared)
- Demand values may show intermediate transition values when changed (e.g., 21.0 → 19.5 → 19.0)
- Some broadcasts occur less frequently than others (demand may require 30+ second captures)

### DHW (Domestic Hot Water) Temperature - GT3_TEMP

**CRITICAL: GT3_TEMP (DHW actual temperature) is NOT available via broadcast.**

Broadcasts do NOT contain the actual DHW tank temperature. GT3_TEMP must be read via RTR.

#### Why Broadcast Mapping Failed

Previous attempts to map GT3_TEMP to broadcasts were incorrect:

| Attempted Mapping | Base | Index | Actual Content | Status |
|-------------------|------|-------|----------------|--------|
| ~~DHW from circuit~~ | 0x0060 | 58 | DHW setpoint/supply, NOT actual temp | **WRONG** |
| ~~DHW from 0x0270~~ | 0x0270 | 4 | DHW setpoint (~50°C), NOT actual temp | **WRONG** |
| ~~DHW from 0x0402~~ | 0x0402 | 78 | Unknown (~23°C), NOT actual temp | **WRONG** |

#### Correct Method: RTR Read

GT3_TEMP must be read via RTR using the element discovery idx:

| Parameter | Static idx | Discovered idx | Notes |
|-----------|------------|----------------|-------|
| GT3_TEMP | 681 | **682** | Varies by firmware! |

**CRITICAL INDEX DISCREPANCY**: The static parameter list (from FHEM) says GT3_TEMP is at idx=681, but the heat pump dynamically reports idx=682. Using idx=681 returns GT3_STATUS (DLC=1), not the temperature.

#### Hardware Verification (2026-01-02)

| Test | Request idx | DLC | Result |
|------|-------------|-----|--------|
| Static idx=681 | 681 | 1 | status=1 (GT3_STATUS) |
| Discovered idx=682 | 682 | **2** | **38.8°C** (GT3_TEMP) ✓ |

The raw sensor value (38.8°C) differs from display (42.8°C) by exactly 4.0K due to a configured calibration offset (GT3_KORRIGERING = +4.0K in installer menu).

#### Implementation

GT3_TEMP is read via RTR in `coordinator.py`:

```python
# Read GT3_TEMP via RTR (uses discovered idx from element discovery)
result = self._client.read_parameter("GT3_TEMP")
dhw_temp = float(result.get("decoded", 0))
```

The element discovery automatically finds the correct idx for the specific heat pump firmware.

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

## Parameter Write Access

### Write Protocol

Parameter writes use the same CAN ID formula as RTR requests:

```python
# Write CAN ID: 0x04003FE0 | (parameter_idx << 14)
# Example: XDHW_TIME (idx=2475)
can_id = 0x04003FE0 | (2475 << 14)  # = 0x066AFFE0

# SLCAN format: T<8-digit-id><dlc><data>
# Example: Write value 1 with 2 bytes
frame = "T066AFFE020001\r"
```

### Write Frame Format

| Component | Format | Example |
|-----------|--------|---------|
| Command | `T` (extended data frame) | `T` |
| CAN ID | 8 hex digits | `066AFFE0` |
| DLC | 1 hex digit (always `2`) | `2` |
| Data | 4 hex digits (big-endian) | `0001` |
| Terminator | `\r` | |

**Note**: FHEM always uses 2-byte (DLC=2) writes regardless of value size.

### FHEM-Deemed Writable Parameters (52 total)

FHEM considers the following parameters writable based on `min < max` range checks. However, **not all of these actually work** - the heat pump ignores writes to many of them.

#### 1. Extra Hot Water (XDHW) - 2 parameters
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| XDHW_TIME | Extra hot water duration (0-48 hours) | **YES - Works** |
| XDHW_STOP_TEMP | Extra hot water target temp | **YES - Works** |

#### 2. DHW Setpoint - 1 parameter
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| DHW_CALCULATED_SETPOINT_TEMP | Hot water setpoint | Untested |

#### 3. DHW Time Programs - 16 parameters
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| DHW_TIMEPROGRAM | Program selection (1-3) | **NO - Ignored** |
| DHW_PROGRAM_MODE | Operating mode (0=Auto, 1=On, 2=Off) | **YES - Works** |
| DHW_PROGRAM_1_1MON - DHW_PROGRAM_1_7SUN | Program 1 schedule (7 days) | **NO - Ignored** |
| DHW_PROGRAM_2_1MON - DHW_PROGRAM_2_7SUN | Program 2 schedule (7 days) | Untested |

#### 4. Room/Heating Programs - 17 parameters
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| ROOM_TIMEPROGRAM | Program selection | Untested |
| ROOM_PROGRAM_MODE | Operating mode | Untested |
| ROOM_PROGRAM_1_1MON - ROOM_PROGRAM_1_7SUN | Program 1 schedule (7 days) | Untested |
| ROOM_PROGRAM_2_1MON - ROOM_PROGRAM_2_7SUN | Program 2 schedule (7 days) | Untested |

#### 5. Heating Season Mode - 1 parameter
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| HEATING_SEASON_MODE | 0=Auto, 1=On, 2=Off | **YES - Works** |

#### 6. Pump DHW Programs - 8 parameters
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| PUMP_DHW_PROGRAM1_START_TIME | Program 1 start | Untested |
| PUMP_DHW_PROGRAM1_STOP_TIME | Program 1 stop | Untested |
| PUMP_DHW_PROGRAM2_START_TIME | Program 2 start | Untested |
| PUMP_DHW_PROGRAM2_STOP_TIME | Program 2 stop | Untested |
| PUMP_DHW_PROGRAM3_START_TIME | Program 3 start | Untested |
| PUMP_DHW_PROGRAM3_STOP_TIME | Program 3 stop | Untested |
| PUMP_DHW_PROGRAM4_START_TIME | Program 4 start | Untested |
| PUMP_DHW_PROGRAM4_STOP_TIME | Program 4 stop | Untested |

#### 7. Holiday Mode - 7 parameters
| Parameter | Description | Hardware Verified |
|-----------|-------------|-------------------|
| HOLIDAY_ACTIVE | Holiday mode toggle (idx=900) | Read-only (use HOLIDAY_ACTIVE_GLOBAL) |
| HOLIDAY_START_DAY | Start day | Untested |
| HOLIDAY_START_MONTH | Start month | Untested |
| HOLIDAY_START_YEAR | Start year | Untested |
| HOLIDAY_STOP_DAY | Stop day | Untested |
| HOLIDAY_STOP_MONTH | Stop month | Untested |
| HOLIDAY_STOP_YEAR | Stop year | Untested |

**Note**: FHEM lists `HOLIDAY_ACTIVE` (idx=900) but actually uses `HOLIDAY_ACTIVE_GLOBAL` (idx=901) for writes.

### Hardware-Verified Write Access (2025-12-10)

| Parameter | idx | Write Works | Notes |
|-----------|-----|-------------|-------|
| XDHW_TIME | 2475 | **Yes** | Extra hot water duration (0-48 hours) |
| XDHW_STOP_TEMP | 2473 | **Yes** | Extra hot water target temp (50.0-65.0°C) |
| HOLIDAY_ACTIVE_GLOBAL | 901 | **Yes** | Circuit 1 holiday mode (0=off, 1=on) |
| HEATING_SEASON_MODE | 884 | **Yes** | Season mode (0=Winter, 1=Auto, 2=Off/summer) |
| DHW_PROGRAM_MODE | 489 | **Yes** | DHW mode (0=Auto, 1=Always_On, 2=Always_Off) |
| DHW_TIMEPROGRAM | 494 | **No** | Program selection (heat pump ignores) |
| DHW_PROGRAM_1_* | 456-462 | **No** | Schedule times (returns stale data) |

### Write Behavior Analysis

**Successful Writes** (heat pump accepts and stores value):
- CAN frame transmitted (USBtin returns `Z` acknowledgment)
- Read-back confirms new value
- Heat pump acts on the change

**Failed Writes** (heat pump ignores):
- CAN frame transmitted successfully
- Read-back shows old/stale value
- No visible change on heat pump

### Writable Parameters (Confirmed)

The following parameter types accept CAN writes:

1. **Extra Hot Water (XDHW)**: Boost functions for on-demand hot water
   - `XDHW_TIME`: Duration in hours (0=off, 1-48=hours) - **VERIFIED**
   - `XDHW_STOP_TEMP`: Target temperature (raw value in 0.1°C) - **VERIFIED**

2. **Holiday Mode**: Vacation/absence control
   - `HOLIDAY_ACTIVE_GLOBAL` (idx=901): Controls Circuit 1 holiday mode (0=off, 1=on) - **VERIFIED**
   - Note: Despite the "GLOBAL" name, this only affects Circuit 1

3. **Heating Season Mode**: Heating enable/disable control
   - `HEATING_SEASON_MODE` (idx=884): Season mode (0=Winter, 1=Auto, 2=Off) - **VERIFIED**
   - Use case: Peak hour blocking by setting to 2 (summer mode = no heating)
   - **CRITICAL**: Heat pump reports idx=884, NOT idx=883 from static FHEM list

4. **DHW Program Mode**: DHW enable/disable control
   - `DHW_PROGRAM_MODE` (idx=489): Operating mode (0=Auto, 1=Always_On, 2=Always_Off) - **VERIFIED**
   - Use case: Peak hour blocking by setting to 2 (Always_Off = no DHW heating)
   - **CRITICAL**: Heat pump reports idx=489, NOT idx=488 from static FHEM list

### Read-Only Parameters (Write Ignored)

The heat pump ignores CAN writes to these parameter types:

1. **Time Programs**: Schedule settings protected from external changes
   - `DHW_TIMEPROGRAM`, `ROOM_TIMEPROGRAM`
   - `DHW_PROGRAM_*`, `ROOM_PROGRAM_*`
   - `PUMP_DHW_PROGRAM*`

2. **Operating Mode Selection**: Core operating modes
   - `ROOM_PROGRAM_MODE`
   - ~~`DHW_PROGRAM_MODE`~~ - **Now verified writable** (see below)
   - ~~`HEATING_SEASON_MODE`~~ - **Now verified writable** (see below)

3. **Energy Blocking**: External control parameters
   - `COMPRESSOR_EXTERN_BLOCK`, `ADDITIONAL_HEATER_EXTERN_BLOCK`
   - Note: These appear writable (min < max) but heat pump ignores writes

### Write Detection Heuristic

To determine if a parameter is truly writable:

```python
def is_writable(param) -> bool:
    """Check if parameter accepts CAN writes."""
    # Basic check: must have valid range
    if param.min >= param.max:
        return False  # Read-only status value

    # Known writable patterns (hardware verified)
    if param.text.startswith('XDHW_') and param.text in ['XDHW_TIME', 'XDHW_STOP_TEMP']:
        return True
    if param.text == 'HOLIDAY_ACTIVE_GLOBAL':
        return True
    if param.text == 'HEATING_SEASON_MODE':
        return True  # Peak hour blocking via summer mode
    if param.text == 'DHW_PROGRAM_MODE':
        return True  # DHW blocking via Always_Off mode

    # Known read-only patterns (heat pump ignores writes)
    readonly_patterns = [
        'TIMEPROGRAM', 'PROGRAM_MODE', '_PROGRAM_',
        'EXTERN_BLOCK',  # Energy blocking doesn't work via CAN
    ]
    for pattern in readonly_patterns:
        if pattern in param.text:
            return False

    # Unknown - needs hardware verification
    return None  # Unknown, may or may not work
```

### Important Findings

1. **CAN acknowledgment ≠ write success**: USBtin `Z` response only confirms transmission, not acceptance
2. **Read-back required**: Always verify writes by reading back the parameter
3. **Timing sensitive**: Some parameters need 500ms+ delay before read-back shows new value
4. **Protected parameters**: Schedule/program settings cannot be changed via CAN (security feature)

## Holiday Mode Parameters

**Hardware Verified** (2025-12-10):

The heat pump has two holiday-related parameters with confusing naming:

| Parameter | idx | CAN ID (Write) | Purpose | Verified |
|-----------|-----|----------------|---------|----------|
| HOLIDAY_ACTIVE | 900 | 0x04E13FE0 | Unknown (always reads 0) | Read only |
| HOLIDAY_ACTIVE_GLOBAL | 901 | 0x04E17FE0 | **Controls Circuit 1 holiday mode** | Read/Write |

### Key Findings

1. **FHEM uses idx=901**: Despite showing "HOLIDAY_ACTIVE" in the UI, FHEM internally writes to idx=901 (`HOLIDAY_ACTIVE_GLOBAL`)

2. **Naming is misleading**: `HOLIDAY_ACTIVE_GLOBAL` (idx=901) only controls Circuit 1's holiday mode, not a global setting

3. **idx=900 purpose unknown**: `HOLIDAY_ACTIVE` (idx=900) always reads 0 regardless of holiday mode state; may be a status flag or unused

### CAN ID Calculation

```python
# HOLIDAY_ACTIVE_GLOBAL (idx=901)
write_id = 0x04003FE0 | (901 << 14)  # = 0x04E17FE0
read_id  = 0x0C003FE0 | (901 << 14)  # = 0x0CE17FE0

# SLCAN write frame (enable holiday mode):
frame = "T04E17FE020001\r"  # value=1

# SLCAN write frame (disable holiday mode):
frame = "T04E17FE020000\r"  # value=0
```

### CLI Usage

```bash
# Read holiday mode status
wps-cli read HOLIDAY_ACTIVE_GLOBAL

# Enable holiday mode on Circuit 1
wps-cli write HOLIDAY_ACTIVE_GLOBAL 1

# Disable holiday mode on Circuit 1
wps-cli write HOLIDAY_ACTIVE_GLOBAL 0
```

## Heating Season Mode (Peak Hour Blocking)

**Hardware Verified** (2025-12-10):

HEATING_SEASON_MODE controls whether the heat pump provides space heating. This can be used for temporary heating blocking during electricity peak hours.

| Parameter | idx | CAN ID (Write) | Values | Verified |
|-----------|-----|----------------|--------|----------|
| HEATING_SEASON_MODE | 884 | 0x04DD3FE0 | 0=Winter, 1=Auto, 2=Off | Read/Write |

**CRITICAL INDEX DISCREPANCY**: The static FHEM parameter list shows idx=883, but the heat pump dynamically reports idx=884. FHEM works because it uses the dynamically-read index from the heat pump. Our implementation has been corrected to use idx=884.

### Value Meanings

| Value | FHEM Display | Heat Pump Menu | Behavior |
|-------|--------------|----------------|----------|
| 0 | Winter | Winter mode | **FORCED HEATING** - heating always enabled |
| 1 | Automatic | Automatic | Normal operation (heating based on outdoor temp) |
| 2 | Off | Summer mode | **NO HEATING** - hot water only |

### Use Case: Peak Hour Blocking

Setting `HEATING_SEASON_MODE = 2` during electricity peak hours provides:
- Complete heating suspension (compressor won't run for heating)
- Hot water production remains available
- Quick restoration by setting back to 1 (Automatic)

**Important**: Unlike EVU blocking (which the heat pump ignores via CAN), this method actually works to temporarily disable heating.

### CAN ID Calculation

```python
# HEATING_SEASON_MODE (idx=884) - HARDWARE-VERIFIED
write_id = 0x04003FE0 | (884 << 14)  # = 0x04DD3FE0
read_id  = 0x0C003FE0 | (884 << 14)  # = 0x0CDD3FE0

# SLCAN write frame (enable summer/off mode):
frame = "T04DD3FE020002\r"  # value=2

# SLCAN write frame (restore automatic):
frame = "T04DD3FE020001\r"  # value=1 (not 0!)
```

### CLI Usage

```bash
# Read current season mode
wps-cli read HEATING_SEASON_MODE

# Disable heating (summer mode / peak hour blocking)
wps-cli write HEATING_SEASON_MODE summer    # or: off, 2

# Restore automatic operation
wps-cli write HEATING_SEASON_MODE automatic # or: auto, 1

# Force heating (winter mode)
wps-cli write HEATING_SEASON_MODE winter    # or: 0
```

**Named Values**: The CLI supports named values (case-insensitive):
| Name | Value | Effect |
|------|-------|--------|
| `winter` | 0 | Forced heating |
| `automatic`, `auto` | 1 | Normal operation |
| `summer`, `off` | 2 | No heating |

## DHW Program Mode (DHW Blocking)

**Hardware Verified** (2025-12-10):

DHW_PROGRAM_MODE controls whether the heat pump heats domestic hot water. This can be used to disable DHW during electricity peak hours.

| Parameter | idx | CAN ID (Write) | Values | Verified |
|-----------|-----|----------------|--------|----------|
| DHW_PROGRAM_MODE | 489 | 0x047ABFE0 | 0=Auto, 1=Always_On, 2=Always_Off | Read/Write |

**CRITICAL INDEX DISCREPANCY**: The static FHEM parameter list shows idx=488, but the heat pump dynamically reports idx=489. Our implementation has been corrected to use idx=489.

### Value Meanings

| Value | FHEM Display | Heat Pump Menu | Behavior |
|-------|--------------|----------------|----------|
| 0 | Automatic | Automatic | Normal operation (follows time program) |
| 1 | Always_On | Always On | DHW always active |
| 2 | Always_Off | Always Off | **NO DHW** - no hot water heating |

### Use Case: Peak Hour Blocking

Setting `DHW_PROGRAM_MODE = 2` during electricity peak hours provides:
- Complete DHW suspension (compressor won't run for hot water)
- Space heating remains available (unless also blocked)
- Quick restoration by setting back to 0 (Automatic)

### CAN ID Calculation

```python
# DHW_PROGRAM_MODE (idx=489) - HARDWARE-VERIFIED
write_id = 0x04003FE0 | (489 << 14)  # = 0x047ABFE0
read_id  = 0x0C003FE0 | (489 << 14)  # = 0x0C7ABFE0

# SLCAN write frame (disable DHW):
frame = "T047ABFE020002\r"  # value=2

# SLCAN write frame (restore automatic):
frame = "T047ABFE020000\r"  # value=0
```

### CLI Usage

```bash
# Read current DHW mode
wps-cli read DHW_PROGRAM_MODE

# Disable DHW (Always Off / peak hour blocking)
wps-cli write DHW_PROGRAM_MODE off        # or: always_off, 2

# Restore automatic operation
wps-cli write DHW_PROGRAM_MODE automatic  # or: auto, 0

# Force DHW always on
wps-cli write DHW_PROGRAM_MODE on         # or: always_on, 1
```

**Named Values**: The CLI supports named values (case-insensitive):
| Name | Value | Effect |
|------|-------|--------|
| `automatic`, `auto` | 0 | Follow time program |
| `on`, `always_on` | 1 | DHW always active |
| `off`, `always_off` | 2 | No DHW heating |

## Buffer Tank Temperature Broadcasts

**Hardware Verified** (2025-12-07):

| CAN ID | Base | Index | Name | Typical Value |
|--------|------|-------|------|---------------|
| 0x08014270 | 0x0270 | 5 | GT9_TEMP (bottom/return) | 43-48°C |
| 0x08018270 | 0x0270 | 6 | GT8_TEMP (top/supply) | 46-50°C |

These temperatures are available via broadcast monitoring with the `--broadcast` flag:
```bash
wps-cli read GT8_TEMP --broadcast
wps-cli read GT9_TEMP --broadcast
```

## Related Files

- [buderus_wps/broadcast_monitor.py](../../buderus_wps/broadcast_monitor.py) - Passive monitoring implementation
- [buderus_wps/can_message.py](../../buderus_wps/can_message.py) - CAN ID constants and structure
- [buderus_wps/heat_pump.py](../../buderus_wps/heat_pump.py) - Parameter read/write implementation
- [fhem/26_KM273v018.pm](../../fhem/26_KM273v018.pm) - FHEM reference implementation

## Revision History

| Date | Change |
|------|--------|
| 2025-12-06 | Initial documentation from hardware testing |
| 2025-12-06 | Added C1 RC10 controller mappings; discovered circuit-specific broadcast patterns |
| 2025-12-06 | Verified C3 demand change capture; discovered idx=18 demand pattern on circuit bases |
| 2025-12-07 | Added buffer tank temperature mappings (GT8_TEMP, GT9_TEMP on base 0x0270) |
| 2025-12-07 | Added Parameter Write Access section with hardware-verified findings |
| 2025-12-07 | Documented XDHW_TIME/XDHW_STOP_TEMP as writable, DHW_TIMEPROGRAM as read-only |
| 2025-12-10 | Added Holiday Mode Parameters section; HOLIDAY_ACTIVE_GLOBAL (idx=901) controls Circuit 1 |
| 2025-12-10 | Discovered FHEM uses idx=901 for holiday mode, not idx=900; verified read/write working |
| 2025-12-10 | Added HEATING_SEASON_MODE as writable; verified via FHEM and heat pump menu |
| 2025-12-10 | Documented peak hour blocking use case: set HEATING_SEASON_MODE=2 to disable heating |
| 2025-12-10 | Added FHEM-Deemed Writable Parameters section: 52 parameters in 7 categories |
| 2025-12-10 | **CRITICAL FIX**: Corrected HEATING_SEASON_MODE idx from 883 to 884 (heat pump's dynamic value) |
| 2025-12-10 | Corrected value meanings: 0=Winter (forced), 1=Auto, 2=Off (was incorrectly 0=Auto) |
| 2025-12-10 | Updated parameter_data.py with hardware-verified idx values for HEATING_SEASON_* params |
| 2025-12-10 | **NEW**: DHW_PROGRAM_MODE (idx=489) verified writable for DHW blocking (0=Auto, 1=On, 2=Off) |
| 2025-12-12 | Added CLI named value support: `wps-cli write HEATING_SEASON_MODE winter/summer/automatic` |
| 2024-12-28 | **NEW**: Verified all 4 circuits broadcast room temp at idx=0 on respective circuit bases (0x0060-0x0063) |
| 2024-12-28 | Added C2 and C4 RC10 controller sections; all circuits now use consistent idx=0 for room temp, idx=33 for setpoint |
| 2024-12-28 | Updated C3 section: primary location is now idx=0/base=0x0062, alternate is idx=55/base=0x0402 for legacy |
| 2024-12-28 | Hardware verified room temperatures: C1=20.5°C, C2=22.0°C, C3=22.5°C, C4=23.9°C (C4 not on heat pump menu) |
| 2026-01-02 | **CRITICAL FIX**: GT3_TEMP (DHW) is NOT in broadcasts - must use RTR read |
| 2026-01-02 | Discovered GT3_TEMP idx mismatch: static=681 (wrong), discovered=682 (correct) |
| 2026-01-02 | Documented GT3_KORRIGERING +4.0K calibration offset causing display vs raw value difference |
| 2026-01-02 | Updated coordinator.py to read GT3_TEMP via RTR instead of broadcast |
| 2026-01-02 | Deprecated broadcast mappings for DHW in config.py and broadcast_monitor.py |
