# Tasks: USB Connection Control Switch

**Input**: Design documents from `/specs/015-usb-connection-switch/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD required per constitution principle IV. All test tasks included and must be completed FIRST (RED) before implementation (GREEN).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Home Assistant Component**: `custom_components/buderus_wps/` for implementation
- **Tests**: `tests/unit/`, `tests/integration/` at repository root
- All paths are absolute from repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal project setup - just the USB icon constant

- [x] T001 Add ICON_USB constant ("mdi:usb-port") to custom_components/buderus_wps/const.py after ICON_ENERGY_BLOCK

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core coordinator infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Add _manually_disconnected state variable (bool, default False) to BuderusCoordinator.__init__ in custom_components/buderus_wps/coordinator.py after line 72
- [x] T003 [P] Extend mock_coordinator fixture in tests/conftest.py with async_manual_connect, async_manual_disconnect AsyncMock methods and _manually_disconnected=False attribute

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Release USB for CLI Debugging (Priority: P1) 🎯 MVP

**Goal**: Developer can toggle switch OFF to release USB port, use CLI for debugging, then toggle ON to reconnect

**Independent Test**: Toggle switch OFF → CLI connects successfully → Toggle switch ON → Integration reconnects and sensors resume showing data

### Tests for User Story 1 (TDD Required)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Create tests/unit/test_usb_connection_switch.py with TestUSBConnectionSwitch class testing switch properties (name, icon, unique_id)
- [x] T005 [P] [US1] Add test_switch_returns_true_when_connected to tests/unit/test_usb_connection_switch.py verifying is_on returns True when _manually_disconnected=False
- [x] T006 [P] [US1] Add test_switch_returns_false_when_manually_disconnected to tests/unit/test_usb_connection_switch.py verifying is_on returns False when _manually_disconnected=True
- [x] T007 [P] [US1] Add TestUSBConnectionSwitchActions class with test_turn_off_calls_manual_disconnect to tests/unit/test_usb_connection_switch.py
- [x] T008 [P] [US1] Add test_turn_on_calls_manual_connect to TestUSBConnectionSwitchActions in tests/unit/test_usb_connection_switch.py

**Verify**: Run `pytest tests/unit/test_usb_connection_switch.py` → ALL TESTS FAIL (RED)

### Implementation for User Story 1

- [x] T009 [US1] Implement async_manual_disconnect() method in BuderusCoordinator (custom_components/buderus_wps/coordinator.py after async_shutdown at line ~93) with: set _manually_disconnected=True, cancel _reconnect_task, disconnect if _connected
- [x] T010 [US1] Implement async_manual_connect() method in BuderusCoordinator (custom_components/buderus_wps/coordinator.py after async_manual_disconnect) with: set _manually_disconnected=False, reset _backoff_delay=BACKOFF_INITIAL, call _sync_connect, set _connected=True
- [x] T011 [US1] Create BuderusUSBConnectionSwitch class in custom_components/buderus_wps/switch.py after BuderusEnergyBlockSwitch (line ~98) with _attr_name="USB Connection", _attr_icon=ICON_USB, is_on property
- [x] T012 [US1] Implement async_turn_off() method in BuderusUSBConnectionSwitch calling await self.coordinator.async_manual_disconnect()
- [x] T013 [US1] Implement async_turn_on() method in BuderusUSBConnectionSwitch calling await self.coordinator.async_manual_connect() (basic version, error handling in US2)
- [x] T014 [US1] Add BuderusUSBConnectionSwitch to async_setup_entry entity list in custom_components/buderus_wps/switch.py line ~26
- [x] T015 [US1] Add ICON_USB to imports in custom_components/buderus_wps/switch.py line ~12

**Verify**: Run `pytest tests/unit/test_usb_connection_switch.py` → ALL TESTS PASS (GREEN)

**Checkpoint**: At this point, User Story 1 should be fully functional - switch appears in HA UI, can toggle OFF/ON, basic connect/disconnect works

---

## Phase 4: User Story 2 - Handle Port Busy Error (Priority: P2)

**Goal**: When CLI has port open and user toggles switch ON, show clear error message and keep switch OFF

**Independent Test**: Keep CLI session active → Toggle switch ON → Verify error logged "port may be in use" → Switch stays OFF → Close CLI → Toggle ON succeeds

### Tests for User Story 2 (TDD Required)

- [x] T016 [US2] Add test_turn_on_handles_port_in_use_error to TestUSBConnectionSwitchActions in tests/unit/test_usb_connection_switch.py testing HomeAssistantError raised when coordinator.async_manual_connect raises DeviceNotFoundError

**Verify**: Run `pytest tests/unit/test_usb_connection_switch.py::TestUSBConnectionSwitchActions::test_turn_on_handles_port_in_use_error` → TEST FAILS (RED)

### Implementation for User Story 2

- [x] T017 [US2] Add HomeAssistantError import to custom_components/buderus_wps/switch.py imports (from homeassistant.exceptions import HomeAssistantError)
- [x] T018 [US2] Wrap async_manual_connect() call in BuderusUSBConnectionSwitch.async_turn_on() with try-except catching DeviceNotFoundError, DevicePermissionError, DeviceInitializationError
- [x] T019 [US2] Add _LOGGER.warning() in except block logging "Cannot connect - port may be in use by CLI: {err}"
- [x] T020 [US2] Raise HomeAssistantError(f"USB port in use: {err}") from err in except block

**Verify**: Run `pytest tests/unit/test_usb_connection_switch.py` → ALL TESTS PASS (GREEN)

**Checkpoint**: Error handling complete - port-busy scenarios handled gracefully with user-visible feedback

---

## Phase 5: User Story 3 - Auto-Reconnection Behavior (Priority: P3)

**Goal**: Manual disconnect stops auto-reconnection, manual connect bypasses backoff, auto-reconnection works normally when switch ON

**Independent Test**: Simulate connection failure → Verify auto-reconnect starts → Toggle switch OFF → Auto-reconnect stops → Toggle ON → Immediate reconnect (no backoff delay)

### Tests for User Story 3 (TDD Required)

- [x] T021 [P] [US3] Create tests/integration/test_coordinator_manual_disconnect.py with TestCoordinatorManualDisconnect class
- [x] T022 [P] [US3] Add test_manual_disconnect_stops_auto_reconnect to test_coordinator_manual_disconnect.py verifying _reconnect_task cancelled when async_manual_disconnect() called
- [x] T023 [P] [US3] Add test_manual_connect_restarts_connection to test_coordinator_manual_disconnect.py verifying _manually_disconnected=False, _backoff_delay reset, _connected=True after async_manual_connect()
- [x] T024 [P] [US3] Add test_manual_disconnect_preserves_stale_data to test_coordinator_manual_disconnect.py verifying _last_known_good_data not cleared
- [x] T025 [P] [US3] Add test_reconnect_loop_exits_on_manual_disconnect to test_coordinator_manual_disconnect.py verifying _reconnect_with_backoff() exits when _manually_disconnected=True

**Verify**: Run `pytest tests/integration/test_coordinator_manual_disconnect.py` → ALL TESTS FAIL (RED)

### Implementation for User Story 3

- [x] T026 [US3] Modify _reconnect_with_backoff() in custom_components/buderus_wps/coordinator.py line ~168: add "if self._manually_disconnected: _LOGGER.debug('Skipping auto-reconnect'); self._reconnect_task = None; return" at start of while loop
- [x] T027 [US3] Verify async_manual_disconnect() cancels _reconnect_task (should already be implemented from T009, verify with test)
- [x] T028 [US3] Verify async_manual_connect() resets _backoff_delay (should already be implemented from T010, verify with test)

**Verify**: Run `pytest tests/integration/test_coordinator_manual_disconnect.py` → ALL TESTS PASS (GREEN)

**Checkpoint**: All user stories complete - state machine works correctly in all scenarios (normal, manual disconnect, connection failure)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, documentation, and final validation

- [x] T029 [P] Run mypy type checking on custom_components/buderus_wps/coordinator.py and custom_components/buderus_wps/switch.py, fix any type errors
- [x] T030 [P] Run ruff linting on custom_components/buderus_wps/coordinator.py and custom_components/buderus_wps/switch.py, fix any issues
- [x] T031 [P] Run black formatting on custom_components/buderus_wps/coordinator.py, custom_components/buderus_wps/switch.py, and tests/ directory
- [x] T032 Run full test suite with pytest --ignore=tests/hil/ verifying all existing tests still pass
- [ ] T033 Run coverage report with pytest tests/unit/test_usb_connection_switch.py tests/integration/test_coordinator_manual_disconnect.py --cov=custom_components.buderus_wps.switch --cov=custom_components.buderus_wps.coordinator --cov-report=term-missing, verify 100% coverage for new code
- [ ] T034 Validate implementation against specs/015-usb-connection-switch/quickstart.md manual acceptance test scenarios (requires physical hardware)
- [ ] T035 Update CLAUDE.md Active Features section if needed (likely already updated by update-agent-context.sh)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001) - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion (T002-T003)
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete (T004-T028)

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (T002-T003) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on Foundational AND User Story 1 (T009-T015) - Enhances US1 async_turn_on error handling
- **User Story 3 (P3)**: Depends on Foundational AND User Story 1 (T009-T010) - Tests/modifies coordinator methods from US1

**Recommended Order**: Sequential (P1 → P2 → P3) since US2 and US3 build on US1 implementation

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Coordinator methods before switch entity (US1: T009-T010 before T011-T015)
- Switch class before setup entry modification (US1: T011-T013 before T014)
- Core implementation before error handling (US1 before US2)
- Implementation before state machine refinement (US1-US2 before US3)

### Parallel Opportunities

- **Phase 1**: Only 1 task (T001) - no parallelism
- **Phase 2**: T002 and T003 can run in parallel [P]
- **User Story 1 Tests**: T004-T008 can all run in parallel [P]
- **User Story 2 Tests**: Only 1 test (T016) - no parallelism
- **User Story 3 Tests**: T021-T025 can all run in parallel [P]
- **Polish**: T029, T030, T031 can run in parallel [P]

**Note**: User stories should generally be done sequentially due to dependencies, but tests within a story can be written in parallel.

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all unit tests for User Story 1 together:
Task: "Create tests/unit/test_usb_connection_switch.py with TestUSBConnectionSwitch class"
Task: "Add test_switch_returns_true_when_connected to tests/unit/test_usb_connection_switch.py"
Task: "Add test_switch_returns_false_when_manually_disconnected to tests/unit/test_usb_connection_switch.py"
Task: "Add TestUSBConnectionSwitchActions class with test_turn_off_calls_manual_disconnect"
Task: "Add test_turn_on_calls_manual_connect to TestUSBConnectionSwitchActions"

# All 5 test tasks (T004-T008) can be written simultaneously by different developers
# or by an agent spawning parallel tasks, since they're in the same file but
# test different aspects
```

---

## Parallel Example: User Story 3 Integration Tests

```bash
# Launch all integration tests for User Story 3 together:
Task: "Create tests/integration/test_coordinator_manual_disconnect.py"
Task: "Add test_manual_disconnect_stops_auto_reconnect"
Task: "Add test_manual_connect_restarts_connection"
Task: "Add test_manual_disconnect_preserves_stale_data"
Task: "Add test_reconnect_loop_exits_on_manual_disconnect"

# All 5 test tasks (T021-T025) can be written simultaneously
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T003) - CRITICAL
3. Complete Phase 3: User Story 1 (T004-T015)
   - Write tests first (T004-T008) → Verify FAIL
   - Implement features (T009-T015) → Verify PASS
4. **STOP and VALIDATE**: Test User Story 1 independently with quickstart.md Test 1
5. Deploy/demo if ready - **Functional MVP** ✅

**Result**: Developers can toggle switch OFF, use CLI, toggle ON, reconnect. Basic workflow complete.

### Incremental Delivery

1. Complete Setup + Foundational (T001-T003) → Foundation ready
2. Add User Story 1 (T004-T015) → Test independently → **Deploy MVP** 🎯
3. Add User Story 2 (T016-T020) → Test independently → **Deploy with error handling**
4. Add User Story 3 (T021-T028) → Test independently → **Deploy with full state machine**
5. Polish (T029-T035) → Final quality gates → **Production ready**

Each story adds value without breaking previous stories.

### Parallel Team Strategy

**Not recommended** for this feature due to sequential dependencies:
- US2 modifies US1 code (async_turn_on error handling)
- US3 modifies US1 code (_reconnect_with_backoff check)

**Better approach**: Single developer implementing sequentially P1 → P2 → P3, or:
1. Developer A: Phases 1-3 (Setup, Foundational, US1)
2. Developer B: Phase 4 (US2) - starts after T015 complete
3. Developer A: Phase 5 (US3) - starts after T015 complete, coordinates with Dev B on coordinator.py changes

---

## Task Count Summary

- **Total Tasks**: 35
- **Setup (Phase 1)**: 1 task
- **Foundational (Phase 2)**: 2 tasks
- **User Story 1 (Phase 3)**: 12 tasks (5 tests + 7 implementation)
- **User Story 2 (Phase 4)**: 5 tasks (1 test + 4 implementation)
- **User Story 3 (Phase 5)**: 8 tasks (5 tests + 3 implementation)
- **Polish (Phase 6)**: 7 tasks

**Test Coverage**: 11 test tasks covering all 14 functional requirements (FR-001 through FR-014)

**Parallel Opportunities**: 13 tasks marked [P] can run concurrently when dependencies allow

---

## Notes

- [P] tasks = different files or independent sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD required: Tests MUST fail before implementing (RED → GREEN → REFACTOR)
- Commit after each task or logical group of related tasks
- Stop at any checkpoint to validate story independently
- Constitution requirement: 100% test coverage for described functionality
- All acceptance scenarios from spec.md must be testable after Phase 5 complete

---

## Acceptance Criteria Mapping

Mapping spec.md acceptance scenarios to task completion:

| Acceptance Scenario | Verified After Task | Test Location |
|---------------------|---------------------|---------------|
| US1-AS1: Integration releases USB within 2s | T015 | Unit test T005-T008 |
| US1-AS2: CLI successfully connects when switch OFF | T015 | Manual test (hardware) |
| US1-AS3: Integration reconnects within 5s | T015 | Unit test T008 |
| US1-AS4: Sensors show stale data when switch OFF | T015 | Integration test (existing graceful degradation) |
| US2-AS1: Error logged when port busy | T020 | Unit test T016 |
| US2-AS2: Reconnection succeeds after CLI closed | T020 | Manual test (hardware) |
| US2-AS3: Sensors remain available during error | T020 | Integration test (existing) |
| US3-AS1: Auto-reconnect stops when switch OFF | T028 | Integration test T022 |
| US3-AS2: No auto-reconnect during manual disconnect | T028 | Integration test T025 |
| US3-AS3: Manual reconnect bypasses backoff | T028 | Integration test T023 |
| US3-AS4: Auto-reconnect works normally when switch ON | T028 | Integration test T022, T025 |

**All 11 acceptance scenarios** testable after completing all 3 user story phases.
