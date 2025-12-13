# Implementation Plan: Home Assistant Integration

**Branch**: `011-ha-integration` | **Date**: 2025-12-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-ha-integration/spec.md`

## Summary

Implement a Home Assistant custom integration for monitoring and controlling a Buderus WPS heat pump via CAN bus over USB serial. The integration provides temperature sensors, compressor status, energy blocking switch, and DHW extra production control. **Significant foundation exists** - this plan focuses on refinements to match spec clarifications.

## Technical Context

**Language/Version**: Python 3.9+ (Home Assistant compatibility)
**Primary Dependencies**: Home Assistant Core APIs, pyserial, voluptuous, existing buderus_wps library
**Storage**: N/A (stateless - reads from heat pump)
**Testing**: pytest with Home Assistant test utilities
**Target Platform**: Home Assistant on Linux (Raspberry Pi primary), local USB serial only
**Project Type**: Single project (Home Assistant custom component)
**Performance Goals**: Sensor updates within 60s (configurable 10-300s), commands within 30s
**Constraints**: Single heat pump, local USB only, YAML config only (no config flow)
**Scale/Scope**: 8 entities (5 temp sensors, 1 binary sensor, 1 switch, 1 number)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | ✅ PASS | Integration uses existing `buderus_wps` library |
| II. Hardware Abstraction | ✅ PASS | USB serial via abstracted adapter layer |
| III. Safety & Reliability | ✅ PASS | Exponential backoff reconnection, graceful error handling |
| IV. Comprehensive Test Coverage | ⚠️ PENDING | Tests required for all acceptance scenarios |
| V. Protocol Documentation | ✅ PASS | Parameters documented in library |
| VI. Home Assistant Standards | ✅ PASS | Uses HA entity types, async I/O, YAML config |
| VII. CLI Design | N/A | This is HA integration, not CLI |

**Gate Result**: PASS (tests must be added during implementation)

## Project Structure

### Documentation (this feature)

```
specs/011-ha-integration/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (HA service schemas)
└── tasks.md             # Phase 2 output
```

### Source Code (existing + modifications)

```
custom_components/buderus_wps/
├── __init__.py          # Integration setup (exists, needs scan interval validation)
├── const.py             # Constants (exists, needs entity name updates)
├── coordinator.py       # Data coordinator (exists, needs exponential backoff)
├── entity.py            # Base entity (exists, needs name prefix)
├── sensor.py            # Temperature sensors (exists, needs name updates)
├── binary_sensor.py     # Compressor status (exists, needs name updates)
├── switch.py            # Energy block (exists), DHW extra (TO REMOVE)
├── number.py            # DHW extra duration (NEW - replaces switch)
└── select.py            # Mode selects (exists, bonus functionality)

tests/
├── unit/
│   └── test_ha_integration.py       # Unit tests for HA entities
├── integration/
│   └── test_ha_coordinator.py       # Integration tests for coordinator
└── acceptance/
    └── test_ha_acceptance.py        # Acceptance scenario tests
```

**Structure Decision**: Extend existing custom_components structure. Key changes:
1. Replace `DHWExtraSwitch` with `DHWExtraNumber` entity
2. Add exponential backoff reconnection to coordinator
3. Update all entity names to include "Heat Pump" prefix
4. Add scan interval validation (10-300s range)

## Existing Implementation Analysis

### What's Already Working

| Component | Status | Notes |
|-----------|--------|-------|
| Temperature sensors (5) | ✅ Working | Uses broadcast monitoring |
| Compressor binary sensor | ✅ Working | From MenuAPI status |
| Energy block switch | ✅ Working | ADDITIONAL_BLOCKED parameter |
| DHW extra switch | ⚠️ Wrong type | Should be number (0-24h), not switch |
| YAML configuration | ✅ Working | Port and scan_interval |
| DataUpdateCoordinator | ⚠️ Incomplete | Missing exponential backoff |
| Entity naming | ⚠️ Non-compliant | Missing "Heat Pump" prefix |

### Required Changes

1. **DHW Extra Control**: Convert from `SwitchEntity` to `NumberEntity` (0-24 hours)
2. **Reconnection Logic**: Add exponential backoff (5s → 10s → 20s → ... → 120s max)
3. **Entity Names**: Add "Heat Pump" prefix per clarification
4. **Scan Interval**: Validate range 10-300 seconds
5. **Tests**: Add comprehensive test coverage for all acceptance scenarios

## Complexity Tracking

*No constitution violations requiring justification*

## Design Decisions

### D1: DHW Extra as Number Entity

**Decision**: Use `NumberEntity` with range 0-24 (hours)
**Rationale**: Matches heat pump native behavior where duration is set in hours. Setting to 0 stops extra production.
**Alternative Rejected**: Switch with hardcoded 60-minute duration - less flexible, doesn't match user expectations

### D2: Exponential Backoff Strategy

**Decision**: 5s initial delay, double each retry, cap at 120s
**Rationale**: Balances quick recovery for transient issues vs. not hammering USB on persistent failures
**Sequence**: 5s → 10s → 20s → 40s → 80s → 120s → 120s → ...

### D3: Entity Naming Convention

**Decision**: Prefix all entity names with "Heat Pump" (e.g., "Heat Pump Outdoor Temperature")
**Rationale**: Clear device identification in HA UI, especially when multiple integrations present
**Implementation**: Set in entity `_attr_name` attribute

### D4: Keep Select Entities (Bonus)

**Decision**: Retain HeatingSeasonMode and DHWProgramMode select entities
**Rationale**: Already implemented and working, useful for advanced peak-hour blocking scenarios
**Spec Note**: Not in original spec but adds value without complexity

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| USB disconnection during operation | Medium | Medium | Exponential backoff, unavailable state |
| Broadcast monitoring timeout | Low | Low | Fallback to RTR requests if needed |
| HA startup race condition | Low | Medium | Proper async initialization |

## Next Steps

1. **Phase 0**: Research HA NumberEntity best practices, backoff patterns
2. **Phase 1**: Generate data-model.md, contracts, quickstart.md
3. **Phase 2**: Generate tasks.md with implementation steps
4. **Implementation**: Execute tasks with TDD approach
