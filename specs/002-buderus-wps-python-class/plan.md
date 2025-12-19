# Implementation Plan: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Branch**: `002-buderus-wps-python-class` | **Date**: 2025-12-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-buderus-wps-python-class/spec.md`

## Summary

This feature implements a Python class that discovers and represents Buderus WPS heat pump parameters. The key insight from FHEM investigation is that CAN IDs are dynamically constructed (`rtr = 0x04003FE0 | (idx << 14)`) based on parameter indices discovered from the device. The implementation provides:

1. **Dynamic Discovery**: CAN bus protocol to retrieve parameter definitions from device
2. **Static Fallback**: Use @KM273_elements_default when discovery fails
3. **Parameter Access**: O(1) lookup by index or name
4. **Validation**: Min/max range checking before write operations
5. **Caching**: Persist discovered parameters to avoid 30s discovery on reconnection

**Current Status**: User Stories 1-3 are already implemented with static data. This plan extends the implementation to include User Story 0 (discovery) and User Story 4 (caching).

## Technical Context

**Language/Version**: Python 3.9+ (Home Assistant compatibility, per constitution)
**Primary Dependencies**: pyserial (existing), struct (stdlib), json (stdlib for cache)
**Storage**: JSON file for parameter cache (filesystem-based, portable)
**Testing**: pytest with coverage reporting (existing infrastructure)
**Target Platform**: Linux (Raspberry Pi primary), cross-platform library
**Project Type**: Single library package with CLI wrapper
**Performance Goals**: Discovery <30s, lookup <1ms, cache load <3s
**Constraints**: No external dependencies beyond pyserial, must run without hardware (mocks)
**Scale/Scope**: 400-2000 parameters, 18-byte header + variable name per element

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | PASS | Core in `buderus_wps/`, CLI wrapper separate |
| II. Hardware Abstraction & Protocol Fidelity | PASS | CAN adapter abstraction exists, FHEM protocol followed |
| III. Safety & Reliability | PASS | Validation before writes, fallback mode supported |
| IV. Comprehensive Test Coverage | PASS | TDD approach, contract tests for protocol fidelity |
| V. Protocol Documentation & Traceability | PASS | FHEM line references documented in spec |
| VI. Home Assistant Integration Standards | N/A | Library focus, HA integration is separate feature |
| VII. CLI Design Principles | N/A | CLI wrapper is separate feature |

**Gate Status**: PASSED - No violations requiring justification.

## Project Structure

### Documentation (this feature)

```
specs/002-buderus-wps-python-class/
├── spec.md              # Feature specification (updated with discovery protocol)
├── plan.md              # This file
├── research.md          # Phase 0 output - protocol analysis
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - integration examples
├── checklists/          # Quality validation checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```
buderus_wps/                    # Core library package
├── __init__.py                 # Package exports
├── parameter.py                # Parameter + HeatPump classes (EXISTS)
├── parameter_data.py           # Static fallback data (EXISTS)
├── discovery.py                # NEW: Discovery protocol implementation
├── can_ids.py                  # NEW: CAN ID construction formulas
├── cache.py                    # NEW: Parameter cache management
├── exceptions.py               # Custom exceptions (EXISTS)
├── can_adapter.py              # CAN adapter abstraction (EXISTS)
└── can_message.py              # CAN message encoding (EXISTS)

tests/
├── unit/
│   ├── test_parameter.py       # Parameter class tests (EXISTS)
│   ├── test_heat_pump.py       # HeatPump class tests (EXISTS)
│   ├── test_discovery.py       # NEW: Discovery protocol unit tests
│   ├── test_can_ids.py         # NEW: CAN ID formula tests
│   └── test_cache.py           # NEW: Cache management tests
├── integration/
│   ├── test_parameter_validation.py  # Validation tests (EXISTS)
│   └── test_discovery_flow.py        # NEW: End-to-end discovery
├── contract/
│   ├── test_parameter_fidelity.py    # FHEM data match (EXISTS)
│   ├── test_can_id_formulas.py       # NEW: FHEM formula verification
│   └── test_binary_parsing.py        # NEW: Element structure parsing
└── acceptance/
    ├── test_acceptance_us0.py        # NEW: Discovery acceptance scenarios
    └── test_acceptance_us4.py        # NEW: Caching acceptance scenarios
```

**Structure Decision**: Extends existing single-package structure. New modules (`discovery.py`, `can_ids.py`, `cache.py`) integrate with existing `parameter.py` and `parameter_data.py`. Test structure mirrors existing patterns with new test files for new functionality.

## Complexity Tracking

*No constitution violations to justify.*

## Implementation Phases

### Phase A: Existing Implementation (COMPLETE)

The following is already implemented and tested:
- Parameter dataclass with 7 attributes
- HeatPump class with index/name lookup
- Static parameter data (1789 entries from @KM273_elements_default)
- Validation methods (is_writable, validate_value)
- 238 tests passing with 100% coverage

### Phase B: CAN ID Construction (NEW)

Add dynamic CAN ID calculation:
- `can_ids.py`: Implement formulas from FHEM (lines 2229-2230)
- Contract tests verifying formula correctness
- Integration with Parameter class

### Phase C: Binary Element Parsing (NEW)

Implement element data structure parsing:
- Parse 18-byte header + variable name
- Handle endianness (little-endian per FHEM)
- Validate parsed data integrity

### Phase D: Discovery Protocol (NEW)

Implement the discovery sequence:
- Element count request/response (0x01FD7FE0/0x09FD7FE0)
- Element data request/response (0x01FD3FE0/0x09FDBFE0)
- 4096-byte chunk handling
- Timeout and error recovery

### Phase E: Caching System (NEW)

Implement parameter cache:
- JSON serialization of discovered parameters
- Cache validation (checksum, device identifier)
- Cache invalidation on firmware change
- Bypass option for forced re-discovery

### Phase F: Integration (NEW)

Connect all components:
- HeatPump class uses discovery or fallback
- CAN IDs computed from discovered idx values
- Cache loaded on initialization if valid

## Key Design Decisions

1. **JSON for Cache**: Simple, human-readable, stdlib-only. No external dependencies.

2. **Separate Modules**: Keep discovery, CAN IDs, and caching in separate files for testability and maintainability. Each module has single responsibility.

3. **Fallback Strategy**:
   - Try cache first (fastest)
   - Try discovery if cache invalid (slow but accurate)
   - Fall back to static data if discovery fails (always available)

4. **CAN Adapter Independence**: Discovery protocol uses abstract CAN adapter interface. Real USBtin or mock adapters both work.

5. **Immutable Parameters**: Parameter dataclass remains frozen. Discovery creates new instances, doesn't modify existing.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Binary format varies by firmware | Validate structure before parsing, fall back on error |
| Discovery timeout on slow devices | Configurable timeout, partial discovery recovery |
| Cache corruption | Checksum validation, automatic re-discovery |
| Large parameter count (~2000) | Streaming parse, don't load all to memory at once |
| Element name encoding issues | Handle null bytes, truncate at len-1 |

## Dependencies Between Features

- **001-can-usb-serial**: CAN adapter layer (EXISTS, provides USBtin communication)
- **005-can-parameter-access**: Will use this feature's HeatPump class for parameter read/write

## Files to Create/Modify

### New Files
- `buderus_wps/discovery.py` - Discovery protocol implementation
- `buderus_wps/can_ids.py` - CAN ID construction formulas
- `buderus_wps/cache.py` - Parameter cache management
- `tests/unit/test_discovery.py` - Discovery unit tests
- `tests/unit/test_can_ids.py` - CAN ID formula tests
- `tests/unit/test_cache.py` - Cache unit tests
- `tests/integration/test_discovery_flow.py` - Integration tests
- `tests/contract/test_can_id_formulas.py` - FHEM formula verification
- `tests/contract/test_binary_parsing.py` - Element structure parsing
- `tests/acceptance/test_acceptance_us0.py` - Discovery acceptance
- `tests/acceptance/test_acceptance_us4.py` - Caching acceptance

### Modified Files
- `buderus_wps/parameter.py` - Add get_read_can_id(), get_write_can_id() methods
- `buderus_wps/__init__.py` - Export new modules

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Discovery time | <30 seconds | Timer in acceptance test |
| Cache load time | <3 seconds | Timer in acceptance test |
| Lookup time | <1ms | Performance test (1000 iterations) |
| Parse accuracy | 100% | Contract tests vs known elements |
| CAN ID accuracy | 100% | Contract tests vs FHEM formula |
| Test coverage | 100% | pytest-cov for new functionality |
