# Implementation Plan: Heat Pump Menu API

**Branch**: `007-heatpump-menu-api` | **Date**: 2025-11-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-heatpump-menu-api/spec.md`

## Summary

This feature creates a high-level Python API that provides menu-style access to the Buderus WPS heat pump, mirroring the physical display menu structure. It builds on top of the existing `HeatPumpClient` (feature 002) to provide:
- Hierarchical menu navigation matching the physical display
- Human-readable status and temperature readings
- Schedule management with proper sw1/sw2 encoding
- Program mode control
- Vacation mode configuration
- Alarm read/acknowledge/clear capabilities
- Multi-circuit support (1-4 circuits)

The API will use English method names aligned with menu labels (e.g., `hot_water` not `dhw`) per Success Criterion SC-006.

## Technical Context

**Language/Version**: Python 3.9+ (per constitution, for Home Assistant compatibility)
**Primary Dependencies**:
- `buderus_wps` (existing library - HeatPumpClient, ParameterRegistry, USBtinAdapter)
- `pyserial` (transitive via buderus_wps)
**Storage**: N/A (stateless API over CAN bus)
**Testing**: pytest with mocks (no physical hardware in tests)
**Target Platform**: Linux on Raspberry Pi (primary), cross-platform compatible
**Project Type**: Single Python library extension
**Performance Goals**:
- Read 4 temperatures + status in <2 seconds (SC-001)
- Navigate and read any setting in <5 seconds (SC-002)
**Constraints**:
- Single-threaded synchronous operation (per existing library design)
- 5-second timeout for CAN operations
- No automatic retries (per constitution)
**Scale/Scope**: Single heat pump connection, 37 functional requirements, 9 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | PASS | Extends `buderus_wps` library with new `MenuAPI` class |
| II. Hardware Abstraction & Protocol Fidelity | PASS | Uses existing CAN protocol via HeatPumpClient; adds sw2 odd-index fix |
| III. Safety & Reliability | PASS | Validation before writes (FR-031), range checks (FR-034), read-only protection (FR-033) |
| IV. Comprehensive Test Coverage | REQUIRED | Must have tests for all 37 FRs, 9 user stories, edge cases |
| V. Protocol Documentation | PASS | Will document sw2 odd-index discovery, menu-to-parameter mapping |
| VI. Home Assistant Integration | DEFERRED | Not in scope for this feature (future feature) |
| VII. CLI Design | N/A | API-only feature |

**Gate Result**: PASS - No violations requiring justification.

## Project Structure

### Documentation (this feature)

```
specs/007-heatpump-menu-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```
buderus_wps/
├── __init__.py          # Update exports
├── menu_api.py          # NEW: High-level menu API (main deliverable)
├── menu_structure.py    # NEW: Menu hierarchy definition
├── schedule_codec.py    # NEW: sw1/sw2 time encoding/decoding
├── heat_pump.py         # Existing: May need minor extensions
├── parameter_registry.py # Existing: Parameter lookups
└── ...                  # Other existing modules

tests/
├── unit/
│   ├── test_menu_api.py         # NEW: MenuAPI unit tests
│   ├── test_menu_structure.py   # NEW: Menu hierarchy tests
│   └── test_schedule_codec.py   # NEW: Time encoding tests
├── integration/
│   └── test_menu_api_integration.py  # NEW: Mocked HeatPumpClient tests
├── contract/
│   └── test_schedule_encoding.py     # NEW: sw1/sw2 protocol tests
└── acceptance/
    └── test_user_stories.py          # NEW: All 9 user story scenarios
```

**Structure Decision**: Extends existing `buderus_wps` package with new modules. No new packages needed since this is a library extension.

## Complexity Tracking

*No violations to justify - all principles satisfied.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |
