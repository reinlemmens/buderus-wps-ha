# Implementation Plan: Buderus WPS Heat Pump Python Class

**Branch**: `002-buderus-wps-python-class` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-buderus-wps-python-class/spec.md`

## Summary

Create a Python class that represents the Buderus WPS heat pump with all 400+ parameters from the KM273_elements_default array in the FHEM Perl module. The class provides structured access to parameter metadata (index, address, name, format, min/max values, read flag) and supports lookup by both index and name with value validation capabilities.

**Technical Approach**: Parse the Perl data structure from `fhem/26_KM273v018.pm`, convert to Python data structures (dataclass or named tuple), implement efficient lookup mechanisms (dict for name-based, list for index-based), and provide validation methods using the min/max constraints.

## Technical Context

**Language/Version**: Python 3.9+ (per constitution for Home Assistant compatibility)
**Primary Dependencies**: Python standard library only (typing, dataclasses)
**Storage**: Static data structure loaded from Python module (no external storage)
**Testing**: pytest with coverage reporting
**Target Platform**: Linux on Raspberry Pi (primary), cross-platform compatible
**Project Type**: Single project (core library)
**Performance Goals**: Parameter lookup < 1 second (both by name and index per SC-002, SC-003)
**Constraints**: No external dependencies for core functionality, must preserve exact data from FHEM reference
**Scale/Scope**: 400+ parameters, lightweight in-memory data structure

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Library-First Architecture
**Status**: ✅ PASS
**Rationale**: This feature creates part of the core library (`buderus_wps`). The parameter class will be independently usable, fully tested, and documented as required.

### Principle II: Hardware Abstraction & Protocol Fidelity
**Status**: ✅ PASS
**Rationale**: This feature preserves the exact KM273_elements_default array structure from the FHEM reference implementation. All indices, addresses (extid), min/max values, formats, read flags, and text names are preserved exactly (FR-007).

### Principle III: Safety & Reliability
**Status**: ✅ PASS
**Rationale**: The parameter class provides validation capability (FR-006) to check if values are within allowed min/max ranges. This is a foundational safety feature for preventing invalid write operations.

### Principle IV: Comprehensive Test Coverage
**Status**: ✅ PASS
**Rationale**: Feature spec includes detailed acceptance scenarios for all 3 user stories plus edge cases. Test plan will include:
- Unit tests for parameter class and lookup methods
- Integration tests for parameter validation
- Contract tests verifying data matches FHEM reference
- Acceptance tests for all scenarios in spec.md

### Principle V: Protocol Documentation & Traceability
**Status**: ✅ PASS
**Rationale**: Code will include cross-references to FHEM implementation, document data types/ranges, and use `# PROTOCOL:` comments for protocol-critical code.

### All Other Principles
**Status**: ✅ PASS
**Rationale**: Principles VI (Home Assistant) and VII (CLI) not applicable to this library-only feature. Technical standards (Python 3.9+, pytest, type hints, docstrings) will be followed.

## Project Structure

### Documentation (this feature)

```
specs/002-buderus-wps-python-class/
├── plan.md              # This file
├── research.md          # Phase 0: Perl parsing strategy, data structure design
├── data-model.md        # Phase 1: Parameter and HeatPump entities
├── quickstart.md        # Phase 1: Usage examples for developers
└── tasks.md             # Phase 2: Implementation task breakdown
```

### Source Code (repository root)

```
buderus_wps/              # Core library package (existing)
├── __init__.py
├── can_adapter.py        # Existing: CAN communication
├── can_message.py        # Existing: Message encoding/decoding
├── exceptions.py         # Existing: Exception types
├── parameter.py          # NEW: Parameter class and definitions
└── heat_pump.py          # NEW: HeatPump class (optional container)

fhem/                     # Reference implementation (existing)
└── 26_KM273v018.pm       # Source of KM273_elements_default data

tests/
├── unit/
│   ├── test_parameter.py # NEW: Unit tests for parameter class
│   └── test_heat_pump.py # NEW: Unit tests for heat pump class (if created)
├── integration/
│   └── test_parameter_validation.py # NEW: Integration tests for validation
└── contract/
    └── test_parameter_fidelity.py # NEW: Verify against FHEM reference
```

**Structure Decision**: Single project structure using existing `buderus_wps/` package. New parameter-related classes will be added as `parameter.py` (and optionally `heat_pump.py` if a container class is needed). The existing test structure (`tests/unit/`, `tests/integration/`, `tests/contract/`) will be used for comprehensive test coverage.

## Complexity Tracking

*No constitution violations detected. This section intentionally left empty.*

