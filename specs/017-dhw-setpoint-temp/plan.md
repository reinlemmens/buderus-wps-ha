# Implementation Plan: DHW Setpoint Temperature Parameter

**Branch**: `017-dhw-setpoint-temp` | **Date**: 2026-01-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-dhw-setpoint-temp/spec.md`

## Summary

Add the `DHW_CALCULATED_SETPOINT_TEMP` parameter (idx 385, range 40-70°C) as a readable and writable entity across the library, CLI, and Home Assistant integration. This parameter controls the target temperature for normal DHW (domestic hot water) operation, distinct from the existing `XDHW_STOP_TEMP` used during boost mode.

**Technical Approach**: Follow the existing pattern established by `BuderusDHWStopTempNumber` - add coordinator read/write methods, create a new number entity, and leverage existing CLI infrastructure. No new architectural components required.

## Technical Context

**Language/Version**: Python 3.9+ (Home Assistant compatibility requirement)
**Primary Dependencies**: homeassistant, pyserial (existing)
**Storage**: N/A (reads/writes to heat pump via CAN bus)
**Testing**: pytest with contract, integration, unit, and acceptance test layers
**Target Platform**: Home Assistant on Linux (Supervisor add-on)
**Project Type**: Single project with library + HA integration
**Performance Goals**: 30s page load, 10s write confirmation, 5s CLI response (from spec)
**Constraints**: CAN bus communication latency, serial port access
**Scale/Scope**: Single heat pump, single user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No project-specific constitution gates defined. Following established patterns:
- [x] Library-first: Parameter already in `parameter_defaults.py`
- [x] CLI interface: Will use existing `read_parameter`/`write_value` methods
- [x] Testing: Will add unit tests for new coordinator methods and HA entity
- [x] Simplicity: Follows existing `BuderusDHWStopTempNumber` pattern exactly

## Project Structure

### Documentation (this feature)

```text
specs/017-dhw-setpoint-temp/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
buderus_wps/                    # Core library (parameter already defined)
├── parameter_defaults.py       # DHW_CALCULATED_SETPOINT_TEMP already at idx 385
├── heat_pump.py               # read_parameter/write_value (existing)
└── menu_api.py                # Optional: add property accessor

custom_components/buderus_wps/  # Home Assistant integration
├── coordinator.py             # Add dhw_setpoint read + async_set_dhw_setpoint method
├── number.py                  # Add BuderusDHWSetpointNumber entity
└── const.py                   # Add icon constant if needed

tests/
├── unit/
│   └── test_ha_number.py      # Add tests for new number entity
├── integration/
│   └── test_coordinator.py    # Add tests for coordinator methods
└── contract/
    └── test_dhw_setpoint.py   # Contract tests for parameter read/write
```

**Structure Decision**: Single project structure - this feature adds to existing modules without new components.

## Complexity Tracking

No constitution violations. Feature follows established patterns with minimal additions:
- 1 new field in `BuderusData` dataclass
- 2 new coordinator methods (read in `_sync_fetch_data`, write `async_set_dhw_setpoint`)
- 1 new number entity class (following `BuderusDHWStopTempNumber` pattern)

---

## Phase 0: Research

### Research Tasks

1. **Verify parameter behavior**: Confirm `DHW_CALCULATED_SETPOINT_TEMP` (idx 385) read/write works on actual hardware
2. **Identify existing patterns**: Review `BuderusDHWStopTempNumber` implementation for consistency
3. **Check step increment**: Determine appropriate step (0.5°C vs 1.0°C)

### Findings

See [research.md](research.md) for detailed findings.

---

## Phase 1: Design

### Data Model

See [data-model.md](data-model.md) for entity definitions.

### API Contracts

See [contracts/](contracts/) for interface definitions.

### Quick Start

See [quickstart.md](quickstart.md) for implementation guide.
