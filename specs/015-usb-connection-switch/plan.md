# Implementation Plan: USB Connection Control Switch

**Branch**: `015-usb-connection-switch` | **Date**: 2025-12-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-usb-connection-switch/spec.md`

## Summary

Add a Home Assistant switch entity that allows developers to temporarily release the USB serial port for CLI debugging. When toggled OFF, the integration disconnects from the USB port, allowing the CLI tool to access it. When toggled ON, the integration reconnects. The feature leverages the existing graceful degradation system (v1.1.0) to preserve stale data during disconnection and integrates with the existing auto-reconnection logic with a three-state model: normal operation, manual disconnect, and connection failure.

**Primary Goal**: Enable developers to switch between HA integration and CLI tool in under 10 seconds without service restart (80% workflow time reduction: 60s → 10s).

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: Home Assistant Core (>=2024.3.0), homeassistant.helpers.update_coordinator, homeassistant.components.switch
**Storage**: N/A (state is non-persistent by design)
**Testing**: pytest, pytest-asyncio, pytest-homeassistant-custom-component
**Target Platform**: Home Assistant OS/Supervised/Container (Linux-based)
**Project Type**: Home Assistant custom component (integration layer)
**Performance Goals**: 2s disconnect, 5s reconnect, 10s workflow switch
**Constraints**: Non-persistent switch state across restarts, exclusive USB port access (OS-level)
**Scale/Scope**: Single device, single user, developer-focused feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture ✅ **PASS**

- **Status**: Compliant
- **Rationale**: Feature adds HA integration layer only. Core USB management already exists in library layer (`buderus_wps.can_adapter.USBtinAdapter`). No library changes needed - only integration-level switch entity and coordinator methods.
- **Verification**: Existing `USBtinAdapter.connect()` and `.disconnect()` methods provide library primitives. New feature wraps these with HA switch interface.

### II. Hardware Abstraction & Protocol Fidelity ✅ **PASS**

- **Status**: Compliant (Not applicable)
- **Rationale**: Feature does not interact with CAN protocol layer. Only manages connection lifecycle. No CAN message changes, no protocol modifications.
- **Verification**: No `# PROTOCOL:` tags needed. Uses existing connection management without protocol changes.

### III. Safety & Reliability ✅ **PASS**

- **Status**: Compliant
- **Rationale**:
  - Manual disconnect prevents write operations (port released)
  - Error handling for port-busy scenarios (FR-006, FR-008)
  - Graceful degradation preserves stale data (FR-007, SC-003)
  - Thread-safe toggle operations (FR-012, async lock)
- **Verification**: Edge cases documented (5 scenarios in spec), error paths covered in acceptance scenarios.

### IV. Comprehensive Test Coverage (NON-NEGOTIABLE) ✅ **PASS**

- **Status**: Compliant
- **Requirement**: 100% coverage for described functionality, TDD required
- **Plan**:
  - Unit tests: Switch entity properties, state logic, error handling (~150 lines)
  - Integration tests: Coordinator manual disconnect/connect cycle, auto-reconnect interaction (~200 lines)
  - Acceptance tests: Manual testing with real USB hardware (not automated due to hardware dependency)
- **Coverage Target**: 100% for new code (switch entity class, coordinator methods)
- **Verification**: All 14 functional requirements (FR-001 through FR-014) have corresponding test cases. All 11 acceptance scenarios testable.

### V. Protocol Documentation & Traceability ✅ **PASS**

- **Status**: Compliant (Not applicable)
- **Rationale**: No protocol changes. Feature operates at connection management layer above protocol.
- **Verification**: N/A - no CAN protocol interaction.

### Testing Gates

1. **All tests pass (all layers)**: Unit + integration tests must pass
2. **Type checking passes (`mypy`)**: Type hints required for new methods
3. **Linting passes (`ruff`)**: Code style compliance
4. **Coverage does not decrease**: 100% for new switch/coordinator code
5. **Documentation updated**: Inline docstrings for public methods
6. **All user story acceptance scenarios tested**: 11 scenarios (3 user stories P1-P3)

### Constitution Compliance Summary

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | ✅ PASS | Integration layer only, library unchanged |
| II. Protocol Fidelity | ✅ PASS | No protocol interaction |
| III. Safety | ✅ PASS | Error handling, graceful degradation, thread safety |
| IV. Test Coverage | ✅ PASS | TDD, 100% coverage, 11 acceptance scenarios |
| V. Traceability | ✅ PASS | No protocol changes |

**Overall**: ✅ **ALL GATES PASSED** - Ready for Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/015-usb-connection-switch/
├── spec.md              # Feature specification (user stories, requirements, success criteria)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: Design decisions and patterns research
├── data-model.md        # Phase 1 output: Entity and state model
├── quickstart.md        # Phase 1 output: Quick implementation guide
├── contracts/           # Phase 1 output: API contracts (switch entity interface)
│   └── switch_entity.md
└── checklists/
    └── requirements.md  # Quality validation (already created)
```

### Source Code (repository root)

```text
custom_components/buderus_wps/     # Home Assistant integration
├── __init__.py                    # Integration setup/teardown
├── coordinator.py                 # [MODIFY] Add manual disconnect/connect methods
├── switch.py                      # [MODIFY] Add BuderusUSBConnectionSwitch class
├── const.py                       # [MODIFY] Add ICON_USB constant
├── entity.py                      # [NO CHANGE] Base entity class
├── sensor.py                      # [NO CHANGE] Sensor entities
└── config_flow.py                 # [NO CHANGE] Configuration UI

tests/
├── unit/
│   ├── test_ha_switch.py          # [EXISTS] Energy block switch tests
│   └── test_usb_connection_switch.py  # [CREATE] USB connection switch tests
├── integration/
│   ├── test_ha_coordinator.py     # [EXISTS] Coordinator tests
│   └── test_coordinator_manual_disconnect.py  # [CREATE] Manual disconnect cycle tests
├── acceptance/
│   └── [Manual testing with real hardware]
└── conftest.py                    # [MODIFY] Add coordinator mock methods
```

**Structure Decision**: Single project (Home Assistant custom component). Feature adds to existing integration layer only. No library changes, no CLI changes. Follows standard HA custom component structure with entity platform pattern.

## Complexity Tracking

> **No violations** - Constitution check passed all gates.

*Table intentionally empty - all principles satisfied without exceptions.*

## Phase 0: Research & Design Decisions

### Research Areas

1. **Home Assistant Switch Entity Pattern**
   - How do existing switches in this integration work? (BuderusEnergyBlockSwitch)
   - What properties/methods must be implemented?
   - How to handle async operations in switch entity?

2. **Coordinator State Management**
   - How does existing coordinator handle connection state?
   - Where to add manual disconnect flag without breaking existing logic?
   - How to safely cancel auto-reconnection tasks?

3. **Graceful Degradation Integration**
   - How does existing graceful degradation (v1.1.0) work?
   - Does it already handle manual disconnect scenario?
   - Any modifications needed to stale data logic?

4. **Error Handling Patterns**
   - How to communicate port-busy errors to user?
   - Should switch return to OFF state on reconnection failure?
   - What Home Assistant error reporting mechanisms are available?

5. **Testing Strategy**
   - How to mock coordinator methods in switch tests?
   - How to test auto-reconnection cancellation?
   - Best practices for testing HA switch entities?

### Resolution: See research.md

All research questions will be resolved in `research.md` (Phase 0 output).

## Phase 1: Design Artifacts

### Data Model

See `data-model.md` for complete entity and state model design.

**Key Entities**:
- **BuderusUSBConnectionSwitch** (new): HA switch entity
- **BuderusCoordinator** (modified): Add manual disconnect state and methods
- **Connection State Machine**: Three states (normal, manual_disconnect, connection_failure)

### API Contracts

See `contracts/` directory for detailed interface specifications.

**New Public Methods** (coordinator.py):
- `async_manual_disconnect() -> None`: Release USB port
- `async_manual_connect() -> None`: Reconnect USB port

**New Entity** (switch.py):
- `BuderusUSBConnectionSwitch`: Switch entity with is_on, async_turn_on, async_turn_off

### Implementation Quick Start

See `quickstart.md` for step-by-step implementation guide.

## Phase 2: Task Breakdown

*Not included in this plan. Generated by `/speckit.tasks` command.*

See `tasks.md` (created separately after plan approval).

## Critical Files to Modify

### High Priority (Core Implementation)

1. **custom_components/buderus_wps/coordinator.py** (~60 lines added, ~5 modified)
   - Add `_manually_disconnected` state variable (line ~64 in `__init__`)
   - Add `async_manual_disconnect()` method (after `async_shutdown` at line ~93)
   - Add `async_manual_connect()` method (after `async_shutdown` at line ~93)
   - Modify `_reconnect_with_backoff()` to check `_manually_disconnected` (line ~166)

2. **custom_components/buderus_wps/switch.py** (~45 lines added, ~4 modified)
   - Add `BuderusUSBConnectionSwitch` class (after `BuderusEnergyBlockSwitch`)
   - Modify `async_setup_entry()` to include new switch (line ~26)

3. **custom_components/buderus_wps/const.py** (~1 line added)
   - Add `ICON_USB = "mdi:usb-port"` constant (after existing icon constants)

### High Priority (Tests - TDD)

4. **tests/unit/test_usb_connection_switch.py** (NEW, ~150 lines)
   - Test switch properties (name, icon, entity_key)
   - Test `is_on` property returns correct state based on coordinator flag
   - Test `async_turn_off()` calls `coordinator.async_manual_disconnect()`
   - Test `async_turn_on()` calls `coordinator.async_manual_connect()`
   - Test error handling when port busy (HomeAssistantError raised)

5. **tests/integration/test_coordinator_manual_disconnect.py** (NEW, ~200 lines)
   - Test manual disconnect stops auto-reconnection loop
   - Test manual connect restarts connection immediately (bypasses backoff)
   - Test stale data preserved during manual disconnect
   - Test connection failure during normal operation triggers auto-reconnect
   - Test connection failure during manual disconnect stays disconnected

### Medium Priority (Test Infrastructure)

6. **tests/conftest.py** (~3 lines added)
   - Add `coordinator.async_manual_connect = AsyncMock()` to coordinator fixture
   - Add `coordinator.async_manual_disconnect = AsyncMock()` to coordinator fixture
   - Add `coordinator._manually_disconnected = False` to coordinator fixture

### Low Priority (Documentation)

7. **Optional**: `docs/usb_connection_switch.md` (if documentation directory exists)
   - User guide: how to use the switch
   - Expected behavior when switch OFF
   - Troubleshooting port-busy errors

## Implementation Order (TDD)

Following Test-Driven Development (constitution principle IV):

1. **Phase 0 Complete**: Finish research.md, data-model.md, contracts/, quickstart.md
2. **Write unit tests first** (test_usb_connection_switch.py) - tests fail (RED)
3. Add `ICON_USB` constant to const.py
4. Implement coordinator methods (`async_manual_disconnect`, `async_manual_connect`) - some tests pass
5. Modify auto-reconnection logic in coordinator (`_reconnect_with_backoff`) - more tests pass
6. Implement switch entity class (`BuderusUSBConnectionSwitch`) - tests pass (GREEN)
7. Add switch to `async_setup_entry` - integration complete
8. **Write integration tests** (test_coordinator_manual_disconnect.py) - tests fail (RED)
9. Refine coordinator state management if integration tests reveal issues (REFACTOR)
10. All tests pass (GREEN)
11. Run coverage, mypy, ruff - quality gates pass
12. Update test fixtures in conftest.py
13. Manual acceptance testing with real hardware

## Risk Assessment

### Low Risk

- **Additive changes only**: No breaking changes to existing features
- **Well-isolated**: Changes confined to coordinator and new switch entity
- **Existing patterns**: Follows `BuderusEnergyBlockSwitch` pattern exactly
- **Graceful degradation exists**: v1.1.0 already handles disconnected state

### Medium Risk

- **Race condition**: Auto-reconnect starts before manual disconnect completes
  - **Mitigation**: Check `_manually_disconnected` at start of `_reconnect_with_backoff`
  - **Verification**: Integration test explicitly covers this scenario

- **User confusion**: Switch shows ON but connection actually failed
  - **Mitigation**: Clear naming ("USB Connection" not "Connection Status")
  - **Documentation**: Explain switch represents intent, not actual status
  - **Future**: Could add separate binary sensor for actual connection status

### Low Risk (Handled by Design)

- **State loss on restart**: Switch initializes to ON after HA restart
  - **Acceptable**: Documented in spec, restarts are rare, default should be connected
  - **Out of scope**: Persistent state across restarts (spec section: Out of Scope)

- **CLI port access**: CLI fails to connect even when switch is OFF
  - **Expected**: Port busy errors are normal race condition
  - **Handled**: Error message guides user ("port may be in use by CLI")

## Success Criteria Mapping

Mapping spec success criteria (SC-001 through SC-010) to implementation verification:

| Criterion | Verification Method | Implementation Component |
|-----------|---------------------|--------------------------|
| SC-001: <10s workflow switch | Manual timing test | Switch toggle + CLI connect |
| SC-002: 95% reconnect success | Integration test (mocked) | `async_manual_connect()` |
| SC-003: Stale data 10+ min | Integration test | Graceful degradation (existing) |
| SC-004: Zero crashes (100 cycles) | Unit test loop | Switch toggle + coordinator state |
| SC-005: 100% clear error messages | Unit test assertions | Error logging in `async_turn_on()` |
| SC-006: Auto-reconnect stops in 2s | Integration test timing | `_reconnect_with_backoff()` check |
| SC-007: Manual reconnect immediate | Integration test timing | `async_manual_connect()` bypasses backoff |
| SC-008: Zero data loss (1000 cycles) | Integration test loop | State machine + graceful degradation |
| SC-009: CLI connects in 1s | Manual test (hardware) | USB port release in `async_manual_disconnect()` |
| SC-010: 80% time reduction | Manual timing comparison | Overall feature workflow |

## Next Steps

1. **Phase 0**: Generate `research.md` (design decisions, existing patterns)
2. **Phase 1**: Generate `data-model.md`, `contracts/`, `quickstart.md`
3. **Update agent context**: Run update script to add new tech to agent-specific file
4. **User approval**: Review plan before proceeding to `/speckit.tasks`
5. **Phase 2**: Generate `tasks.md` via `/speckit.tasks` command
6. **Implementation**: Execute tasks in TDD order
