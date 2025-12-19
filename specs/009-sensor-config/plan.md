# Implementation Plan: Sensor Configuration and Installation Settings

**Branch**: `009-sensor-config` | **Date**: 2024-12-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-sensor-config/spec.md`

## Summary

This feature extracts the hardcoded CAN broadcast-to-sensor mappings from the TUI into a shared configuration module in the core library. It also introduces installation-specific configuration for heating circuits and DHW distribution. The configuration will be loaded from a YAML file with sensible defaults when the file is missing.

## Technical Context

**Language/Version**: Python 3.9+ (as per constitution)
**Primary Dependencies**: PyYAML (for configuration parsing), existing buderus_wps library
**Storage**: YAML configuration file (`~/.config/buderus-wps/config.yaml` or `./config.yaml`)
**Testing**: pytest with mocking for file I/O
**Target Platform**: Linux on Raspberry Pi (primary), cross-platform compatible
**Project Type**: Single library project with CLI
**Performance Goals**: Configuration loading < 100ms (one-time at startup)
**Constraints**: Must work without configuration file (graceful fallback to defaults)
**Scale/Scope**: Single configuration file, ~50 lines typical config

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | ✅ PASS | Config module lives in core library, usable by CLI/TUI/HA |
| II. Hardware Abstraction | ✅ PASS | Sensor mappings abstract CAN addresses to human names |
| III. Safety & Reliability | ✅ PASS | Graceful fallback to defaults, validation on load |
| IV. Comprehensive Test Coverage | ✅ PASS | Tests required for all acceptance scenarios |
| V. Protocol Documentation | ✅ PASS | Sensor mappings document CAN address meanings |
| VI. Home Assistant Standards | N/A | Not HA integration code |
| VII. CLI Design Principles | ✅ PASS | Config via files per CLI principles |

**Gate Status**: PASS - proceed to Phase 0

## Project Structure

### Documentation (this feature)

```
specs/009-sensor-config/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── config_api.py    # Configuration API contracts
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```
buderus_wps/
├── config.py            # NEW: Configuration loader and models
├── __init__.py          # Update: Export config classes
└── [existing modules]

buderus_wps_cli/
└── tui/
    └── app.py           # UPDATE: Import mappings from config

tests/
├── unit/
│   └── test_config.py   # NEW: Unit tests for config module
├── integration/
│   └── test_config_integration.py  # NEW: Integration tests
└── acceptance/
    └── test_config_acceptance.py   # NEW: Acceptance tests
```

**Structure Decision**: Configuration module added to core library (`buderus_wps/config.py`) following library-first architecture. TUI updated to consume shared config.

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Library-First Architecture | ✅ PASS | `config.py` in core library, contracts defined |
| II. Hardware Abstraction | ✅ PASS | Sensor mappings abstract CAN addresses |
| III. Safety & Reliability | ✅ PASS | Validation + graceful fallback documented |
| IV. Comprehensive Test Coverage | ✅ PASS | Test files specified in structure |
| V. Protocol Documentation | ✅ PASS | Mappings in data-model.md and contracts |
| VI. Home Assistant Standards | N/A | Not HA code |
| VII. CLI Design Principles | ✅ PASS | Config file + env var + CLI flag support |

**Post-Design Gate Status**: ✅ PASS - ready for `/speckit.tasks`

## Complexity Tracking

*No violations - design follows constitution principles*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
