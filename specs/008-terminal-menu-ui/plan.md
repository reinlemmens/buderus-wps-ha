# Implementation Plan: Terminal Menu UI

**Branch**: `008-terminal-menu-ui` | **Date**: 2025-12-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-terminal-menu-ui/spec.md`

## Summary

Build a terminal-based UI application using Python curses that exposes the Menu API (feature 007) through an interactive interface. The application provides a status dashboard on startup with temperatures from broadcast monitoring, hierarchical menu navigation mirroring the physical display, and parameter editing with validation. Supports 1-4 heating circuits dynamically configured via buderus-wps.yaml.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- `curses` (standard library) - terminal UI rendering
- `buderus_wps` (feature 007) - Menu API, CAN communication
- `PyYAML` - configuration file parsing

**Storage**: `buderus-wps.yaml` configuration file for circuit mappings
**Testing**: pytest with curses mocking
**Target Platform**: Linux on Raspberry Pi, SSH-accessible terminal
**Project Type**: Single project (CLI extension)
**Performance Goals**:
- Status display within 3 seconds of launch (SC-001)
- Any menu item reachable in ≤5 key presses (SC-002)
- Temperature edit in under 30 seconds (SC-003)

**Constraints**:
- Minimum terminal size: 80x24
- SSH-compatible (no mouse, ANSI escape codes only)
- Manual refresh only (no automatic polling)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | ✅ PASS | TUI in `buderus_wps_cli/tui/`, uses `buderus_wps` library |
| II. Hardware Abstraction | ✅ PASS | Uses Menu API abstraction, no direct CAN access |
| III. Safety & Reliability | ✅ PASS | Validation before writes, read-only dashboard, graceful error handling |
| IV. Comprehensive Test Coverage | ⚠️ REQUIRED | Must have tests for all 8 user stories + 6 edge cases |
| V. Protocol Documentation | ✅ PASS | No new protocol elements; uses existing API |
| VI. HA Integration Standards | N/A | Not applicable to CLI feature |
| VII. CLI Design Principles | ✅ PASS | Keyboard navigation, clean exit codes, help text |

**Testing Requirements** (from Constitution IV):
- Unit tests: Screen rendering, keyboard handling, value formatting
- Integration tests: Menu navigation with mock API, edit flow with validation
- Acceptance tests: All 8 user story scenarios (dashboard, navigation, editing, circuits, schedules, energy, alarms, vacation)
- Edge case tests: Connection loss, invalid input, resize, Ctrl+C, missing config

## Project Structure

### Documentation (this feature)

```
specs/008-terminal-menu-ui/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Technical research
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Implementation quickstart
└── contracts/           # Phase 1: API contracts
    └── tui_api.py       # TUI internal API contract
```

### Source Code (repository root)

```
buderus_wps_cli/
├── __init__.py
├── cli.py               # Existing CLI entry point
└── tui/                 # NEW: Terminal UI package
    ├── __init__.py      # Package exports
    ├── app.py           # Main application loop (exists, needs extension)
    ├── state.py         # Application state management (exists)
    ├── keyboard.py      # Key handling (exists)
    ├── screens/         # Screen implementations
    │   ├── __init__.py
    │   ├── base.py      # Base screen class (exists)
    │   ├── dashboard.py # Status dashboard (NEW)
    │   ├── menu.py      # Menu navigation (exists, needs extension)
    │   ├── editor.py    # Parameter editing (NEW)
    │   └── schedule.py  # Schedule display/editing (NEW)
    └── widgets/         # Reusable UI components
        ├── __init__.py  # (exists)
        ├── status_bar.py # (exists)
        ├── help_bar.py  # (exists)
        └── breadcrumb.py # (exists)

tests/
├── unit/
│   └── tui/
│       ├── test_keyboard.py     # Key mapping tests
│       ├── test_screens.py      # Screen rendering tests
│       └── test_editor.py       # Edit mode tests
├── integration/
│   └── tui/
│       ├── test_navigation.py   # Menu navigation flow
│       └── test_edit_flow.py    # Edit, validate, write flow
└── acceptance/
    └── tui/
        ├── test_us1_dashboard.py    # User Story 1
        ├── test_us2_navigation.py   # User Story 2
        ├── test_us3_dhw_edit.py     # User Story 3
        ├── test_us4_circuits.py     # User Story 4
        ├── test_us5_schedules.py    # User Story 5
        ├── test_us6_energy.py       # User Story 6
        ├── test_us7_alarms.py       # User Story 7
        └── test_us8_vacation.py     # User Story 8
```

**Structure Decision**: Extends existing `buderus_wps_cli/tui/` package with new screens for dashboard, editor, and schedule display. Tests organized by layer (unit/integration/acceptance) with dedicated TUI subdirectory.

## Complexity Tracking

*No constitution violations requiring justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
