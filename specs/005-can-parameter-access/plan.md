# Implementation Plan: CAN Bus Parameter Read/Write Access

**Branch**: `005-can-parameter-access` | **Date**: 2025-10-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-can-parameter-access/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement library and CLI functionality to read and write heat pump parameters using human-readable names instead of hexadecimal addresses. This feature provides a user-friendly interface layer on top of the CAN communication primitives (Feature 001) and parameter definitions (Feature 002), with automatic validation, error handling, and timeout management. The implementation enables both programmatic access via the library and command-line access for scripting and manual operations.

## Technical Context

**Language/Version**: Python 3.9+ (per constitution, for Home Assistant compatibility)
**Primary Dependencies**:
- `pyserial` (from Feature 001 - CAN USB serial communication)
- Built-in `logging` module with rotating file handler
- `argparse` for CLI argument parsing
- Standard library collections for parameter lookup optimization
**Storage**: In-memory parameter configuration loaded from Feature 002; rotating log files (10MB limit)
**Testing**: pytest with coverage reporting (targeting 100% for all described functionality per constitution)
**Target Platform**: Linux (primary), macOS (development), any platform supporting Python 3.9+ and serial ports
**Project Type**: Single project (library + CLI wrapper)
**Performance Goals**:
- Parameter name lookup: <100ms for 400+ parameters
- Read operation: <2 seconds (5-second timeout)
- Write operation: <3 seconds (5-second timeout)
**Constraints**:
- Synchronous blocking operations only (no async)
- Single-threaded usage (no thread-safety guarantees)
- Immediate failure on errors (no automatic retries)
- 5-second timeout for device communication
**Scale/Scope**:
- 400+ heat pump parameters
- Error-default logging with optional debug mode
- CLI supports both human-readable and machine-parseable output

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Library-First Architecture ✅
- **Status**: PASS
- **Assessment**: This feature implements library functionality (`buderus_wps` package) with a thin CLI wrapper (`buderus_wps_cli`), following the layered architecture. Library will be independently testable and documented.

### Principle II: Hardware Abstraction & Protocol Fidelity ✅
- **Status**: PASS
- **Assessment**: Feature builds on top of Feature 001 (CAN communication) and Feature 002 (parameter definitions from FHEM reference). Protocol implementation is abstracted from this layer - this feature focuses on parameter access interface.

### Principle III: Safety & Reliability ✅
- **Status**: PASS
- **Assessment**:
  - Write operations validate against min/max constraints (FR-003)
  - Read-only parameters are enforced (FR-004)
  - 5-second timeout prevents indefinite hangs (FR-007)
  - Immediate failure with clear diagnostic messages (FR-007)
  - Error-only logging by default with optional debug mode (FR-013, FR-014)

### Principle IV: Comprehensive Test Coverage for All Described Functionality ⚠️
- **Status**: PENDING (Phase 1 completion required)
- **Assessment**: Specification includes:
  - 3 user stories with 11 acceptance scenarios total
  - 8 edge cases (4 resolved in clarifications)
  - 14 functional requirements + 5 non-functional requirements
  - All require corresponding tests per constitution
- **Action**: Phase 1 must generate test specifications for all scenarios; implementation must achieve 100% coverage

### Principle V: Protocol Documentation & Traceability ✅
- **Status**: PASS
- **Assessment**: This feature uses parameter definitions from Feature 002 which maintains FHEM traceability. Code will include comments referencing dependency features and parameter metadata sources.

### Principle VI: Home Assistant Integration Standards N/A
- **Status**: N/A
- **Assessment**: This feature provides library and CLI only. Home Assistant integration is out of scope (per spec.md line 140).

### Principle VII: CLI Design Principles ⚠️
- **Status**: NEEDS CLARIFICATION
- **Assessment**:
  - Spec requires human-readable and machine-parseable output (FR-008)
  - Spec requires appropriate exit codes (FR-010)
  - Constitution requires verb-noun structure and --format json flag
  - **Action**: Phase 0 research must clarify CLI command structure and options

### Technical Standards Check ✅
- **Language**: Python 3.9+ ✅
- **Type Hints**: Will be mandatory for public APIs ✅
- **Formatting**: Will use `black` ✅
- **Linting**: Will use `ruff` ✅
- **Type Checking**: Will use `mypy` strict mode ✅
- **Documentation**: Google-style docstrings ✅
- **Testing**: pytest with coverage (100% target for described functionality) ✅

### Testing Gates (Pre-Implementation) ⚠️
All tests must be written before implementation:
1. Unit tests for parameter lookup, validation, read/write operations
2. Integration tests for CAN communication with mocks
3. Contract tests verifying parameter metadata compatibility
4. Acceptance tests for all 11 user story scenarios
5. Edge case tests for all 8 documented edge cases

**GATE STATUS**: ⚠️ CONDITIONAL PASS - May proceed to Phase 0 research with actions noted above

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
buderus_wps/                    # Core library package
├── __init__.py
├── protocol.py                 # CAN protocol (Feature 001)
├── device.py                   # Device abstraction (Feature 001)
├── can_adapter.py              # Hardware abstraction (Feature 001)
├── elements.py                 # Parameter definitions (Feature 002)
├── parameter_access.py         # NEW: Parameter read/write operations (THIS FEATURE)
└── exceptions.py               # NEW: Custom exceptions for parameter operations

buderus_wps_cli/                # CLI tool package
├── __init__.py
├── cli.py                      # NEW: Command-line interface (THIS FEATURE)
└── formatters.py               # NEW: Output formatting (human/JSON) (THIS FEATURE)

tests/
├── unit/                       # Unit tests
│   ├── test_parameter_access.py         # NEW: Parameter operations tests
│   ├── test_parameter_validation.py     # NEW: Validation logic tests
│   └── test_cli_formatters.py           # NEW: CLI output tests
├── integration/                # Integration tests with mocks
│   ├── test_parameter_read_write.py     # NEW: End-to-end read/write with mock CAN
│   └── test_cli_commands.py             # NEW: CLI command execution tests
├── contract/                   # Protocol contract tests
│   └── test_parameter_metadata.py       # NEW: Verify compatibility with Feature 002
└── acceptance/                 # User story acceptance tests
    ├── test_us1_read_parameters.py      # NEW: User Story 1 scenarios
    ├── test_us2_write_parameters.py     # NEW: User Story 2 scenarios
    └── test_us3_cli_commands.py         # NEW: User Story 3 scenarios

logs/                           # NEW: Log file directory (rotating logs, 10MB limit)
```

**Structure Decision**: Single project structure selected. This feature extends the existing `buderus_wps` library package with parameter access functionality and adds CLI components to `buderus_wps_cli` package. Test organization follows constitution requirements with all four test layers (unit, integration, contract, acceptance).

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

