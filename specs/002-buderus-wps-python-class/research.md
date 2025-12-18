# Research: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-12-18 (Updated for discovery protocol)
**Status**: Complete

## Overview

This document captures research decisions for implementing a Python class representing the Buderus WPS heat pump with **dynamic parameter discovery** via CAN bus protocol. This replaces the previous static approach based on investigation findings that CAN IDs are device-specific.

**Major Change from Previous Version**: Parameters are now dynamically discovered from the device using binary CAN protocol, NOT statically loaded from Perl data.

## Research Topics

### 1. CAN Bus Discovery Protocol Implementation

**Question**: How does the FHEM discovery protocol work and how do we implement it in Python?

**Decision**: Implement exact FHEM protocol using Python struct module

**Rationale**:
- FHEM reference provides complete, tested implementation
- Protocol is well-defined with fixed CAN IDs and binary structure
- Python struct module provides reliable big-endian parsing
- Can be fully tested with mock CAN adapter (no hardware needed)

**FHEM Reference Analysis** (from agent research):
- Main loop: fhem/26_KM273v018.pm:2052-2187 (`KM273_ReadElementList()`)
- Element count request: Send `R01FD7FE00` to 0x01FD7FE0, receive on 0x09FD7FE0
- Element data request: Send `T01FD3FE08` + offset + length to 0x01FD3FE0, receive on 0x09FDBFE0
- Data accumulation: CAN messages arrive in 8-byte chunks, accumulated into buffer
- Parsing starts when `readIndex >= readCounter`

**Implementation Approach**:
```python
# Discovery sequence
1. Send element count request to 0x01FD7FE0
2. Receive count from 0x09FD7FE0
3. Request data in 4096-byte chunks to 0x01FD3FE0
4. Receive data from 0x09FDBFE0 (8 bytes per CAN message)
5. Accumulate until chunk complete
6. Parse binary elements (18-byte header + variable name)
7. Repeat until all elements retrieved
```

**Retry Strategy Decision**:
- **Continuous retry with fixed timeout** (matching FHEM behavior)
- Timeout: 20 iterations per chunk request
- No exponential backoff (FHEM doesn't use it)
- Abort on malformed data, restart from beginning
- Agent finding: "Retry strategy is continuous with fixed 20-iteration timeouts, no exponential backoff"

**Element Count Edge Cases**:
- count=0: Treat as discovery failure, fall back to static data
- count>2047: Allow (no upper limit in FHEM), but log warning
- Mismatch between count and actual data: Use adaptive termination (if data length doesn't increase after retry, assume complete)

### 2. Binary Element Data Parsing

**Question**: How to parse 18-byte header + variable-length name structure reliably?

**Decision**: Use Python struct module with big-endian format

**Rationale** (from FHEM analysis):
- FHEM uses `unpack("nH14NNc", ...)` format
- All multi-byte integers are **big-endian** (network byte order)
- Proven reliable in production FHEM deployments
- Python struct provides identical functionality

**Binary Structure** (confirmed from FHEM:2135-2143):
```
Offset | Size | Field  | Format | Description
-------|------|--------|--------|---------------------------
0      | 2    | idx    | >H     | Big-endian unsigned short
2      | 7    | extid  | 7s     | 7 bytes, convert to hex string
9      | 4    | max    | >i     | Big-endian signed int (reinterpret from unsigned)
13     | 4    | min    | >i     | Big-endian signed int (reinterpret from unsigned)
17     | 1    | len    | b      | Signed byte (name length INCLUDING null)
18     | len-1| name   | (len-1)s | Name string (null terminator stripped)
```

**Python Parsing Code**:
```python
import struct

def parse_element(data: bytes, offset: int) -> tuple:
    """Parse single element from binary data.

    # PROTOCOL: Binary structure from FHEM:2135-2143
    """
    # Parse 18-byte header
    header = struct.unpack_from(">H7s4s4sb", data, offset)
    idx = header[0]
    extid = header[1].hex().upper()  # 7 bytes -> 14 hex chars
    max_unsigned = struct.unpack(">I", header[2])[0]
    min_unsigned = struct.unpack(">I", header[3])[0]
    len_field = header[4]

    # Reinterpret unsigned as signed (matching FHEM's pack/unpack trick)
    max_val = struct.unpack(">i", struct.pack(">I", max_unsigned))[0]
    min_val = struct.unpack(">i", struct.pack(">I", min_unsigned))[0]

    # Extract name (len-1 bytes, stripping null terminator)
    if len_field > 1 and len_field < 100:
        name = data[offset+18:offset+18+len_field-1].decode('latin-1')
        return (idx, extid, min_val, max_val, len_field, name)
    else:
        raise ValueError(f"Invalid len field: {len_field}")
```

**String Encoding Decision**:
- **Latin-1** (ISO-8859-1) encoding for parameter names
- Agent finding: "String encoding appears to be ASCII/Latin-1 (no explicit UTF-8 decoding in FHEM)"
- Latin-1 is compatible with ASCII but handles extended characters
- Safer than assuming pure ASCII

**Null Termination Handling**:
- Agent finding: "The name IS null-terminated in the protocol, but FHEM strips the null byte when extracting"
- `len` field includes the null terminator
- Extract `len-1` bytes for actual name string
- Decode to string using latin-1

**Malformed Element Handling**:
- Validate: `idx > previous_idx`, `1 < len < 100`, sufficient bytes remaining
- Agent finding: "When malformed elements are detected: Aborts parsing, Triggers retry, Marks discovery as incomplete"
- On validation failure: abort parsing, log error, retry from beginning
- Match FHEM's aggressive error recovery strategy

### 3. Parameter Caching Strategy

**Question**: How to implement high-performance caching that reduces discovery from ~30s to <3s?

**Decision**: JSON cache with device identifier and checksum validation

**Rationale**:
- JSON is human-readable (debugging, manual inspection)
- Fast enough for <3s load target (400-2000 parameters)
- Platform-independent (pickle is Python-specific)
- Allows schema evolution (can add fields without breaking)

**Cache Format**:
```python
{
    "version": "1.0",
    "device_id": "serial_number_or_mac",  # Unique device identifier
    "firmware_version": "detected_version",  # For invalidation on updates
    "discovery_timestamp": "2025-12-18T19:00:00Z",
    "checksum": "sha256_of_parameters",  # Integrity validation
    "parameter_count": 1789,
    "parameters": [
        {
            "idx": 0,
            "extid": "814A53C66A0802",
            "min": 0,
            "max": 100,
            "format": "int",
            "read": 0,
            "text": "PARAMETER_NAME",
            "source": "discovered"
        },
        // ... more parameters
    ]
}
```

**Cache Location Decision**:
- **User config directory**: `~/.config/buderus-wps/` (XDG standard on Linux)
- Filename: `parameter_cache_{device_id}.json`
- Alternative for Home Assistant: `/config/.storage/buderus_wps_cache/`
- Fallback: `/tmp/buderus_wps_cache/` if config dir not writable

**Cache Invalidation Triggers**:
1. **Device ID mismatch**: Different heat pump connected
2. **Checksum failure**: File corrupted
3. **Version incompatibility**: Cache format changed
4. **Firmware update detected**: Firmware version in cache != current device version
5. **Manual invalidation**: User can force re-discovery via API/CLI flag

**Device Identifier Strategy**:
- **Primary**: Serial number from CAN parameter (if available)
- **Fallback**: Hash of first 10 discovered parameter extids (unique fingerprint)
- **Last resort**: CAN adapter serial port path (least reliable, may change)

**Performance Target Validation**:
- JSON parsing 2000 parameters: ~500ms (well under 3s target)
- Cache validation (checksum): ~100ms
- Total load time budget: <3s (SC-007 requirement)

### 4. Chunk Handling and Accumulation

**Question**: How to handle partial/incomplete 4096-byte chunks and 8-byte CAN messages?

**Decision**: Accumulate 8-byte CAN messages into buffer, request chunks sequentially

**Rationale** (from FHEM analysis):
- Agent finding: "Data arrives in 8-byte CAN messages (max)"
- Agent finding: "FHEM accumulates these into readData buffer"
- CAN bus message size limited to 8 bytes
- Discovery data can be MB in size (2000 parameters × ~30 bytes = 60KB)
- Must accumulate multiple messages into chunks

**Implementation Strategy**:
```python
class DiscoveryProtocol:
    def __init__(self, can_adapter):
        self._adapter = can_adapter
        self._buffer = bytearray()
        self._expected_count = 0

    def request_chunk(self, offset: int, length: int = 4096):
        """Request 4096-byte chunk from device.

        # PROTOCOL: Data buffer read request (FHEM:2086-2092)
        """
        # Send T01FD3FE08 + offset + length to 0x01FD3FE0
        # Format: T01FD3FE0 + 1byte offset_high + 1byte offset_low + 1byte len_high + 1byte len_low
        msg = f"T01FD3FE0{offset>>8:02X}{offset&0xFF:02X}{length>>8:02X}{length&0xFF:02X}"
        self._adapter.send(msg)

    def accumulate_responses(self, timeout: float = 5.0):
        """Accumulate 8-byte CAN responses into buffer.

        # PROTOCOL: Response accumulation (FHEM:2108-2115)
        """
        start = time.time()
        while time.time() - start < timeout:
            response = self._adapter.receive(can_id=0x09FDBFE0)
            if response:
                # Extract data bytes (up to 8 bytes per message)
                data_bytes = response.data  # bytearray of 1-8 bytes
                self._buffer.extend(data_bytes)

                # Check if we have complete chunk
                if len(self._buffer) >= 4096:
                    return True

        return len(self._buffer) > 0  # Partial data is OK on last chunk
```

**Short CAN Message Handling**:
- Agent finding: "Short CAN messages (< 8 bytes) are left-shifted before packing to maintain alignment"
- Python approach: CAN adapter handles message alignment
- We receive complete data bytes, no manual shifting needed

**Partial Chunk Handling**:
- Last chunk may be < 4096 bytes (end of element data)
- Parse what we have, check if more elements expected
- Agent finding: "Partial chunks are handled gracefully - FHEM waits for more data until readIndex >= writeIndex"

### 5. Fallback Data Structure (EXISTING - PRESERVED)

**Decision**: Preserve existing research decision on @KM273_elements_default conversion

**From Previous Research**:
- Manual Perl-to-Python conversion (one-time)
- Store as `parameter_data.py` Python module
- Contract test verifies fidelity
- Used ONLY when discovery fails (FR-006)

**No changes needed** - this fallback mechanism remains valid for discovery failure scenarios

### 6. Parameter Class Design (UPDATED)

**Decision**: Extend existing dataclass design with CAN ID calculation and source tracking

**Updates**:
```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Parameter:
    """Represents a discovered or fallback heat pump parameter.

    # PROTOCOL: Maps to binary element structure (FHEM:2135-2143)
    # or KM273_elements_default array (FHEM:218+) for fallback
    """
    idx: int              # Parameter index (used for CAN ID calculation)
    extid: str            # External ID (7-byte hex string, 14 chars)
    min: int              # Minimum allowed value (signed int)
    max: int              # Maximum allowed value (signed int)
    format: str           # Data format (int, temp, etc.)
    read: int             # Read-only flag (0=writable, 1=read-only)
    text: str             # Human-readable parameter name
    source: Literal["discovered", "fallback"] = "discovered"  # Track origin

    def is_writable(self) -> bool:
        """Check if parameter is writable."""
        return self.read == 0

    def validate_value(self, value: int) -> bool:
        """Validate if value is within allowed range."""
        return self.min <= value <= self.max

    def get_read_can_id(self) -> int:
        """Calculate CAN ID for read request.

        # PROTOCOL: Formula from FHEM:2229
        rtr = 0x04003FE0 | (idx << 14)
        """
        return 0x04003FE0 | (self.idx << 14)

    def get_write_can_id(self) -> int:
        """Calculate CAN ID for write request.

        # PROTOCOL: Formula from FHEM:2230
        txd = 0x0C003FE0 | (idx << 14)
        """
        return 0x0C003FE0 | (self.idx << 14)
```

**Type Safety**:
- Use `Literal["discovered", "fallback"]` for source tracking
- Prevents typos, enables IDE autocomplete
- Useful for debugging and logging

### 7. Lookup Mechanism (EXISTING - PRESERVED)

**Decision**: Preserve dual-dict design (by idx, by name) - O(1) lookup for both

**No changes needed** - existing design supports both discovered and fallback parameters

```python
class ParameterRegistry:
    """Container for all heat pump parameters with lookup methods."""

    def __init__(self):
        self._params_by_idx: dict[int, Parameter] = {}
        self._params_by_name: dict[str, Parameter] = {}
        self._cache_manager = ParameterCache()

    def discover_parameters(self, can_adapter) -> None:
        """Run discovery protocol or load from cache."""
        # Try cache first
        if cached_params := self._cache_manager.load():
            self._populate(cached_params)
            return

        # Run discovery
        discovered = DiscoveryProtocol(can_adapter).run()
        self._populate(discovered)
        self._cache_manager.save(discovered)

    def _populate(self, parameters: list[Parameter]) -> None:
        """Populate lookup dicts."""
        for param in parameters:
            self._params_by_idx[param.idx] = param
            self._params_by_name[param.text] = param
```

### 8. Testing Strategy (UPDATED FOR DISCOVERY)

**Decision**: Four-layer test strategy with comprehensive mocking

**Test Layers**:

**1. Unit Tests** - Test individual components in isolation:
- `test_binary_parser.py`: Binary element parsing with known vectors
  - Valid elements (various idx, extid, min/max combinations)
  - Edge cases (min=max, negative values, len=2, len=99)
  - Invalid elements (len=0, len=100, len>remaining data, idx not increasing)

- `test_parameter.py`: Parameter class methods
  - is_writable() logic
  - validate_value() with various ranges
  - get_read_can_id() / get_write_can_id() formulas

- `test_parameter_cache.py`: Cache persistence
  - Save/load roundtrip
  - Checksum validation
  - Device ID matching
  - Invalid JSON handling

**2. Integration Tests** - Test component interactions with mocks:
- `test_discovery_sequence.py`: Full discovery with mock CAN adapter
  - Mock adapter returns element count on 0x09FD7FE0
  - Mock adapter returns 8-byte chunks on 0x09FDBFE0
  - Verify correct sequence: count request → data requests → parsing
  - Test timeout handling and retries

- `test_cache_roundtrip.py`: Discovery → cache → load
  - Run discovery (with mocks)
  - Save to cache
  - Load from cache on next connection
  - Verify parameters identical

**3. Contract Tests** - Verify protocol correctness:
- `test_protocol_fidelity.py`: Binary structure matches FHEM
  - Parse known-good element data from FHEM
  - Verify idx, extid, min, max, len, name extracted correctly
  - Compare against expected values

- `test_can_id_construction.py`: CAN ID formulas correct
  - Test vectors: idx=0→0x04003FE0, idx=1→0x04007FE0, idx=100→0x04193FE0
  - Verify read and write IDs for known idx values

- `test_fallback_fidelity.py`: Fallback data matches Perl
  - Parse @KM273_elements_default from FHEM file
  - Compare count and spot-check parameters
  - Verify all indices present

**4. Acceptance Tests** - Verify user scenarios from spec:
- All 23 acceptance scenarios from spec.md
- User Story 0 (P0): Discovery protocol (5 scenarios)
- User Story 1 (P1): Parameter reading (5 scenarios)
- User Story 2 (P2): Validation (5 scenarios)
- User Story 3 (P3): Access methods (4 scenarios)
- User Story 4 (P2): Caching (4 scenarios)

**Mock CAN Adapter**:
```python
class MockCANAdapter:
    """Mock CAN adapter for testing without hardware."""

    def __init__(self, test_data: dict):
        self._responses = test_data  # Pre-programmed responses
        self._sent_messages = []

    def send(self, message: str):
        """Record sent message."""
        self._sent_messages.append(message)

    def receive(self, can_id: int, timeout: float = 1.0) -> CANMessage:
        """Return pre-programmed response for CAN ID."""
        return self._responses.get(can_id, None)
```

**Coverage Target**: 100% of described functionality per Principle IV

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| Discovery Protocol | Exact FHEM implementation | Proven reliable, well-documented, testable with mocks |
| Binary Parsing | Python struct with big-endian | Matches FHEM unpack format, reliable |
| String Encoding | Latin-1 | FHEM behavior, handles extended ASCII |
| Retry Strategy | Continuous with fixed timeout | Matches FHEM (20 iterations), reliable |
| Cache Format | JSON with checksums | Human-readable, platform-independent, <3s load time |
| Cache Location | `~/.config/buderus-wps/` | XDG standard, user-writable |
| Device Identifier | Serial number or extid hash | Unique, stable across reboots |
| Chunk Handling | Accumulate 8-byte CAN messages | Matches FHEM, handles partial chunks |
| Fallback Data | Preserve Perl conversion | Still valid for discovery failures |
| Parameter Class | Dataclass with CAN ID methods | Type safe, immutable, protocol fidelity |
| Lookup Mechanism | Dual dict (preserved) | O(1) for both name and index lookup |
| Testing | Four-layer with mocks | 100% coverage without hardware |

## Next Steps

**Phase 0 Complete** ✅ - All NEEDS CLARIFICATION items resolved

Proceed to Phase 1:
1. Generate data-model.md with updated entities:
   - Parameter (with CAN ID methods)
   - DiscoveredElement (binary parsing intermediate)
   - ParameterCache (persistence format)
   - ParameterRegistry (lookup + cache management)

2. Update quickstart.md with discovery flow examples:
   - First connection (discovery)
   - Subsequent connections (cached)
   - Fallback scenario (discovery fails)
   - Parameter lookup and CAN ID calculation

3. No contracts/ needed (library-only feature, no API)
