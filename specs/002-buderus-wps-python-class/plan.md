# Implementation Plan: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Branch**: `002-buderus-wps-python-class` | **Date**: 2025-12-18 (Updated) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-buderus-wps-python-class/spec.md`

## Summary

Create a Python class that represents the Buderus WPS heat pump with **dynamic parameter discovery** via CAN bus protocol. The system discovers parameter definitions from the device at runtime (idx, extid, min, max, format, read flag, text) using a binary protocol, caches them for performance, and falls back to @KM273_elements_default when discovery fails. The class supports lookup by both index and name with value validation and dynamic CAN ID construction.

**Critical Change from Previous Plan**: Parameters are now **dynamically discovered** from the device, NOT statically loaded from Perl data. This is a P0 requirement based on FHEM investigation revealing CAN IDs are device-specific.

**Technical Approach**:
1. Implement CAN bus discovery protocol (element count request, element data retrieval in 4096-byte chunks)
2. Parse binary element data (18-byte header + variable-length name per element)
3. Cache discovered parameters to persistent storage for performance (90% time reduction)
4. Calculate CAN IDs dynamically: `rtr = 0x04003FE0 | (idx << 14)`, `txd = 0x0C003FE0 | (idx << 14)`
5. Fall back to @KM273_elements_default only when discovery fails
6. Preserve existing good design: dataclass for Parameter, dual-dict lookup, validation methods

## Technical Context

**Language/Version**: Python 3.9+ (per constitution for Home Assistant compatibility)
**Primary Dependencies**:
- Python standard library (typing, dataclasses, struct for binary parsing)
- CAN adapter layer (USBtin or socketcand - provided by existing infrastructure)
- Persistent storage (filesystem for cache - JSON or pickle)

**Storage**:
- **Primary**: Discovered parameters cached to persistent storage (JSON/pickle file)
- **Fallback**: Static data from @KM273_elements_default (embedded Python module)

**Testing**: pytest with coverage reporting (unit, integration, contract, acceptance)
**Target Platform**: Linux on Raspberry Pi (primary), cross-platform compatible
**Project Type**: Single project (core library)

**Performance Goals**:
- Discovery: <30 seconds for 400-2000 parameters (SC-001)
- Cached loading: <3 seconds (SC-007 - 90% improvement over discovery)
- Parameter lookup: <1 second both by name and index (SC-003, SC-004)

**Constraints**:
- MUST implement discovery protocol before any parameter access (FR-001)
- MUST NOT use hardcoded CAN IDs except fixed discovery IDs (FR-010)
- MUST preserve exact protocol structure from FHEM reference (Principle II)
- Discovery MUST work without physical hardware (mocks for testing)

**Scale/Scope**: 400-2000 parameters (device-dependent), lightweight caching, binary protocol parsing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Library-First Architecture
**Status**: ✅ PASS
**Rationale**: This feature creates part of the core library (`buderus_wps`). The parameter class, discovery protocol, and caching will be independently usable, fully tested, and documented as required. Separation of concerns: discovery layer, parameter registry, cache manager.

### Principle II: Hardware Abstraction & Protocol Fidelity
**Status**: ✅ PASS
**Rationale**:
- Discovery protocol exactly matches FHEM reference implementation (fhem/26_KM273v018.pm:2052-2187)
- Binary element structure: idx (2 bytes), extid (7 bytes), max (4 bytes), min (4 bytes), len (1 byte), name (len-1 bytes) - per FHEM:2135-2143
- CAN ID construction: `rtr = 0x04003FE0 | (idx << 14)` and `txd = 0x0C003FE0 | (idx << 14)` - per FHEM:2229-2230
- Fixed discovery CAN IDs preserved: 0x01FD7FE0, 0x09FD7FE0, 0x01FD3FE0, 0x09FDBFE0, 0x01FDBFE0
- All protocol-critical code will have `# PROTOCOL:` tags with FHEM line number references

### Principle III: Safety & Reliability
**Status**: ✅ PASS
**Rationale**:
- Parameter validation using discovered min/max constraints (FR-015)
- Fallback to @KM273_elements_default when discovery fails (FR-006)
- Cache validation before use (checksum, device identifier match) (FR-021)
- Cache invalidation on corruption or firmware mismatch (FR-022)
- Timeout and retry logic for discovery protocol
- Read-only flag enforcement prevents accidental writes (FR-018)

### Principle IV: Comprehensive Test Coverage
**Status**: ✅ PASS
**Rationale**: Feature spec includes 5 user stories with 23 acceptance scenarios plus 10 edge cases. Test plan will include:
- **Unit tests**: Binary parser, Parameter class, CAN ID calculation, cache validation
- **Integration tests**: Full discovery sequence with mocked CAN responses, cache roundtrip
- **Contract tests**: Binary structure matches FHEM, CAN IDs match formula, fallback data fidelity
- **Acceptance tests**: All 23 scenarios from spec.md (P0-P3 user stories)
- **Mocking strategy**: Mock CAN adapter to simulate discovery protocol without hardware

### Principle V: Protocol Documentation & Traceability
**Status**: ✅ PASS
**Rationale**:
- Code will cross-reference FHEM implementation with line numbers
- Discovery protocol fully documented with binary structure diagrams
- `# PROTOCOL:` tags for all CAN-related code
- Cache format documented for future compatibility
- Data flow diagrams for discovery → cache → fallback sequence

### All Other Principles
**Status**: ✅ PASS
**Rationale**: Principles VI (Home Assistant) and VII (CLI) not directly applicable to this library-only feature. Technical standards (Python 3.9+, pytest, type hints, docstrings) will be followed.

## Project Structure

### Documentation (this feature)

```
specs/002-buderus-wps-python-class/
├── plan.md              # This file (UPDATED for discovery protocol)
├── research.md          # Phase 0: Discovery protocol analysis, binary parsing, caching strategy (TO UPDATE)
├── data-model.md        # Phase 1: Parameter, DiscoveredElement, Cache entities (TO UPDATE)
├── quickstart.md        # Phase 1: Usage examples with discovery flow (TO UPDATE)
└── tasks.md             # Phase 2: Implementation task breakdown (TO REGENERATE)
```

### Source Code (repository root)

```
buderus_wps/              # Core library package (existing)
├── __init__.py
├── can_adapter.py        # Existing: CAN communication (will use for discovery)
├── can_message.py        # Existing: Message encoding/decoding
├── exceptions.py         # Existing: Exception types (add DiscoveryError)
├── element_discovery.py  # NEW: CAN bus discovery protocol implementation
├── parameter.py          # UPDATED: Parameter class + fallback data
├── parameter_data.py     # UPDATED: @KM273_elements_default fallback (from Perl)
├── parameter_registry.py # NEW: Parameter lookup + cache management
└── parameter_cache.py    # NEW: Cache persistence (JSON/pickle)

fhem/                     # Reference implementation (existing, READ-ONLY)
└── 26_KM273v018.pm       # Discovery protocol reference (lines 2052-2187, 2229-2230, 2135-2143)

tests/
├── unit/
│   ├── test_element_discovery.py     # NEW: Unit tests for discovery protocol
│   ├── test_binary_parser.py         # NEW: Binary element parsing tests
│   ├── test_parameter.py              # UPDATED: Parameter class tests
│   ├── test_parameter_registry.py    # NEW: Registry + lookup tests
│   └── test_parameter_cache.py       # NEW: Cache persistence tests
├── integration/
│   ├── test_discovery_sequence.py    # NEW: Full discovery with mocks
│   ├── test_cache_roundtrip.py       # NEW: Discovery → cache → load
│   └── test_parameter_validation.py  # EXISTING: Validation tests
└── contract/
    ├── test_protocol_fidelity.py     # NEW: Binary structure matches FHEM
    ├── test_can_id_construction.py   # NEW: CAN ID formulas correct
    └── test_fallback_fidelity.py     # EXISTING: Fallback data matches Perl
```

**Structure Decision**: Single project structure using existing `buderus_wps/` package. New discovery-related modules added: `element_discovery.py` (protocol implementation), `parameter_registry.py` (lookup + cache), `parameter_cache.py` (persistence). Updated `parameter.py` to support both discovered and fallback parameters.

## Complexity Tracking

### Justified Additional Complexity (vs. Previous Plan)

**Previous Plan**: Static parameters loaded from Perl data
**New Plan**: Dynamic discovery + caching + fallback

**Justification**: Investigation of FHEM revealed CAN IDs are NOT static - they are calculated from device-specific idx values. Using hardcoded IDs would result in incorrect/incompatible parameter access. Discovery protocol is mandatory for correct operation.

**Complexity Added**:
1. **CAN bus discovery protocol** (FR-001 to FR-007) - REQUIRED for correct operation
2. **Binary element parsing** (FR-004) - REQUIRED by protocol specification
3. **Parameter caching** (FR-019 to FR-023) - OPTIONAL but high-value (90% performance gain)
4. **Dynamic CAN ID construction** (FR-008 to FR-010) - REQUIRED (replaces incorrect hardcoded IDs)

**Mitigation**:
- Mock CAN adapter for testing without hardware
- Comprehensive contract tests verify protocol correctness
- Fallback to static data when discovery unavailable (degraded but functional)
- Cache reduces complexity burden in production (discovery runs once, cached thereafter)

## Phase 0: Research & Analysis

**Status**: TO UPDATE (existing research.md predates discovery protocol investigation)

**Research Topics**:

### 1. CAN Bus Discovery Protocol Analysis *(NEW)*

**Question**: How does the FHEM discovery protocol work and how do we implement it in Python?

**NEEDS CLARIFICATION**:
- Binary data parsing library: struct module vs. custom parser
- Discovery retry strategy: how many retries, backoff timing
- Element count edge cases: what if count=0, count>2047, count doesn't match actual data
- Partial chunk handling: what if 4096-byte chunk is incomplete

**FHEM Reference**:
- Main loop: fhem/26_KM273v018.pm:2052-2187 (`KM273_ReadElementList()`)
- Binary parsing: fhem/26_KM273v018.pm:2135-2143 (element structure)
- CAN ID construction: fhem/26_KM273v018.pm:2229-2230 (formula)

### 2. Binary Element Data Parsing *(NEW)*

**Question**: How to parse 18-byte header + variable-length name structure reliably?

**NEEDS CLARIFICATION**:
- Endianness of multi-byte fields (idx=2 bytes, max/min=4 bytes)
- String encoding for name field (ASCII, UTF-8, Latin-1?)
- Null termination handling in name field
- Malformed element handling (len=0, len > remaining data)

**Structure** (from FHEM:2135-2143):
```
idx      (2 bytes)   - parameter index
extid    (7 bytes)   - hexadecimal string representation
max      (4 bytes)   - maximum value
min      (4 bytes)   - minimum value
len      (1 byte)    - name length (including null terminator?)
name     (len-1 bytes) - parameter name string
```

### 3. Parameter Caching Strategy *(NEW)*

**Question**: How to implement high-performance caching that reduces discovery from ~30s to <3s?

**NEEDS CLARIFICATION**:
- Cache format: JSON (human-readable) vs pickle (faster) vs custom binary
- Cache location: user config dir, app data dir, temp dir
- Cache invalidation triggers: device ID change, firmware version change, corrupted file
- Device identifier: serial number, MAC address, unique CAN response?

**Requirements** (from spec FR-019 to FR-023):
- Persistent storage after discovery
- Load on subsequent connections
- Integrity validation (checksum)
- Device identifier matching

### 4. CAN ID Construction Formula *(NEW)*

**Question**: How to correctly implement dynamic CAN ID calculation?

**Decision**: Use exact FHEM formula (no clarification needed - spec is clear)

**Formula** (from FHEM:2229-2230):
```python
# Read request CAN ID
rtr = 0x04003FE0 | (idx << 14)

# Write/response CAN ID
txd = 0x0C003FE0 | (idx << 14)
```

**Verification**: Contract tests will verify calculated IDs match expected values for known idx values

### 5. Fallback Data Structure *(EXISTING - STILL VALID)*

**Decision**: Preserve existing research decision on @KM273_elements_default conversion

**From Previous Research**:
- Manual Perl-to-Python conversion (one-time)
- Store as `parameter_data.py` Python module
- Contract test verifies fidelity
- Used ONLY when discovery fails (FR-006)

### 6. Parameter Class Design *(EXISTING - STILL VALID)*

**Decision**: Preserve existing dataclass design with additions

**Updates Needed**:
```python
@dataclass(frozen=True)
class Parameter:
    """Represents a discovered or fallback heat pump parameter.

    # PROTOCOL: Maps to binary element structure (FHEM:2135-2143)
    # or KM273_elements_default array (FHEM:218+) for fallback
    """
    idx: int              # Parameter index (used for CAN ID calculation)
    extid: str            # External ID (7-byte hex string)
    min: int              # Minimum allowed value
    max: int              # Maximum allowed value
    format: str           # Data format (int, temp, etc.)
    read: int             # Read-only flag (0=writable, 1=read-only)
    text: str             # Human-readable parameter name

    # NEW: Source tracking
    source: Literal["discovered", "fallback"]  # Track how parameter was obtained

    def is_writable(self) -> bool:
        """Check if parameter is writable."""
        return self.read == 0

    def validate_value(self, value: int) -> bool:
        """Validate if value is within allowed range."""
        return self.min <= value <= self.max

    # NEW: CAN ID calculation methods
    def get_read_can_id(self) -> int:
        """Calculate CAN ID for read request.

        # PROTOCOL: Formula from FHEM:2229
        """
        return 0x04003FE0 | (self.idx << 14)

    def get_write_can_id(self) -> int:
        """Calculate CAN ID for write request.

        # PROTOCOL: Formula from FHEM:2230
        """
        return 0x0C003FE0 | (self.idx << 14)
```

### 7. Lookup Mechanism *(EXISTING - STILL VALID)*

**Decision**: Preserve dual-dict design (by idx, by name) - O(1) lookup for both

**No changes needed** - existing design supports both discovered and fallback parameters

### 8. Testing Strategy *(UPDATED)*

**Additional Test Requirements**:

**Discovery Protocol Tests**:
- Mock CAN adapter simulating element count response
- Mock CAN adapter simulating element data chunks (4096-byte)
- Binary parser with known-good test vectors
- Malformed data handling (incomplete chunks, invalid lengths)

**Cache Tests**:
- Roundtrip: discover → cache → load → verify identical
- Cache invalidation: detect corrupt cache, wrong device
- Performance: cached load < 3 seconds

**Contract Tests**:
- Binary element structure matches FHEM specification
- CAN ID formulas produce correct results
- Fallback data still matches Perl source

## Phase 1: Design Artifacts

**Status**: TO GENERATE (after Phase 0 research completion)

Will create/update:
1. **data-model.md**:
   - Parameter entity (updated with CAN ID methods)
   - DiscoveredElement entity (binary parsing intermediate)
   - ParameterCache entity (persistence format)
   - ParameterRegistry entity (lookup + cache management)

2. **quickstart.md**:
   - Discovery flow example
   - Cached loading example
   - Fallback scenario example
   - Parameter lookup and validation examples

3. **contracts/** (if needed):
   - Not applicable - this is a library feature, no API contracts

## Next Steps

1. **Complete Phase 0 Research**:
   - Resolve all NEEDS CLARIFICATION items
   - Update research.md with decisions
   - Document binary parsing strategy
   - Document caching approach

2. **Phase 1 Design**:
   - Generate/update data-model.md with discovery entities
   - Update quickstart.md with discovery examples

3. **Phase 2 Implementation**:
   - Regenerate tasks.md with discovery tasks
   - Implement in priority order: P0 (discovery) → P1 (reading) → P2 (validation, caching) → P3 (access methods)
