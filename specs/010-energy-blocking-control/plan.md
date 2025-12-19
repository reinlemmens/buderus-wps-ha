# Implementation Plan: Energy Blocking Control

**Branch**: `010-energy-blocking-control` | **Date**: 2025-12-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-energy-blocking-control/spec.md`

## Summary

Implement energy blocking control for the Buderus WPS heat pump, allowing users to block the compressor and auxiliary heater from consuming energy. This enables demand response during peak electricity pricing and manual load shedding. The implementation uses existing CAN bus parameters identified in the FHEM reference (ADDITIONAL_USER_BLOCKED for aux heater, COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 for compressor).

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: pyserial (existing), buderus_wps core library
**Storage**: N/A (state persists in heat pump)
**Testing**: pytest with mocked CAN adapter
**Target Platform**: Linux on Raspberry Pi (primary), cross-platform compatible
**Project Type**: Library + CLI extension
**Performance Goals**: < 5 seconds for blocking operations, < 3 seconds for status reads
**Constraints**: Must not interfere with heat pump safety systems
**Scale/Scope**: 6 new CLI commands, 1 new library class, ~15 test cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | ✓ PASS | Core logic in `buderus_wps.energy_blocking`, CLI wraps library |
| II. Hardware Abstraction & Protocol Fidelity | ✓ PASS | Uses existing CAN protocol via HeatPumpClient |
| III. Safety & Reliability | ✓ PASS | Validates via read-after-write, documents safety overrides |
| IV. Comprehensive Test Coverage | ✓ PASS | Unit + integration + contract tests planned |
| V. Protocol Documentation & Traceability | ✓ PASS | FHEM line references in research.md |
| VI. Home Assistant Integration Standards | N/A | Future enhancement |
| VII. CLI Design Principles | ✓ PASS | Verb-noun structure, JSON output support |

## Project Structure

### Documentation (this feature)

```
specs/010-energy-blocking-control/
├── plan.md              # This file
├── research.md          # Phase 0 output - FHEM parameter research
├── data-model.md        # Phase 1 output - Entity definitions
├── quickstart.md        # Phase 1 output - Usage examples
├── contracts/           # Phase 1 output - API contracts
│   └── energy_blocking_api.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```
buderus_wps/
├── __init__.py          # Add EnergyBlockingControl export
├── energy_blocking.py   # NEW: EnergyBlockingControl class
└── ...

buderus_wps_cli/
├── commands/
│   └── energy.py        # NEW: CLI commands for energy blocking
└── cli.py               # Add energy command group

tests/
├── unit/
│   └── test_energy_blocking.py    # NEW: Unit tests
├── integration/
│   └── test_energy_blocking_integration.py  # NEW: Integration tests
└── contract/
    └── test_energy_blocking_contract.py     # NEW: Protocol tests
```

**Structure Decision**: Follows existing project structure. New `energy_blocking.py` in core library, new `energy.py` in CLI commands directory.

## Design Decisions

### 1. Parameter Selection

**Decision**: Use ADDITIONAL_USER_BLOCKED (idx 155) for aux heater and COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 (idx 263) for compressor.

**Rationale**:
- These are explicitly user-controllable parameters (extid starts with 'C0', max > 0)
- They directly control the blocking state without requiring external hardware inputs
- Reference: FHEM 26_KM273v018.pm lines 332 (aux) and 415 (compressor)

### 2. Value Encoding

**Decision**: Use standard boolean encoding (0 = unblocked, 1 = blocked).

**Rationale**:
- Heat pump parameters use standard integer encoding
- The large max value (16777216) represents a bitmask capability we don't need
- Simple boolean is sufficient for on/off control

### 3. Verification Strategy

**Decision**: Read-after-write verification using status parameters.

**Rationale**:
- Writing to control parameter, then reading status parameter confirms heat pump accepted the change
- Handles edge cases where write appears successful but heat pump didn't apply it
- Status parameters: COMPRESSOR_BLOCKED (idx 247), ADDITIONAL_BLOCKED (idx 9)

### 4. Error Handling

**Decision**: Return structured BlockingResult with success flag, message, and optional error details.

**Rationale**:
- Follows existing library patterns
- Provides actionable feedback to users
- Supports both CLI and programmatic usage

## CAN Protocol Details

### Write Operations

| Operation | Parameter | idx | Value |
|-----------|-----------|-----|-------|
| Block compressor | COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 | 263 | 1 |
| Unblock compressor | COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 | 263 | 0 |
| Block aux heater | ADDITIONAL_USER_BLOCKED | 155 | 1 |
| Unblock aux heater | ADDITIONAL_USER_BLOCKED | 155 | 0 |

### Read Operations (Status)

| Status | Parameter | idx | Blocked if |
|--------|-----------|-----|------------|
| Compressor status | COMPRESSOR_BLOCKED | 247 | value != 0 |
| Aux heater status | ADDITIONAL_BLOCKED | 9 | value != 0 |

## Test Strategy

### Unit Tests (tests/unit/test_energy_blocking.py)

1. BlockingState dataclass validation
2. BlockingResult construction
3. EnergyBlockingControl initialization
4. Parameter name lookup
5. Value encoding (0/1)

### Integration Tests (tests/integration/test_energy_blocking_integration.py)

1. Block compressor via mocked adapter
2. Unblock compressor via mocked adapter
3. Block aux heater via mocked adapter
4. Unblock aux heater via mocked adapter
5. Get status returns both components
6. Clear all blocks
7. Error handling on timeout
8. Error handling on verification failure

### Contract Tests (tests/contract/test_energy_blocking_contract.py)

1. Write message format for COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1
2. Write message format for ADDITIONAL_USER_BLOCKED
3. Read message format for COMPRESSOR_BLOCKED
4. Read message format for ADDITIONAL_BLOCKED

### Acceptance Tests (tests/acceptance/test_energy_blocking_acceptance.py)

1. User Story 1: Block/unblock compressor flow
2. User Story 2: Block/unblock aux heater flow
3. User Story 3: View blocking status
4. User Story 4: Clear all blocks
5. Edge case: Rapid command succession

## Complexity Tracking

*No constitution violations - table not needed*

## Dependencies

- Existing: HeatPumpClient, ParameterRegistry, USBtinAdapter
- No new external dependencies required
