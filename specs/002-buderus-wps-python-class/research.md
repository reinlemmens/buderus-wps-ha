# Research: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-12-18 (Updated)
**Status**: Complete

## Overview

This document captures research decisions for implementing a Python class representing the Buderus WPS heat pump with dynamic parameter discovery. The critical insight is that CAN IDs are NOT static - they must be dynamically constructed from parameter indices discovered from the device.

## Research Topics

### 1. CAN ID Discovery Protocol (NEW - Critical Finding)

**Question**: How does FHEM discover CAN IDs for parameter access?

**Decision**: Implement dynamic discovery protocol from FHEM

**Rationale**:
- FHEM investigation revealed CAN IDs are calculated at runtime, not hardcoded
- The @KM273_elements_default array is fallback only, not primary source
- Without discovery, parameter read/write operations cannot succeed

**FHEM Protocol Analysis** (Source: `fhem/26_KM273v018.pm`):

1. **Fixed Discovery CAN IDs** (lines 2052-2187):
   | Purpose | Send CAN ID | Receive CAN ID |
   |---------|-------------|----------------|
   | Element count | 0x01FD7FE0 | 0x09FD7FE0 |
   | Element data | 0x01FD3FE0 | 0x09FDBFE0 |
   | Data buffer read | 0x01FDBFE0 | - |

2. **CAN ID Construction Formulas** (lines 2229-2230):
   ```python
   rtr = 0x04003FE0 | (idx << 14)  # Read request
   txd = 0x0C003FE0 | (idx << 14)  # Response/Write
   ```

3. **Discovery Sequence**:
   - Send R01FD7FE00 → Receive element count on 0x09FD7FE0
   - Send T01FD3FE08 + offset + length → Receive data on 0x09FDBFE0
   - Parse binary data in 4096-byte chunks

**Alternatives Considered**:
1. **Hardcoded CAN IDs from @KM273_elements_default** - Rejected because:
   - `extid` field is NOT the CAN ID used for communication
   - CAN IDs must be calculated from `idx` using formulas
   - Would not match actual device protocol

### 2. Binary Element Data Structure (NEW)

**Question**: How is element data encoded in the discovery response?

**Decision**: Parse binary structure as documented in FHEM (lines 2135-2143)

**Binary Element Structure**:
```
Offset  Size  Field    Type             Notes
0       2     idx      uint16 LE        Parameter index
2       7     extid    hex string       External ID (14 hex chars)
9       4     max      int32 LE         Maximum value
13      4     min      int32 LE         Minimum value
17      1     len      uint8            Name length
18      N     name     ASCII string     Parameter name (len-1 bytes, null-terminated)
```

**Implementation Approach**:
```python
import struct

def parse_element(data: bytes, offset: int) -> tuple[dict, int]:
    """Parse single element from binary data.

    Returns (element_dict, next_offset) or (None, -1) on error.
    """
    # Parse fixed header (18 bytes)
    idx = struct.unpack_from('<H', data, offset)[0]        # uint16 LE
    extid = data[offset+2:offset+9].hex().upper()          # 7 bytes → 14 hex chars
    max_val = struct.unpack_from('<i', data, offset+9)[0]  # int32 LE
    min_val = struct.unpack_from('<i', data, offset+13)[0] # int32 LE
    name_len = data[offset+17]

    # Parse variable-length name
    name = data[offset+18:offset+18+name_len-1].decode('ascii', errors='replace')

    element = {
        'idx': idx, 'extid': extid, 'max': max_val,
        'min': min_val, 'format': 'int', 'read': 0, 'text': name.rstrip('\x00')
    }

    return element, offset + 18 + name_len
```

**Rationale**:
- Uses Python stdlib only (struct module)
- Little-endian matches FHEM implementation
- Error handling for malformed data

### 3. Discovery Protocol Implementation

**Question**: How to implement the full discovery sequence?

**Decision**: State machine with timeout handling

**Discovery Flow**:
```
START
  ↓
Request element count (0x01FD7FE0)
  ↓
Wait for count response (0x09FD7FE0, timeout 5s)
  ↓
For offset in range(0, total_bytes, 4096):
  ├── Request chunk (0x01FD3FE0 + offset + 4096)
  ├── Wait for data response (0x09FDBFE0, timeout 10s per chunk)
  └── Parse elements from chunk
  ↓
Build parameter index
  ↓
COMPLETE (or FALLBACK on any error)
```

**Implementation Approach**:
```python
class ParameterDiscovery:
    """Discovers parameters from Buderus WPS heat pump via CAN bus."""

    ELEMENT_COUNT_SEND = 0x01FD7FE0
    ELEMENT_COUNT_RECV = 0x09FD7FE0
    ELEMENT_DATA_SEND = 0x01FD3FE0
    ELEMENT_DATA_RECV = 0x09FDBFE0
    CHUNK_SIZE = 4096
    TIMEOUT_COUNT = 5.0
    TIMEOUT_CHUNK = 10.0

    def __init__(self, adapter: CANAdapter):
        self._adapter = adapter

    async def discover(self) -> list[dict]:
        """Discover all parameters from device.

        Returns list of parameter dicts or raises DiscoveryError.
        """
        count = await self._request_element_count()
        elements = []

        for offset in range(0, count * AVG_ELEMENT_SIZE, self.CHUNK_SIZE):
            chunk = await self._request_element_chunk(offset, self.CHUNK_SIZE)
            elements.extend(self._parse_chunk(chunk))

        return elements
```

**Rationale**:
- Async I/O for non-blocking operation (Home Assistant compatibility)
- Configurable timeouts for slow devices
- Clear error states for fallback triggering

### 4. Caching Strategy (NEW)

**Question**: How to avoid 30s discovery on every connection?

**Decision**: JSON file cache with validation

**Cache Structure**:
```json
{
  "version": "1.0.0",
  "created": "2025-12-18T10:30:00Z",
  "device_id": "BUDERUS_WPS_SN12345",
  "firmware": "v1.23",
  "checksum": "sha256:abc123...",
  "element_count": 1789,
  "parameters": [
    {"idx": 0, "extid": "814A53C66A0802", ...},
    ...
  ]
}
```

**Cache Validation**:
1. File exists and is valid JSON
2. Version matches current library version
3. Checksum validates data integrity
4. Device ID matches connected device (if identifiable)

**Invalidation Triggers**:
- Checksum mismatch
- Version mismatch
- Firmware version change (if detectable)
- Manual bypass (`force_discovery=True`)

**Rationale**:
- JSON is human-readable for debugging
- No external dependencies (stdlib json module)
- Checksum prevents corruption issues
- Device ID prevents cross-device cache misuse

**Alternatives Considered**:
1. **Pickle** - Rejected because:
   - Security concerns with untrusted data
   - Not human-readable
   - Python version dependent

2. **SQLite** - Rejected because:
   - Overkill for simple list storage
   - Adds complexity
   - File-based JSON is simpler

3. **No caching** - Rejected because:
   - 30s discovery on every connection is unacceptable UX
   - Unnecessary load on heat pump controller

### 5. Fallback Strategy

**Question**: What happens when discovery fails?

**Decision**: Three-tier fallback with user notification

**Fallback Order**:
1. **Cache**: Load from cached discovery (fastest, ~1s)
2. **Discovery**: Run discovery protocol (slow, ~30s)
3. **Static Data**: Use @KM273_elements_default (always available)

**Implementation**:
```python
class HeatPump:
    def __init__(self, adapter: CANAdapter = None, cache_path: Path = None):
        self._parameters = None
        self._source = None  # 'cache', 'discovery', 'fallback'

        if cache_path and self._load_cache(cache_path):
            self._source = 'cache'
        elif adapter and self._run_discovery(adapter):
            self._source = 'discovery'
            self._save_cache(cache_path)
        else:
            self._load_fallback()
            self._source = 'fallback'

    @property
    def using_fallback(self) -> bool:
        """True if operating with static fallback data."""
        return self._source == 'fallback'
```

**Rationale**:
- User can check `using_fallback` to know data quality
- Logging indicates which source was used
- Static fallback ensures library always works

### 6. Perl Data Structure Parsing Strategy (Original)

**Question**: How should we extract and convert the KM273_elements_default array from Perl to Python?

**Decision**: Manual one-time conversion with automated verification

**Rationale**:
- The FHEM Perl file contains a static array that rarely changes
- Perl parsing in Python adds unnecessary runtime dependency
- Manual conversion is more reliable and maintainable
- We can create a verification script to check fidelity after conversion

**Status**: COMPLETE - 1789 parameters extracted and verified

### 7. Python Data Structure Design (Original)

**Question**: What Python data structure should represent individual parameters and the parameter collection?

**Decision**: Use `dataclass` for Parameter, dict+list for lookup

**Parameter Class Design** (EXTENDED for CAN IDs):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Parameter:
    """Represents a single Buderus WPS heat pump parameter.

    # PROTOCOL: Maps to KM273_elements_default array in fhem/26_KM273v018.pm
    # PROTOCOL: CAN ID formulas from fhem/26_KM273v018.pm:2229-2230
    """
    idx: int
    extid: str
    min: int
    max: int
    format: str
    read: int
    text: str

    def get_read_can_id(self) -> int:
        """Calculate CAN ID for read request.

        Formula: rtr = 0x04003FE0 | (idx << 14)
        """
        return 0x04003FE0 | (self.idx << 14)

    def get_write_can_id(self) -> int:
        """Calculate CAN ID for write/response.

        Formula: txd = 0x0C003FE0 | (idx << 14)
        """
        return 0x0C003FE0 | (self.idx << 14)

    def is_writable(self) -> bool:
        return self.read == 0

    def validate_value(self, value: int) -> bool:
        return self.min <= value <= self.max
```

**Status**: COMPLETE - Parameter class exists, needs CAN ID methods added

### 8. Lookup Mechanism Design (Original)

**Question**: How to efficiently support lookup by both index and name?

**Decision**: Dual-index approach with dict for names, dict for indices

**Status**: COMPLETE - HeatPump class implemented with O(1) lookup

### 9. Test Strategy (Extended)

**Question**: How to ensure comprehensive test coverage per Principle IV?

**Decision**: Extended four-layer test strategy

**Additional Test Layers for Discovery**:

1. **Unit Tests** - `tests/unit/test_can_ids.py`
   - CAN ID formula correctness
   - Edge cases (idx=0, max idx)
   - Verify against FHEM reference values

2. **Unit Tests** - `tests/unit/test_discovery.py`
   - Binary element parsing
   - Chunk boundary handling
   - Timeout handling

3. **Unit Tests** - `tests/unit/test_cache.py`
   - JSON serialization/deserialization
   - Checksum validation
   - Cache invalidation

4. **Contract Tests** - `tests/contract/test_can_id_formulas.py`
   - CRITICAL: Verify formulas match FHEM exactly
   - Test known idx → CAN ID pairs

5. **Contract Tests** - `tests/contract/test_binary_parsing.py`
   - Verify parsing against known binary data
   - Test with malformed data

6. **Integration Tests** - `tests/integration/test_discovery_flow.py`
   - Full discovery sequence with mock adapter
   - Fallback triggering on error

7. **Acceptance Tests** - `tests/acceptance/test_acceptance_us0.py`
   - User Story 0 acceptance scenarios
   - Discovery timeout handling
   - Fallback verification

8. **Acceptance Tests** - `tests/acceptance/test_acceptance_us4.py`
   - User Story 4 acceptance scenarios
   - Cache creation/loading
   - Cache invalidation

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| CAN ID Discovery | Dynamic protocol from FHEM | IDs calculated at runtime, not static |
| Binary Parsing | struct module, LE integers | Matches FHEM, stdlib only |
| Discovery Impl | Async state machine | Non-blocking, HA compatible |
| Caching | JSON file with checksum | Human-readable, no dependencies |
| Fallback | Three-tier (cache → discovery → static) | Always functional |
| Perl Parsing | Manual + verification | COMPLETE |
| Data Structure | dataclass + dual dict | COMPLETE |
| CAN ID Methods | Add to Parameter class | New requirement |

## Next Steps

Proceed to Phase 1:
1. Update data-model.md with discovery entities
2. Create quickstart.md with discovery examples
3. Generate tasks.md for implementation breakdown
