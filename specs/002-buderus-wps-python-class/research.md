# Research: Buderus WPS Heat Pump Python Class

**Feature**: 002-buderus-wps-python-class
**Date**: 2025-10-24
**Status**: Complete

## Overview

This document captures research decisions for implementing a Python class representing the Buderus WPS heat pump with all parameters from the FHEM KM273_elements_default array.

## Research Topics

### 1. Perl Data Structure Parsing Strategy

**Question**: How should we extract and convert the KM273_elements_default array from Perl to Python?

**Decision**: Manual one-time conversion with automated verification

**Rationale**:
- The FHEM Perl file contains a static array that rarely changes
- Perl parsing in Python adds unnecessary runtime dependency
- Manual conversion is more reliable and maintainable
- We can create a verification script to check fidelity after conversion

**Alternatives Considered**:
1. **Runtime Perl parsing** - Rejected because:
   - Requires Perl installation as a dependency
   - Adds complexity for a one-time conversion task
   - Runtime overhead for static data

2. **Regex-based extraction** - Rejected because:
   - Perl syntax is complex and context-sensitive
   - Risk of parsing errors with edge cases
   - Still requires verification step

**Implementation Approach**:
1. Create Python script to parse Perl array structure using simple regex
2. Convert to Python list of dictionaries
3. Store as Python module (`parameter_data.py`)
4. Create contract test to verify Python data matches Perl source

**Perl Structure Example**:
```perl
{ 'idx' => 0, 'extid' => '814A53C66A0802', 'max' => 0, 'min' => 0, 'format' => 'int', 'read' => 0, 'text' => 'ACCESSORIES_CONNECTED_BITMASK' }
```

**Python Structure**:
```python
{
    "idx": 0,
    "extid": "814A53C66A0802",
    "max": 0,
    "min": 0,
    "format": "int",
    "read": 0,
    "text": "ACCESSORIES_CONNECTED_BITMASK"
}
```

### 2. Python Data Structure Design

**Question**: What Python data structure should represent individual parameters and the parameter collection?

**Decision**: Use `dataclass` for Parameter, dict+list for lookup

**Rationale**:
- `@dataclass` provides type safety, immutability (frozen=True), and clean syntax
- Dict for O(1) name-based lookup
- List/dict for O(1) index-based lookup (handle gaps with dict)
- No external dependencies (dataclasses in stdlib since Python 3.7)

**Parameter Class Design**:
```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Parameter:
    """Represents a single Buderus WPS heat pump parameter.

    # PROTOCOL: Maps to KM273_elements_default array in fhem/26_KM273v018.pm
    """
    idx: int              # Sequential parameter index
    extid: str            # External ID (CAN address)
    min: int              # Minimum allowed value
    max: int              # Maximum allowed value
    format: str           # Data format (int, temp, etc.)
    read: int             # Read-only flag (0=writable, 1=read-only)
    text: str             # Human-readable parameter name

    def is_writable(self) -> bool:
        """Check if parameter is writable."""
        return self.read == 0

    def validate_value(self, value: int) -> bool:
        """Validate if value is within allowed range."""
        return self.min <= value <= self.max
```

**Alternatives Considered**:
1. **NamedTuple** - Rejected because:
   - Less clear syntax for methods
   - No built-in validation support

2. **Dict** - Rejected because:
   - No type safety
   - No IDE autocomplete
   - Easy to make typos in key names

3. **Pydantic BaseModel** - Rejected because:
   - Adds external dependency
   - Overkill for simple immutable data
   - Constitution requires minimal dependencies

### 3. Lookup Mechanism Design

**Question**: How to efficiently support lookup by both index and name?

**Decision**: Dual-index approach with dict for names, dict for indices

**Rationale**:
- Both operations need O(1) performance (SC-002, SC-003: < 1 second)
- Index lookup may have gaps (FR-008) so dict is safer than list
- Memory overhead is negligible for 400 entries
- Simple, predictable performance

**HeatPump Class Design**:
```python
class HeatPump:
    """Container for all Buderus WPS heat pump parameters."""

    def __init__(self):
        # Load from parameter_data module
        self._params_by_idx = {}   # {idx: Parameter}
        self._params_by_name = {}  # {text: Parameter}
        self._load_parameters()

    def get_parameter_by_index(self, idx: int) -> Parameter:
        """Get parameter by index. Raises KeyError if not found."""
        return self._params_by_idx[idx]

    def get_parameter_by_name(self, name: str) -> Parameter:
        """Get parameter by name. Raises KeyError if not found."""
        return self._params_by_name[name]

    def list_all_parameters(self) -> list[Parameter]:
        """Return all parameters sorted by index."""
        return sorted(self._params_by_idx.values(), key=lambda p: p.idx)
```

**Alternatives Considered**:
1. **Single dict with both indices** - Rejected because:
   - Mixes int and str keys (confusing)
   - No type safety for lookup operations

2. **List for index lookup** - Rejected because:
   - Requires handling gaps (idx 13 missing between 12 and 14)
   - Array resizing overhead if gaps are large
   - Dict is simpler and handles gaps naturally

3. **SQLite database** - Rejected because:
   - Overkill for static in-memory data
   - Adds I/O overhead
   - Violates "no external dependencies" constraint

### 4. Handling Non-Sequential Indices

**Question**: How to handle parameters with gaps in index sequence (FR-008)?

**Decision**: Use dict for index lookup, document gaps

**Rationale**:
- Dict naturally handles non-sequential keys
- No special logic needed
- Document gaps in data structure comments

**Example Gap**:
```python
# idx=13 is missing between idx=12 and idx=14
# This matches the FHEM reference implementation
```

**Implementation**:
- Contract test will verify indices match FHEM exactly
- get_parameter_by_index() raises KeyError for missing indices
- Documentation will note that gaps exist

### 5. Format Type Handling

**Question**: How to handle different format types (int, temp, etc.)?

**Decision**: Store as string, document known formats, allow extensibility

**Rationale**:
- FHEM reference uses string format field
- Preserves exact protocol fidelity (Principle II)
- Future features can interpret formats as needed
- This feature (002) only provides access to metadata

**Known Formats** (from FHEM):
- `"int"` - Integer value
- `"temp"` - Temperature value (format interpretation TBD in future features)
- Others may exist (to be documented as discovered)

**Implementation**:
```python
# In Parameter dataclass
format: str  # Known values: "int", "temp" - see protocol docs

# Future feature can add format-specific validation:
# def validate_by_format(self, value: Any) -> bool:
#     if self.format == "temp":
#         return self._validate_temperature(value)
#     ...
```

### 6. Test Strategy

**Question**: How to ensure comprehensive test coverage per Principle IV?

**Decision**: Four-layer test strategy matching feature requirements

**Test Layers**:
1. **Unit Tests** - `tests/unit/test_parameter.py`
   - Parameter class validation methods
   - is_writable() logic
   - validate_value() edge cases (min=max, negative values)

2. **Unit Tests** - `tests/unit/test_heat_pump.py`
   - Lookup by index (found, not found, gaps)
   - Lookup by name (found, not found, case sensitivity)
   - List all parameters
   - Performance: lookups < 1 second

3. **Integration Tests** - `tests/integration/test_parameter_validation.py`
   - Validation across multiple parameters
   - Read-only vs writable distinction
   - Format type handling

4. **Contract Tests** - `tests/contract/test_parameter_fidelity.py`
   - **CRITICAL**: Verify Python data matches FHEM Perl source
   - Parse Perl file and compare counts
   - Spot-check key parameters (idx=0, idx=1, last parameter)
   - Verify all indices present in Python data

**Coverage Target**: 100% of described functionality per Principle IV

### 7. Performance Considerations

**Question**: How to ensure < 1 second lookup performance (SC-002, SC-003)?

**Decision**: In-memory data structures with O(1) lookup

**Rationale**:
- Dict lookups are O(1) average case
- 400 entries is tiny for modern hardware
- No I/O or network operations
- Simple benchmarks confirm < 1ms typical performance

**Verification**:
- Add performance tests to measure lookup times
- Test with pytest-benchmark if needed
- Document typical performance in README

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| Perl Parsing | Manual conversion + verification | One-time task, no runtime dependency |
| Data Structure | dataclass for Parameter | Type safety, immutability, stdlib only |
| Lookup Mechanism | Dual dict (by idx, by name) | O(1) performance for both operations |
| Index Gaps | Dict handles naturally | No special logic needed |
| Format Types | Store as string | Preserves protocol fidelity |
| Testing | Four-layer strategy | Principle IV compliance |
| Performance | In-memory O(1) structures | Exceeds < 1s requirement |

## Next Steps

Proceed to Phase 1:
1. Generate data-model.md with Parameter and HeatPump entities
2. Create quickstart.md with usage examples
3. No contracts/ needed (this is a library-only feature with no API)

