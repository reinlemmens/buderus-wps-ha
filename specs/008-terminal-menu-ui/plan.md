# Implementation Plan: Terminal Menu UI

**Branch**: `008-terminal-menu-ui` | **Date**: 2025-11-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-terminal-menu-ui/spec.md`
**Depends On**: Feature 007 (Heat Pump Menu API)

## Summary

Build a terminal-based interactive menu application that exposes the Menu API from feature 007. The application will use Python's curses library for cross-platform terminal UI, providing arrow-key navigation, status dashboard, and parameter editing capabilities that mirror the physical heat pump display.

## Technical Context

**Language/Version**: Python 3.9+ (per constitution, Home Assistant compatibility)
**Primary Dependencies**:
- `curses` (stdlib) - Terminal UI rendering and keyboard input
- `buderus_wps` (feature 007) - Menu API for heat pump communication
- `pyserial` - Serial communication (indirect, via Menu API)

**Storage**: N/A (no persistent storage, real-time device access)
**Testing**: pytest with curses mocking, acceptance tests with pexpect
**Target Platform**: Linux/Raspberry Pi (primary), macOS/Windows (secondary)
**Project Type**: Single CLI application extending existing CLI package
**Performance Goals**:
- Status display within 3 seconds of launch (SC-001)
- Menu navigation <100ms response time
- Value write confirmation within 2 seconds

**Constraints**:
- Must work over SSH connections
- Must handle terminal resize gracefully
- Must not block on serial I/O (non-blocking reads)

**Scale/Scope**: Single-user interactive application, ~7 screens (dashboard + 6 menu areas)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | PASS | Builds on buderus_wps library, extends CLI layer |
| II. Hardware Abstraction | PASS | Uses Menu API abstraction, no direct CAN access |
| III. Safety & Reliability | PASS | Read-only dashboard default, validation before writes |
| IV. Test Coverage | PASS | TDD required, curses mocking for tests |
| V. Protocol Documentation | N/A | UI layer, no protocol changes |
| VI. Home Assistant Integration | N/A | CLI tool, not HA plugin |
| VII. CLI Design Principles | PASS | Keyboard navigation, graceful exit, help text |

**Pre-Design Gate**: PASS - All applicable principles satisfied

## Project Structure

### Documentation (this feature)

```
specs/008-terminal-menu-ui/
├── plan.md              # This file
├── research.md          # Phase 0: TUI library research
├── data-model.md        # Phase 1: Screen/view models
├── quickstart.md        # Phase 1: User guide
├── contracts/           # Phase 1: Not applicable (no external API)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
buderus_wps_cli/
├── __init__.py          # Existing CLI package
├── cli.py               # Existing CLI commands
├── tui/                 # NEW: Terminal UI module
│   ├── __init__.py
│   ├── app.py           # Main application loop
│   ├── screens/         # Screen components
│   │   ├── __init__.py
│   │   ├── dashboard.py # Status dashboard
│   │   ├── menu.py      # Menu navigation
│   │   ├── editor.py    # Value editing
│   │   └── schedule.py  # Schedule display/edit
│   ├── widgets/         # Reusable UI elements
│   │   ├── __init__.py
│   │   ├── status_bar.py
│   │   ├── breadcrumb.py
│   │   └── input_field.py
│   └── keyboard.py      # Key handling

tests/
├── unit/
│   └── test_tui_*.py    # TUI unit tests
├── integration/
│   └── test_tui_integration.py
└── acceptance/
    └── test_tui_acceptance.py
```

**Structure Decision**: Extend existing `buderus_wps_cli` package with new `tui/` submodule. This keeps UI code separate from command-line parsing while reusing the existing package infrastructure.

## Complexity Tracking

*No violations - all design choices align with constitution.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |
