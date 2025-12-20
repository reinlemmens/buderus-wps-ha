# Buderus WPS CAN Bus Protocol Documentation

This document describes the CAN bus protocol used by Buderus WPS heat pumps,
as implemented in this Python library. The protocol is derived from the FHEM
Perl reference implementation (`fhem/26_KM273v018.pm`).

## CAN Bus Configuration

- **Baud Rate**: 125 kbit/s
- **Frame Format**: Extended CAN (29-bit identifiers)
- **Byte Order**: Big-endian (network byte order)

## CAN ID Formulas

All parameter access uses dynamic CAN IDs calculated from the parameter index:

### Read Request (RTR)
```python
CAN_ID_READ = 0x04003FE0 | (idx << 14)
```
- Send as RTR (Remote Transmission Request) frame
- Data length: 0 bytes
- Device responds on write CAN ID with current value

### Write Request / Response
```python
CAN_ID_WRITE = 0x0C003FE0 | (idx << 14)
```
- Write: Send as data frame with encoded value (typically 2 bytes)
- Response: Received on this ID after RTR request

### Example: ACCESS_LEVEL (idx=1)
```
Read:  0x04003FE0 | (1 << 14) = 0x04007FE0
Write: 0x0C003FE0 | (1 << 14) = 0x0C007FE0
```

## Format Types

The protocol uses 13 format types for encoding/decoding values:

| Format | Factor | Unit | Description |
|--------|--------|------|-------------|
| `int` | 1 | - | Raw integer, no scaling |
| `tem` | 0.1 | °C | Temperature (2 bytes, signed) |
| `pw2` | 0.01 | kW | Power, 2 decimal places |
| `pw3` | 0.001 | kW | Power, 3 decimal places |
| `hm1` | 1 | s | Time in seconds → HH:MM |
| `hm2` | 10 | s | Time in 10-second intervals → HH:MM |
| `t15` | - | - | 15-minute intervals (special encoding) |
| `sw1` | 1 | - | Timer switch bit field 1 |
| `sw2` | 1 | - | Timer switch bit field 2 |
| `rp1` | 1 | - | Room program selector |
| `rp2` | 1 | - | Room program mode |
| `dp1` | 1 | - | DHW program selector |
| `dp2` | 1 | - | DHW program mode |

### Encoding (Human-Readable to Raw)

FHEM uses this formula to convert user values to raw CAN values:
```perl
$value1 = int($value / $factor + 0.5);
```

Example for temperature:
- User enters: 53.0°C
- Factor: 0.1
- Raw: int(53.0 / 0.1 + 0.5) = 530

### Decoding (Raw to Human-Readable)

```perl
$value = $raw * $factor;
```

Example:
- Raw: 530
- Factor: 0.1
- Result: 53.0°C

## Special Format Encodings

### t15 Format (15-Minute Intervals)

Used for timer schedules. Encodes time as:
- Bits 0-1: Quarter (0=:00, 1=:15, 2=:30, 3=:45)
- Bits 2+: Hour (0-23)

```python
# Encode: "07:30" -> 30
hour = 7
quarter = 2  # 30 minutes / 15
raw = (hour << 2) | quarter  # = 30

# Decode: 30 -> "07:30"
quarter = raw & 0x03  # = 2
hour = raw >> 2       # = 7
time = f"{hour:02d}:{quarter * 15:02d}"  # = "07:30"
```

### hm1/hm2 Formats (Time Duration)

- `hm1`: Value in seconds
- `hm2`: Value in 10-second intervals

Displayed as HH:MM:
```python
# hm1: 3660 seconds -> "1:01"
total_seconds = 3660 * factor  # factor=1 for hm1
hours = total_seconds // 3600   # = 1
minutes = (total_seconds % 3600) // 60  # = 1

# hm2: 120 (10s intervals) -> "0:20"
total_seconds = 120 * 10  # factor=10 for hm2
# = 1200 seconds = 0 hours, 20 minutes
```

### Select Formats (rp1, rp2, dp1, dp2)

Enumeration values with string labels:

```python
# rp1 - Room Program
0: HP_Optimized
1: Program_1
2: Program_2
3: Family
4: Morning
5: Evening
6: Seniors

# rp2 - Room Mode
0: Automatic
1: Normal
2: Exception
3: HeatingOff

# dp1 - DHW Program
0: Always_On
1: Program_1
2: Program_2

# dp2 - DHW Mode
0: Automatic
1: Always_On
2: Always_Off
```

## DEAD Sensor Value

Disconnected temperature sensors return the special value `0xDEAD`:
- Raw: 0xDEAD (57005 unsigned, -8531 signed)
- As signed 16-bit: -8531

When this value is detected, the sensor reading should be treated as unavailable.

## Discovery Protocol

The heat pump supports dynamic parameter discovery via dedicated CAN IDs:

| Purpose | CAN ID | Direction |
|---------|--------|-----------|
| Request element count | 0x01FD7FE0 | Send RTR |
| Receive element count | 0x09FD7FE0 | Receive |
| Request element data | 0x01FD3FE0 | Send data |
| Request buffer read | 0x01FDBFE0 | Send RTR |
| Receive element data | 0x09FDBFE0 | Receive |

### Discovery Sequence

1. Send RTR to `0x01FD7FE0` to request element count
2. Receive total bytes on `0x09FD7FE0` (4 bytes, big-endian)
3. For each 4096-byte chunk:
   a. Send data request to `0x01FD3FE0` with length (4B) + offset (4B)
   b. Send RTR to `0x01FDBFE0` to trigger data stream
   c. Receive data frames on `0x09FDBFE0` (8 bytes each)
4. Parse binary element data

### Element Binary Format

Each element is encoded as:
```
Offset  Size  Type        Description
0       2     uint16_be   idx (parameter index)
2       7     bytes       extid (external ID, hex string)
9       4     uint32_be   max (convert to signed)
13      4     uint32_be   min (convert to signed)
17      1     int8        name_len (including null terminator)
18      N     ascii       name (name_len - 1 bytes, null-terminated)
```

## Broadcast Traffic

The heat pump broadcasts some sensor readings periodically. These can be
passively monitored without sending requests:

### Temperature Broadcasts

Temperature readings use base + offset encoding:
```python
CAN_ID = (base << 11) | (offset & 0x7FF)
```

Where:
- `base`: Parameter base (e.g., 0x3A = outdoor temp)
- `offset`: Specific sensor index

Common temperature bases:
- 0x3A: Outdoor temperature
- 0x62: Supply temperature
- 0x63: Return temperature
- 0xA5: DHW temperature
- 0xD8: Brine inlet temperature

## Implementation Notes

1. **Byte Order**: All multi-byte values use big-endian (network byte order)

2. **Signedness**: Determined by parameter min value:
   - min < 0: Signed interpretation
   - min >= 0: Unsigned interpretation

3. **Write Size**: FHEM always uses 2 bytes for writes (line 2746)

4. **RTR Frames**: Read requests must be sent as RTR (Remote Transmission Request)

5. **Extended IDs**: All CAN IDs are 29-bit extended identifiers

## References

- FHEM KM273 module: `fhem/26_KM273v018.pm`
- SLCAN protocol: Lawicel CAN-USB adapter specification
- CAN 2.0B specification for extended identifiers
